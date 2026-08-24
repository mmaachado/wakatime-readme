#!/usr/bin/env python3
"""Stand-ins for the two data sources, for tests above the client layer."""

from __future__ import annotations

from wakatime_readme.github import Profile, Repository
from wakatime_readme.wakatime import Language, Stats

SAMPLE_LANGUAGES = (
    Language('Python', 3_100_000.0, 57.41, '861 hrs 6 mins'),
    Language('Markdown', 1_200_000.0, 22.22, '333 hrs 20 mins'),
    Language('HTML', 600_000.0, 11.11, '166 hrs 40 mins'),
)

SAMPLE_STATS = Stats(
    total_seconds=5_400_000.0,
    daily_average=7200.0,
    start=None,
    human_range='since Jan 01 2020',
    languages=SAMPLE_LANGUAGES,
)


class StubWakaTime:
    """Answers with one canned range and records what was asked for."""

    def __init__(self, stats: Stats = SAMPLE_STATS) -> None:
        self._stats = stats
        self.ranges: list[str] = []

    def stats(self, range_name: str) -> Stats:
        """Return the canned range, noting which one was requested."""
        self.ranges.append(range_name)
        return self._stats


class StubGitHub:
    """Answers with canned profile and repository data."""

    def __init__(
        self,
        profile: Profile | None = None,
        repositories: tuple[Repository, ...] = (),
        release: str = 'v1.2.3',
    ) -> None:
        self._profile = profile or Profile('octocat', 'The Octocat', 42, 8, 3)
        self._repositories = repositories or (
            Repository('hello-world', 'octocat/hello-world', 12, fork=False),
            Repository('spoon-knife', 'octocat/spoon-knife', 7, fork=False),
            Repository('dotfiles', 'octocat/dotfiles', 3, fork=False),
        )
        self._release = release
        self.calls: list[str] = []

    def profile(self) -> Profile:
        """Return the canned profile."""
        self.calls.append('profile')
        return self._profile

    def repositories(self) -> tuple[Repository, ...]:
        """Return the canned listing, most starred first."""
        self.calls.append('repositories')
        return self._repositories

    def repository(self, full_name: str) -> Repository:
        """Return one canned repository by name."""
        self.calls.append(f'repository:{full_name}')
        for repository in self._repositories:
            if repository.full_name == full_name:
                return repository
        raise LookupError(f'no such repository: {full_name}')

    def latest_release(self, full_name: str) -> str:
        """Return the canned release tag."""
        self.calls.append(f'release:{full_name}')
        return self._release


class ExplodingWakaTime:
    """A stats source that fails the test if anything reaches it."""

    def stats(self, range_name: str) -> Stats:
        """Never returns; being called at all is the failure."""
        message = (
            f'WakaTime was consulted for {range_name!r} '
            f'but should not have been'
        )
        raise AssertionError(message)
