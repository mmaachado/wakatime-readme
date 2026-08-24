#!/usr/bin/env python3
"""Command-line entry point: parse, wire, report, choose an exit code.

No decision about metrics or formatting lives here. This module reads
the configuration, assembles the pieces, and translates whatever comes
back into a status a workflow can act on.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TextIO

from .config import ConfigError, Settings, settings_from
from .formatters import FormatError
from .github import ConflictError, GitHubClient
from .http import HttpError
from .metrics import Context, MetricError
from .rewriter import (
    Placeholder,
    Rewrite,
    apply,
    find,
    uses_github,
    uses_wakatime,
)
from .targets import GitHubFile, LocalFile, Target
from .wakatime import StaleStats, WakaTimeClient

OK = 0
CONFIG_ERROR = 1
DATA_UNAVAILABLE = 2

# Raised when the author wrote something the tool cannot honour. These
# will not fix themselves on the next scheduled run, so they fail loudly.
AUTHORING_ERRORS = (ConfigError, MetricError, FormatError, LookupError)

# Raised when the data simply is not there yet. A nightly job should not
# turn red because an API was briefly busy.
TRANSIENT_ERRORS = (StaleStats, HttpError, ConflictError)


def _warn(stream: TextIO, message: str, env: Mapping[str, str]) -> None:
    """Report something worth noticing, annotated when inside a workflow."""
    if env.get('GITHUB_ACTIONS'):
        print(f'::warning::{message}', file=stream)
    else:
        print(f'warning: {message}', file=stream)


def _github_client(settings: Settings) -> GitHubClient:
    """Build the GitHub client, insisting on knowing whose data to read."""
    if not settings.username:
        raise ConfigError(
            'GitHub data needs an account; pass --username or --repo'
        )
    return GitHubClient(
        settings.github_token, settings.username, settings.github_url
    )


def _target(settings: Settings, github: GitHubClient | None) -> Target:
    """Choose between editing a local file and committing to a repository."""
    if github is not None and settings.writes_to_github:
        return GitHubFile(
            client=github,
            repository=settings.repository,
            path=settings.readme_path,
            branch=settings.branch,
            committer=settings.committer,
            author=settings.author,
        )
    return LocalFile(Path(settings.readme_path))


def _context(
    settings: Settings,
    placeholders: tuple[Placeholder, ...],
    github: GitHubClient | None,
) -> Context:
    """Wire up only the providers this document actually calls for."""
    wakatime = None
    if uses_wakatime(placeholders):
        if not settings.wakatime_api_key:
            raise ConfigError(
                'this file has WakaTime placeholders but no API key; '
                'set WAKATIME_API_KEY'
            )
        wakatime = WakaTimeClient(
            settings.wakatime_api_key,
            settings.wakatime_url,
            settings.retries,
        )

    metrics_github = None
    if uses_github(placeholders):
        metrics_github = (
            github if github is not None else _github_client(settings)
        )

    return Context(
        wakatime=wakatime,
        github=metrics_github,
        range_name=settings.range_name,
    )


def _report(result: Rewrite, target: Target, stream: TextIO) -> None:
    """Print what each placeholder resolved to, changing nothing."""
    print(f'{target.describe()}:', file=stream)
    if not result.resolutions:
        print('  (no placeholders)', file=stream)
        return
    width = max(len(item.placeholder.spec) for item in result.resolutions)
    for item in result.resolutions:
        mark = '*' if item.changed else ' '
        rendered = item.rendered.replace('\n', '\\n')
        if len(rendered) > 60:
            rendered = f'{rendered[:57]}...'
        spec = item.placeholder.spec.ljust(width)
        print(f'  {mark} {spec}  ->  {rendered}', file=stream)


def _once(
    settings: Settings,
    github: GitHubClient | None,
    out: TextIO,
    err: TextIO,
    env: Mapping[str, str],
) -> int:
    """Read, resolve and write a single time through."""
    target = _target(settings, github)
    text = target.read()
    placeholders = find(text)

    if not placeholders:
        _warn(err, f'no placeholders found in {target.describe()}', env)
        return OK

    context = _context(settings, placeholders, github)
    result = apply(text, context, settings.chart)

    if settings.dry_run:
        _report(result, target, out)
        return OK

    if not result.changed:
        print(f'{target.describe()} is already up to date', file=err)
        return OK

    target.write(result.text, settings.commit_message)
    print(f'updated {target.describe()}', file=err)
    return OK


def _attempt(
    settings: Settings,
    out: TextIO,
    err: TextIO,
    env: Mapping[str, str],
) -> int:
    """Run once, and once more if the file moved under us mid-flight."""
    github = _github_client(settings) if settings.writes_to_github else None
    try:
        return _once(settings, github, out, err, env)
    except ConflictError:
        _warn(err, 'the file changed while we worked; starting over', env)

    # Deliberately rebuild everything. Re-reading gives a fresh sha, and
    # re-resolving means the retry lands on top of whatever arrived
    # rather than overwriting it.
    fresh = _github_client(settings) if settings.writes_to_github else None
    return _once(settings, fresh, out, err, env)


def main(
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    """Run the tool and return the status the caller should exit with."""
    env = os.environ if env is None else env
    out = sys.stdout if out is None else out
    err = sys.stderr if err is None else err

    # Settled first and on its own, so the handlers below can rely on
    # `settings` existing when they need to read it.
    try:
        settings = settings_from(argv, env)
    except ConfigError as error:
        print(f'error: {error}', file=err)
        return CONFIG_ERROR

    try:
        return _attempt(settings, out, err, env)
    except AUTHORING_ERRORS as error:
        print(f'error: {error}', file=err)
        return CONFIG_ERROR
    except OSError as error:
        print(f'error: {error}', file=err)
        return CONFIG_ERROR
    except TRANSIENT_ERRORS as error:
        _warn(err, f'{error}; leaving the file alone', env)
        return DATA_UNAVAILABLE if settings.strict else OK


if __name__ == '__main__':
    raise SystemExit(main())
