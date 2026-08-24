#!/usr/bin/env python3
"""GitHub client: profile data, plus reading and writing a file in place.

Writing goes through the Contents API rather than a checkout, which is
what lets the action run as a single step. Every lookup is memoised, so
a file with three GitHub placeholders still costs one request.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .http import CONFLICT, JsonClient, Redactor

BASE_URL = 'https://api.github.com'
API_VERSION = '2022-11-28'
PAGE_SIZE = 100

OK = 200
CREATED = 201
NOT_FOUND = 404


class ConflictError(Exception):
    """The file moved between our read and our write.

    Someone else committed to the same path in between. The caller is
    expected to read again and retry once.
    """


@dataclass(frozen=True)
class Profile:
    """The public face of an account.

    Example:
        >>> Profile('octocat', 'The Octocat', 42, 8, 3).followers
        42
    """

    login: str
    name: str
    followers: int
    public_repos: int
    public_gists: int


@dataclass(frozen=True)
class Repository:
    """One repository, reduced to what a README might want to show.

    Example:
        >>> Repository('dotfiles', 'octocat/dotfiles', 3, fork=False).stars
        3
    """

    name: str
    full_name: str
    stars: int
    fork: bool


@dataclass(frozen=True)
class FileContent:
    """A file as GitHub returned it, with the blob sha needed to replace it.

    Example:
        >>> FileContent('# Title', 'abc123').sha
        'abc123'
    """

    text: str
    sha: str


def _profile(payload: Mapping[str, Any]) -> Profile:
    """Build a profile from a users endpoint response."""
    return Profile(
        login=str(payload.get('login', '')),
        # An account with no display name set returns null here.
        name=str(payload.get('name') or payload.get('login', '')),
        followers=int(payload.get('followers', 0)),
        public_repos=int(payload.get('public_repos', 0)),
        public_gists=int(payload.get('public_gists', 0)),
    )


def _repository(payload: Mapping[str, Any]) -> Repository:
    """Build a repository from one entry of a repos listing."""
    return Repository(
        name=str(payload.get('name', '')),
        full_name=str(payload.get('full_name', '')),
        stars=int(payload.get('stargazers_count', 0)),
        fork=bool(payload.get('fork', False)),
    )


class GitHubClient:
    """Reads profile data and edits one file through the Contents API.

    The username has to be supplied rather than discovered: a workflow
    token belongs to a bot, so asking the API who it is would return the
    bot instead of the person whose README this is.

    Example:
        >>> GitHubClient('', 'octocat').username
        'octocat'
    """

    def __init__(
        self,
        token: str,
        username: str,
        base_url: str = BASE_URL,
    ) -> None:
        """Prepare the client without contacting anything yet."""
        self.username = username
        self.base_url = base_url
        self._profile: Profile | None = None
        self._repositories: tuple[Repository, ...] | None = None
        self._one_repo: dict[str, Repository] = {}
        headers = {
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': API_VERSION,
        }
        if token:
            # The token travels in this header and nowhere else, and is
            # registered for scrubbing so it cannot surface in an error.
            headers['Authorization'] = f'Bearer {token}'
        self._client = JsonClient(
            base_url=base_url,
            headers=headers,
            redactor=Redactor((token,) if token else ()),
        )

    def profile(self) -> Profile:
        """Return the account's public profile, fetching it once."""
        if self._profile is None:
            body = self._get(f'/users/{self.username}', 'profile')
            self._profile = _profile(body)
        return self._profile

    def repositories(self) -> tuple[Repository, ...]:
        """Return every public repository, most starred first.

        Fetched once per run and reused, so `gh_stars` and `gh_top_repo`
        together still cost a single listing.
        """
        if self._repositories is None:
            found = list(self._all_pages())
            found.sort(key=lambda repo: repo.stars, reverse=True)
            self._repositories = tuple(found)
        return self._repositories

    def repository(self, full_name: str) -> Repository:
        """Return one repository by its `owner/name`."""
        if full_name not in self._one_repo:
            body = self._get(f'/repos/{full_name}', f'repository {full_name}')
            self._one_repo[full_name] = _repository(body)
        return self._one_repo[full_name]

    def latest_release(self, full_name: str) -> str:
        """Return the tag of the most recent release.

        Raises:
            LookupError: when the repository has never published one.
        """
        response = self._client.request(
            'GET', f'/repos/{full_name}/releases/latest'
        )
        if response.status == NOT_FOUND:
            raise LookupError(f'{full_name} has no published release')
        self._check(response.status, f'latest release of {full_name}')
        return str((response.body or {}).get('tag_name', ''))

    def read(self, repository: str, path: str, ref: str = '') -> FileContent:
        """Fetch a file's text and the blob sha needed to replace it."""
        query = f'?ref={ref}' if ref else ''
        body = self._get(
            f'/repos/{repository}/contents/{path}{query}',
            f'{path} in {repository}',
        )
        encoded = str(body.get('content', ''))
        text = base64.b64decode(encoded).decode('utf-8')
        return FileContent(text=text, sha=str(body.get('sha', '')))

    def write(
        self,
        repository: str,
        path: str,
        content: FileContent,
        message: str,
        branch: str = '',
        committer: Mapping[str, str] | None = None,
        author: Mapping[str, str] | None = None,
    ) -> None:
        """Commit new text for a file that already exists.

        The sha must be the one that came back from `read` in this same
        run; GitHub rejects the write outright if it is stale.

        Raises:
            ConflictError: when the blob moved in between.
        """
        payload: dict[str, Any] = {
            'message': message,
            'content': base64.b64encode(content.text.encode('utf-8')).decode(
                'ascii'
            ),
            'sha': content.sha,
        }
        if branch:
            payload['branch'] = branch
        if committer:
            payload['committer'] = dict(committer)
        if author:
            payload['author'] = dict(author)

        response = self._client.request(
            'PUT', f'/repos/{repository}/contents/{path}', payload
        )
        if response.status == CONFLICT:
            raise ConflictError(
                f'{path} in {repository} changed between the read and '
                f'the write'
            )
        self._check(response.status, f'commit to {path} in {repository}')

    def _all_pages(self) -> Sequence[Repository]:
        """Walk the repos listing until a short page ends it."""
        collected: list[Repository] = []
        page = 1
        while True:
            body = self._get(
                f'/users/{self.username}/repos'
                f'?per_page={PAGE_SIZE}&page={page}',
                'repository listing',
            )
            entries = body if isinstance(body, list) else []
            collected.extend(_repository(entry) for entry in entries)
            if len(entries) < PAGE_SIZE:
                return collected
            page += 1

    def _get(self, path: str, what: str) -> Any:  # noqa: ANN401 - JSON shape
        """Fetch one path, raising a named error on anything but success."""
        response = self._client.request('GET', path)
        self._check(response.status, what)
        return response.body

    def _check(self, status: int, what: str) -> None:
        """Turn an unexpected status into a scrubbed, named failure."""
        if status not in (OK, CREATED):
            raise self._client.fail(
                f'GitHub returned {status} for {what}', status
            )
