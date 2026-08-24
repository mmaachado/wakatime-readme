#!/usr/bin/env python3
"""Where the document comes from and where it goes back to.

Two implementations behind one small protocol: a file on disk, for
running locally, and a file in a repository, for running as an action.
Nothing downstream knows which one it is holding, which is why the whole
rewriting path can be tested without a network or a temp directory.

Neither of them translates line endings. A file that arrives with CRLF
goes back with CRLF, because a run that silently reflowed every line
would produce an enormous diff for a one-word change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .github import FileContent, GitHubClient

DEFAULT_MESSAGE = 'chore: refresh README metrics'


class Target(Protocol):
    """A document that can be read and written back."""

    def read(self) -> str:
        """Return the current text."""
        ...

    def write(self, text: str, message: str) -> None:
        """Store new text, describing the change for anything that logs it."""
        ...

    def describe(self) -> str:
        """Name this target for messages meant for a human."""
        ...


@dataclass
class LocalFile:
    """A file on this machine.

    Example:
        >>> LocalFile(Path('README.md')).describe()
        'README.md'
    """

    path: Path

    def read(self) -> str:
        """Return the file's text with its line endings untouched."""
        with self.path.open(encoding='utf-8', newline='') as handle:
            return handle.read()

    def write(self, text: str, message: str) -> None:
        """Overwrite the file, again without touching line endings."""
        with self.path.open('w', encoding='utf-8', newline='') as handle:
            handle.write(text)

    def describe(self) -> str:
        """Name the file as the caller referred to it."""
        return str(self.path)


@dataclass
class GitHubFile:
    """A file in a repository, edited through the Contents API.

    Reading remembers the blob sha, because writing without the sha from
    this same read is rejected outright.

    Example:
        >>> GitHubFile(None, 'owner/repo', 'README.md').describe()
        'README.md in owner/repo'
    """

    client: GitHubClient
    repository: str
    path: str
    branch: str = ''
    committer: dict[str, str] | None = None
    author: dict[str, str] | None = None
    _content: FileContent | None = field(default=None, init=False)

    def read(self) -> str:
        """Fetch the file and hold on to the sha for the write."""
        self._content = self.client.read(
            self.repository, self.path, self.branch
        )
        return self._content.text

    def write(self, text: str, message: str) -> None:
        """Commit the new text against the sha from this run's read."""
        if self._content is None:
            raise RuntimeError(
                f'{self.describe()} must be read before it can be written'
            )
        self.client.write(
            repository=self.repository,
            path=self.path,
            content=FileContent(text=text, sha=self._content.sha),
            message=message,
            branch=self.branch,
            committer=self.committer,
            author=self.author,
        )

    def describe(self) -> str:
        """Name the file and the repository it lives in."""
        return f'{self.path} in {self.repository}'
