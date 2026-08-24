#!/usr/bin/env python3
"""WakaTime client and the stats model the metrics read from.

Nothing is fetched until a metric asks for it, and each range is fetched
at most once per run.
"""

from __future__ import annotations

import base64
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from .http import ACCEPTED, HttpError, JsonClient, Redactor

BASE_URL = 'https://wakatime.com/api/v1'
DEFAULT_RANGE = 'all_time'

UNAUTHORIZED = 401
FORBIDDEN = 403
SECONDS_PER_HOUR = 3600.0


class StaleStats(Exception):
    """WakaTime is still recomputing, so no value can be trusted yet.

    Free plans recompute ranges of a year or more on first request. The
    documented advice is to check `is_up_to_date` and retry; when the
    retries run out we raise this rather than write a number we do not
    believe.
    """


@dataclass(frozen=True)
class Language:
    """One language's slice of a range.

    Example:
        >>> Language('Python', 3212992.0, 46.27, '892 hrs 29 mins').hours
        892.4977777777778
    """

    name: str
    total_seconds: float
    percent: float
    text: str

    @property
    def hours(self) -> float:
        """Seconds expressed as hours."""
        return self.total_seconds / SECONDS_PER_HOUR


@dataclass(frozen=True)
class Stats:
    """A whole range of coding activity.

    Example:
        >>> Stats(3600.0, 60.0, None, 'since Mar 30 2023', ()).since
        'Mar 30 2023'
    """

    total_seconds: float
    daily_average: float
    # Bounded ranges carry an ISO start; `all_time` carries null for both
    # `start` and `end`, and expresses itself only in prose.
    start: str | None
    human_range: str
    languages: tuple[Language, ...]

    @property
    def hours(self) -> float:
        """Total seconds expressed as hours."""
        return self.total_seconds / SECONDS_PER_HOUR

    @property
    def since(self) -> str:
        """The first day of the range, however the API expressed it.

        Example:
            >>> Stats(0.0, 0.0, '2024-01-05', '', ()).since
            '2024-01-05'
        """
        if self.start:
            return self.start
        return self.human_range.removeprefix('since ')

    def language(self, name: str) -> Language:
        """Find one language by name, case-insensitively.

        Raises:
            LookupError: naming the language and what was available, so a
                typo in a placeholder is obvious from the message alone.
        """
        wanted = name.casefold()
        for language in self.languages:
            if language.name.casefold() == wanted:
                return language
        raise LookupError(
            f'no WakaTime data for language {name!r}; '
            f'this range has {[lang.name for lang in self.languages]}'
        )

    def ranked(self, rank: int) -> Language:
        """Return the nth language by time, 1-based.

        Raises:
            LookupError: when the range holds fewer languages than that.
        """
        if rank < 1 or rank > len(self.languages):
            raise LookupError(
                f'no language at rank {rank}; this range has '
                f'{len(self.languages)}'
            )
        return self.languages[rank - 1]


def _language(payload: dict[str, Any]) -> Language:
    """Build a language from one entry of the API's `languages` array."""
    return Language(
        name=str(payload['name']),
        total_seconds=float(payload.get('total_seconds', 0.0)),
        percent=float(payload.get('percent', 0.0)),
        text=str(payload.get('text', '')),
    )


def _stats(payload: dict[str, Any]) -> Stats:
    """Build the stats model from the `data` object of a stats response."""
    languages: Sequence[dict[str, Any]] = payload.get('languages', [])
    start = payload.get('start')
    return Stats(
        total_seconds=float(payload.get('total_seconds', 0.0)),
        daily_average=float(payload.get('daily_average', 0.0)),
        start=str(start)[:10] if start else None,
        human_range=str(payload.get('human_readable_range', '')),
        languages=tuple(_language(entry) for entry in languages),
    )


class WakaTimeClient:
    """Reads coding activity, retrying while the API recomputes.

    Example:
        >>> WakaTimeClient('key').base_url
        'https://wakatime.com/api/v1'
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = BASE_URL,
        retries: int = 3,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        """Prepare the client without contacting anything yet."""
        self.base_url = base_url
        self.retries = retries
        # Looked up now rather than bound as a default argument, so a
        # test can replace the clock without reaching into the instance.
        self._sleep = sleep if sleep is not None else time.sleep
        self._cache: dict[str, Stats] = {}
        # The key goes into the Authorization header and nowhere else, and
        # is registered for redaction so it cannot surface in an error.
        credential = base64.b64encode(api_key.encode('utf-8')).decode()
        self._client = JsonClient(
            base_url=base_url,
            headers={'Authorization': f'Basic {credential}'},
            redactor=Redactor((api_key, credential)),
        )

    def stats(self, range_name: str = DEFAULT_RANGE) -> Stats:
        """Return one range, fetching it at most once per run."""
        if range_name not in self._cache:
            self._cache[range_name] = self._fetch(range_name)
        return self._cache[range_name]

    def _fetch(self, range_name: str) -> Stats:
        """Request a range, retrying while the answer is not settled."""
        for attempt in range(self.retries):
            response = self._client.request(
                'GET', f'/users/current/stats/{range_name}'
            )
            if response.status in (UNAUTHORIZED, FORBIDDEN):
                raise self._client.fail(
                    'WakaTime rejected the API key', response.status
                )
            if response.status >= ACCEPTED:
                self._wait(attempt)
                continue

            payload = (response.body or {}).get('data') or {}
            if payload.get('is_up_to_date', True):
                return _stats(payload)
            self._wait(attempt)

        raise StaleStats(
            f'WakaTime is still recomputing {range_name!r} after '
            f'{self.retries} attempts'
        )

    def _wait(self, attempt: int) -> None:
        """Back off between attempts, but never after the last one."""
        if attempt < self.retries - 1:
            self._sleep(2.0**attempt)


def unavailable(error: Exception) -> bool:
    """Say whether an error means "no trustworthy data right now".

    Those are the failures that exit 0 with a warning by default, rather
    than failing the whole workflow.

    Example:
        >>> unavailable(StaleStats('still computing'))
        True
    """
    return isinstance(error, (StaleStats, HttpError))
