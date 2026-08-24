#!/usr/bin/env python3
"""What each placeholder name resolves to.

A registry of small functions over the two clients. Adding a metric is
one function plus one entry, never a change to the parser.

The clients are optional on the context: a file that only asks for
GitHub numbers should not require a WakaTime key, so a metric whose
provider is missing says which credential to supply instead of failing
somewhere deeper.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from .formatters import Value
from .github import Profile, Repository
from .wakatime import SECONDS_PER_HOUR, Stats


class StatsSource(Protocol):
    """The slice of the WakaTime client the metrics actually use."""

    def stats(self, range_name: str) -> Stats:
        """Return one range of coding activity."""
        ...


class ProfileSource(Protocol):
    """The slice of the GitHub client the metrics actually use."""

    def profile(self) -> Profile:
        """Return the account's public profile."""
        ...

    def repositories(self) -> tuple[Repository, ...]:
        """Return every public repository, most starred first."""
        ...

    def repository(self, full_name: str) -> Repository:
        """Return one repository by its `owner/name`."""
        ...

    def latest_release(self, full_name: str) -> str:
        """Return the tag of the most recent release."""
        ...


class MetricError(ValueError):
    """A placeholder cannot be resolved as written."""


@dataclass(frozen=True)
class Context:
    """Everything a metric is allowed to reach for.

    Example:
        >>> Context(None, None, 'all_time').range_name
        'all_time'
    """

    wakatime: StatsSource | None
    github: ProfileSource | None
    range_name: str


Metric = Callable[[Context, str | None], Value]


def _stats(context: Context) -> Stats:
    """Get the configured range, or say which credential is missing."""
    if context.wakatime is None:
        raise MetricError(
            'this placeholder needs WakaTime data; '
            'set WAKATIME_API_KEY to use it'
        )
    return context.wakatime.stats(context.range_name)


def _github(context: Context) -> ProfileSource:
    """Get the GitHub client, or say which setting is missing."""
    if context.github is None:
        raise MetricError(
            'this placeholder needs GitHub data; '
            'set a repository or username to use it'
        )
    return context.github


def _named(arg: str | None, metric: str) -> str:
    """Insist on the argument a metric cannot work without."""
    if not arg:
        raise MetricError(
            f'{metric} needs an argument, as in <!--wr:{metric}:VALUE-->'
        )
    return arg


def _rank(arg: str | None, metric: str) -> int:
    """Read the optional 1-based rank a ranking metric accepts."""
    if not arg:
        return 1
    try:
        return int(arg)
    except ValueError as error:
        raise MetricError(
            f'{metric} takes a whole number, received {arg!r}'
        ) from error


def _lang_hours(context: Context, arg: str | None) -> Value:
    """Hours logged in one language over the configured range."""
    return _stats(context).language(_named(arg, 'lang_hours')).hours


def _lang_percent(context: Context, arg: str | None) -> Value:
    """Share of the range one language accounts for."""
    return _stats(context).language(_named(arg, 'lang_percent')).percent


def _lang_text(context: Context, arg: str | None) -> Value:
    """One language's time in the API's own phrasing."""
    return _stats(context).language(_named(arg, 'lang_text')).text


def _total_hours(context: Context, arg: str | None) -> Value:
    """Hours logged across every language."""
    return _stats(context).hours


def _top_lang(context: Context, arg: str | None) -> Value:
    """Name of the nth most-used language."""
    return _stats(context).ranked(_rank(arg, 'top_lang')).name


def _daily_average(context: Context, arg: str | None) -> Value:
    """Average hours per day over the range."""
    return _stats(context).daily_average / SECONDS_PER_HOUR


def _since(context: Context, arg: str | None) -> Value:
    """First day of the range."""
    return _stats(context).since


def _gh_followers(context: Context, arg: str | None) -> Value:
    """How many accounts follow this one."""
    return _github(context).profile().followers


def _gh_repos(context: Context, arg: str | None) -> Value:
    """How many public repositories the account has."""
    return _github(context).profile().public_repos


def _gh_stars(context: Context, arg: str | None) -> Value:
    """Stars across every public repository."""
    listing = _github(context).repositories()
    return sum(repository.stars for repository in listing)


def _gh_top_repo(context: Context, arg: str | None) -> Value:
    """Name of the nth most-starred repository."""
    rank = _rank(arg, 'gh_top_repo')
    listing = _github(context).repositories()
    if rank < 1 or rank > len(listing):
        raise MetricError(
            f'no repository at rank {rank}; this account has {len(listing)}'
        )
    return listing[rank - 1].name


def _gh_repo_stars(context: Context, arg: str | None) -> Value:
    """Stars on one named repository."""
    name = _named(arg, 'gh_repo_stars')
    return _github(context).repository(name).stars


def _gh_latest_release(context: Context, arg: str | None) -> Value:
    """Tag of the most recent release of one named repository."""
    name = _named(arg, 'gh_latest_release')
    return _github(context).latest_release(name)


METRICS: dict[str, Metric] = {
    'lang_hours': _lang_hours,
    'lang_percent': _lang_percent,
    'lang_text': _lang_text,
    'total_hours': _total_hours,
    'top_lang': _top_lang,
    'daily_average': _daily_average,
    'since': _since,
    'gh_followers': _gh_followers,
    'gh_repos': _gh_repos,
    'gh_stars': _gh_stars,
    'gh_top_repo': _gh_top_repo,
    'gh_repo_stars': _gh_repo_stars,
    'gh_latest_release': _gh_latest_release,
}

# Which provider each metric reaches for, so callers can tell in advance
# whether a file needs a given credential at all.
GITHUB_PREFIX = 'gh_'


def needs_github(name: str) -> bool:
    """Say whether a metric reads GitHub rather than WakaTime.

    Example:
        >>> needs_github('gh_stars'), needs_github('lang_hours')
        (True, False)
    """
    return name.startswith(GITHUB_PREFIX)


def resolve(context: Context, name: str, arg: str | None) -> Value:
    """Look up one metric and run it.

    Example:
        >>> resolve(Context(None, None, 'all_time'), 'nope', None)
        Traceback (most recent call last):
        wakatime_readme.metrics.MetricError: unknown metric: 'nope'
    """
    metric = METRICS.get(name)
    if metric is None:
        raise MetricError(f'unknown metric: {name!r}')
    return metric(context, arg)
