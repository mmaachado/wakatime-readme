#!/usr/bin/env python3
"""Turning arguments and environment into one settled configuration.

Precedence is explicit argument, then action input, then plain
environment variable, then default. It is expressed once, by seeding
each argument's default from the environment, so there is no second
place where the rules could drift.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from .blocks import DEFAULT_BLOCKS, ChartOptions
from .github import BASE_URL as GITHUB_URL
from .targets import DEFAULT_MESSAGE
from .wakatime import BASE_URL as WAKATIME_URL
from .wakatime import DEFAULT_RANGE

TRUTHY = frozenset({'1', 'true', 'yes', 'on'})
DEFAULT_README = 'README.md'
DEFAULT_RETRIES = 3


class ConfigError(ValueError):
    """The configuration cannot be used as given."""


@dataclass(frozen=True)
class Settings:
    """Everything one run needs to know.

    The two credentials are kept out of the generated repr. A settings
    object ends up in tracebacks and debug output, and a dataclass will
    happily print every field it holds.
    """

    readme_path: str
    repository: str
    branch: str
    username: str
    range_name: str
    retries: int
    strict: bool
    dry_run: bool
    commit_message: str
    committer: dict[str, str] | None
    author: dict[str, str] | None
    wakatime_url: str
    github_url: str
    chart: ChartOptions
    wakatime_api_key: str = field(default='', repr=False)
    github_token: str = field(default='', repr=False)

    @property
    def writes_to_github(self) -> bool:
        """Whether the document lives in a repository rather than on disk.

        Example:
            >>> bool('owner/repo')
            True
        """
        return bool(self.repository)


def _env(env: Mapping[str, str], name: str, default: str = '') -> str:
    """Read a setting, preferring an action input over a plain variable."""
    upper = name.upper()
    return env.get(f'INPUT_{upper}') or env.get(upper) or default


def _flag(env: Mapping[str, str], name: str, default: bool = False) -> bool:
    """Read a boolean setting the way workflow inputs express one."""
    raw = _env(env, name)
    if not raw:
        return default
    return raw.strip().lower() in TRUTHY


def _people(name: str, email: str) -> dict[str, str] | None:
    """Build a commit identity, or nothing when it was left unset."""
    if name and email:
        return {'name': name, 'email': email}
    if name or email:
        raise ConfigError(
            'a commit identity needs both a name and an email; '
            f'received name={name!r} email={email!r}'
        )
    return None


def _owner_of(repository: str) -> str:
    """Take the account name out of an `owner/name` pair."""
    owner, _, remainder = repository.partition('/')
    if not owner or not remainder:
        raise ConfigError(
            f'a repository looks like owner/name, received {repository!r}'
        )
    return owner


def build_parser(env: Mapping[str, str]) -> argparse.ArgumentParser:
    """Describe the command line, seeding defaults from the environment."""
    parser = argparse.ArgumentParser(
        prog='wakatime-readme',
        description=(
            'Fill named placeholders in a Markdown file with live '
            'WakaTime and GitHub metrics.'
        ),
    )
    boolean = argparse.BooleanOptionalAction

    parser.add_argument(
        '--readme', default=_env(env, 'readme_path', DEFAULT_README)
    )
    parser.add_argument(
        '--repo',
        default=_env(env, 'repository') or env.get('GITHUB_REPOSITORY', ''),
        help='owner/name; without it the local file is edited in place',
    )
    parser.add_argument('--branch', default=_env(env, 'branch'))
    parser.add_argument('--username', default=_env(env, 'username'))
    parser.add_argument(
        '--range', default=_env(env, 'time_range', DEFAULT_RANGE)
    )
    parser.add_argument(
        '--retries', type=int, default=int(_env(env, 'retries', '0') or 0)
    )
    parser.add_argument(
        '--strict', action=boolean, default=_flag(env, 'strict')
    )
    parser.add_argument(
        '--dry-run', action=boolean, default=_flag(env, 'dry_run')
    )
    parser.add_argument(
        '--message', default=_env(env, 'commit_message', DEFAULT_MESSAGE)
    )
    parser.add_argument(
        '--committer-name', default=_env(env, 'committer_name')
    )
    parser.add_argument(
        '--committer-email', default=_env(env, 'committer_email')
    )
    parser.add_argument('--author-name', default=_env(env, 'author_name'))
    parser.add_argument('--author-email', default=_env(env, 'author_email'))
    parser.add_argument(
        '--wakatime-url', default=_env(env, 'api_base_url', WAKATIME_URL)
    )
    parser.add_argument(
        '--github-url', default=_env(env, 'github_api_url', GITHUB_URL)
    )

    chart = parser.add_argument_group('chart')
    chart.add_argument('--blocks', default=_env(env, 'blocks', DEFAULT_BLOCKS))
    chart.add_argument(
        '--code-lang', default=_env(env, 'code_lang', 'markdown')
    )
    chart.add_argument(
        '--lang-count', type=int, default=int(_env(env, 'lang_count', '5'))
    )
    chart.add_argument(
        '--ignore',
        default=_env(env, 'ignored_languages'),
        help='space-separated language names to leave out of the chart',
    )
    chart.add_argument(
        '--stop-at-other',
        action=boolean,
        default=_flag(env, 'stop_at_other'),
    )
    chart.add_argument(
        '--show-time', action=boolean, default=_flag(env, 'show_time', True)
    )
    chart.add_argument(
        '--show-total', action=boolean, default=_flag(env, 'show_total', True)
    )
    return parser


def _chart(options: argparse.Namespace) -> ChartOptions:
    """Collect the chart settings out of the parsed arguments."""
    return ChartOptions(
        blocks=options.blocks,
        code_lang=options.code_lang,
        lang_count=options.lang_count,
        ignored_languages=frozenset(options.ignore.split()),
        stop_at_other=options.stop_at_other,
        show_time=options.show_time,
        show_total=options.show_total,
    )


def settings_from(
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> Settings:
    """Resolve one run's configuration.

    Example:
        >>> settings_from([], {}).readme_path
        'README.md'
    """
    env = os.environ if env is None else env
    options = build_parser(env).parse_args(argv)

    repository = options.repo.strip()
    username = options.username.strip()
    if not username and repository:
        # The workflow token belongs to a bot, so the account whose
        # metrics we want has to come from the repository instead.
        username = _owner_of(repository)

    return Settings(
        readme_path=options.readme,
        repository=repository,
        branch=options.branch.strip(),
        username=username,
        range_name=options.range,
        retries=options.retries or DEFAULT_RETRIES,
        strict=options.strict,
        dry_run=options.dry_run,
        commit_message=options.message,
        committer=_people(options.committer_name, options.committer_email),
        author=_people(options.author_name, options.author_email),
        wakatime_url=options.wakatime_url,
        github_url=options.github_url,
        chart=_chart(options),
        wakatime_api_key=_env(env, 'wakatime_api_key'),
        github_token=_env(env, 'github_token'),
    )
