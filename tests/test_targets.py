#!/usr/bin/env python3
"""Tests for the two places a document can live."""

from __future__ import annotations

from pathlib import Path

import pytest

from wakatime_readme.github import FileContent
from wakatime_readme.targets import GitHubFile, LocalFile

CRLF = 'line one\r\nline two\r\n'
LF = 'line one\nline two\n'


class RecordingGitHub:
    """A GitHub client that hands back canned text and records writes."""

    def __init__(self, text: str = '# Title\n', sha: str = 'sha-1') -> None:
        self._content = FileContent(text, sha)
        self.reads: list[tuple[str, str, str]] = []
        self.writes: list[dict[str, object]] = []

    def read(self, repository: str, path: str, ref: str = '') -> FileContent:
        """Return the canned file, noting what was asked for."""
        self.reads.append((repository, path, ref))
        return self._content

    def write(self, **kwargs: object) -> None:
        """Record the commit that would have been made."""
        self.writes.append(kwargs)


def test_local_file_round_trips_lf(tmp_path: Path) -> None:
    path = tmp_path / 'README.md'
    path.write_bytes(LF.encode('utf-8'))

    target = LocalFile(path)
    target.write(target.read(), 'noop')

    assert path.read_bytes() == LF.encode('utf-8')


def test_local_file_round_trips_crlf(tmp_path: Path) -> None:
    # Rewriting one word must not reflow every line in the diff, so the
    # line endings that came in have to be the ones that go back out.
    path = tmp_path / 'README.md'
    path.write_bytes(CRLF.encode('utf-8'))

    target = LocalFile(path)
    target.write(target.read(), 'noop')

    assert path.read_bytes() == CRLF.encode('utf-8')


def test_local_file_reports_its_path(tmp_path: Path) -> None:
    path = tmp_path / 'README.md'

    assert LocalFile(path).describe() == str(path)


def test_local_file_missing_on_disk_raises(tmp_path: Path) -> None:
    with pytest.raises(OSError, match=r'README\.md'):
        LocalFile(tmp_path / 'README.md').read()


def test_github_file_returns_the_remote_text() -> None:
    client = RecordingGitHub('# Remote\n')

    text = GitHubFile(client, 'owner/repo', 'README.md').read()  # type: ignore[arg-type]

    assert text == '# Remote\n'


def test_github_file_commits_with_the_sha_from_its_read() -> None:
    client = RecordingGitHub(sha='sha-from-read')
    target = GitHubFile(client, 'owner/repo', 'README.md')  # type: ignore[arg-type]

    target.read()
    target.write('# New\n', 'a message')

    written = client.writes[0]
    content = written['content']
    assert isinstance(content, FileContent)
    assert content.sha == 'sha-from-read'
    assert content.text == '# New\n'
    assert written['message'] == 'a message'


def test_github_file_passes_the_branch_through() -> None:
    client = RecordingGitHub()
    target = GitHubFile(client, 'owner/repo', 'README.md', branch='master')  # type: ignore[arg-type]

    target.read()
    target.write('x', 'm')

    assert client.reads[0][2] == 'master'
    assert client.writes[0]['branch'] == 'master'


def test_github_file_refuses_to_write_before_reading() -> None:
    # Without a read there is no sha, and a write without one would be
    # rejected by the API anyway. Failing here says why.
    target = GitHubFile(RecordingGitHub(), 'owner/repo', 'README.md')  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match='must be read'):
        target.write('x', 'm')


def test_github_file_names_both_the_path_and_the_repository() -> None:
    target = GitHubFile(RecordingGitHub(), 'owner/repo', 'docs/README.md')  # type: ignore[arg-type]

    assert target.describe() == 'docs/README.md in owner/repo'
