#!/usr/bin/env python3
"""Stand-ins for the two data sources, for tests above the client layer."""

from __future__ import annotations

from wakatime_readme.github import Profile, Repository
from wakatime_readme.wakatime import Language, Stats

SAMPLE_LANGUAGES = (
    Language('Python', 3212992.0, 46.27, '892 hrs 29 mins'),
    Language('Markdown', 2459788.0, 35.42, '683 hrs 16 mins'),
    Language('HTML', 215602.0, 3.10, '59 hrs 53 mins'),
)

SAMPLE_STATS = Stats(
    total_seconds=6850967.0,
    daily_average=8750.0,
    start=None,
    human_range='since Mar 30 2023',
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
        self._profile = profile or Profile('mmaachado', 'Marcelo', 27, 20, 1)
        self._repositories = repositories or (
            Repository('sycp', 'mmaachado/sycp', 29, fork=False),
            Repository(
                'django-shadcn', 'mmaachado/django-shadcn', 1, fork=False
            ),
            Repository('dotfiles', 'mmaachado/dotfiles', 1, fork=False),
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
