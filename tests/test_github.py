#!/usr/bin/env python3
"""Tests for the GitHub client, against real captured responses."""

from __future__ import annotations

import base64
from collections.abc import Callable

import pytest

from tests.helpers import FakeTransport, Listing, Payload, ok
from wakatime_readme.github import (
    ConflictError,
    FileContent,
    GitHubClient,
)
from wakatime_readme.http import HttpError

Install = Callable[..., FakeTransport]

TOKEN = 'ghs_secret-token-value'  # noqa: S105 - a fake, for asserting it never leaks
REPO = 'mmaachado/mmaachado'


def client(token: str = TOKEN) -> GitHubClient:
    """Build a client for the account the fixtures were captured from."""
    return GitHubClient(token, 'mmaachado')


def contents(text: str, sha: str = 'blob-sha') -> Payload:
    """Shape a Contents API response the way GitHub returns one."""
    encoded = base64.b64encode(text.encode('utf-8')).decode('ascii')
    return {'content': encoded, 'encoding': 'base64', 'sha': sha}


def test_parses_the_real_profile(transport: Install, gh_user: Payload) -> None:
    transport(ok(gh_user))

    profile = client().profile()

    assert profile.login == 'mmaachado'
    assert profile.followers == 27
    assert profile.public_repos == 20
    assert profile.public_gists == 1


def test_orders_repositories_by_stars(
    transport: Install, gh_repos: Listing
) -> None:
    transport(ok(gh_repos))

    repositories = client().repositories()

    assert repositories[0].name == 'sycp'
    assert repositories[0].stars == 29


def test_total_stars_across_the_account(
    transport: Install, gh_repos: Listing
) -> None:
    transport(ok(gh_repos))

    total = sum(repo.stars for repo in client().repositories())

    assert total == 31


def test_profile_is_fetched_only_once(
    transport: Install, gh_user: Payload
) -> None:
    fake = transport(ok(gh_user))
    github = client()

    github.profile()
    github.profile()

    assert fake.call_count == 1


def test_listing_is_shared_between_lookups(
    transport: Install, gh_repos: Listing
) -> None:
    # Only one listing is staged: stars and top repo must share it.
    fake = transport(ok(gh_repos))
    github = client()

    github.repositories()
    github.repositories()

    assert fake.call_count == 1


def test_pagination_continues_past_a_full_page(
    transport: Install, gh_repos: Listing
) -> None:
    full_page = [dict(gh_repos[0]) for _ in range(100)]
    fake = transport(ok(full_page), ok(gh_repos))

    repositories = client().repositories()

    assert fake.call_count == 2
    assert len(repositories) == 120
    assert 'page=2' in fake.calls[1][1]


def test_pagination_stops_on_a_short_page(
    transport: Install, gh_repos: Listing
) -> None:
    # 20 repositories is less than a full page, so one request is enough.
    fake = transport(ok(gh_repos))

    client().repositories()

    assert fake.call_count == 1


def test_missing_release_is_reported_as_a_lookup(transport: Install) -> None:
    transport(ok({'message': 'Not Found'}, status=404))

    with pytest.raises(LookupError) as caught:
        client().latest_release('mmaachado/sycp')

    assert 'mmaachado/sycp' in str(caught.value)


def test_reads_a_file_and_keeps_its_sha(transport: Install) -> None:
    transport(ok(contents('# Title\n', sha='abc123')))

    found = client().read(REPO, 'README.md')

    assert found.text == '# Title\n'
    assert found.sha == 'abc123'


def test_write_sends_back_the_sha_it_was_given(transport: Install) -> None:
    # GitHub rejects the write outright if the sha is stale, so it has to
    # be the one from this run's read.
    fake = transport(ok({'commit': {'sha': 'new'}}, status=200))

    client().write(
        REPO, 'README.md', FileContent('# New\n', 'abc123'), 'update'
    )

    body = fake.sent()
    assert body['sha'] == 'abc123'
    assert base64.b64decode(body['content']).decode('utf-8') == '# New\n'
    assert body['message'] == 'update'


def test_write_uses_put(transport: Install) -> None:
    fake = transport(ok({}, status=200))

    client().write(REPO, 'README.md', FileContent('x', 's'), 'msg')

    assert fake.calls[0][0] == 'PUT'


def test_write_passes_branch_and_authorship_when_given(
    transport: Install,
) -> None:
    fake = transport(ok({}, status=200))

    client().write(
        REPO,
        'README.md',
        FileContent('x', 's'),
        'msg',
        branch='master',
        committer={'name': 'bot', 'email': 'bot@example.com'},
    )

    body = fake.sent()
    assert body['branch'] == 'master'
    assert body['committer']['name'] == 'bot'


def test_write_omits_optional_fields_when_absent(
    transport: Install,
) -> None:
    # Sending an empty branch would make GitHub reject the commit.
    fake = transport(ok({}, status=200))

    client().write(REPO, 'README.md', FileContent('x', 's'), 'msg')

    body = fake.sent()
    assert 'branch' not in body
    assert 'committer' not in body


def test_conflicting_write_is_distinguishable(transport: Install) -> None:
    transport(ok({'message': 'is at another sha'}, status=409))

    with pytest.raises(ConflictError):
        client().write(REPO, 'README.md', FileContent('x', 'old'), 'msg')


def test_token_travels_in_the_header_not_the_url(
    transport: Install, gh_user: Payload
) -> None:
    fake = transport(ok(gh_user))

    client().profile()

    assert TOKEN not in fake.calls[0][1]
    assert fake.header('authorization') == f'Bearer {TOKEN}'


def test_no_authorization_header_without_a_token(
    transport: Install, gh_user: Payload
) -> None:
    # Public data is readable unauthenticated, which is what the local CLI
    # relies on when no token is configured.
    fake = transport(ok(gh_user))

    client(token='').profile()

    assert fake.header('authorization') is None


def test_failure_does_not_leak_the_token(transport: Install) -> None:
    transport(ok({'message': 'Bad credentials'}, status=401))

    with pytest.raises(HttpError) as caught:
        client().profile()

    assert TOKEN not in str(caught.value)
    assert caught.value.status == 401
