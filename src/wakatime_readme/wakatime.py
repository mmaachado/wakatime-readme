#!/usr/bin/env python3
"""WakaTime client and the stats model the metrics read from.

Nothing is fetched until a metric asks for it, and each range is fetched
at most once per run.
"""

from __future__ import annotations

import base64
import time
import urllib.parse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from .http import ACCEPTED, HttpError, JsonClient, Redactor

BASE_URL = 'https://wakatime.com/api/v1'
DEFAULT_RANGE = 'all_time'

# Minutes of pause that still count as coding. WakaTime keeps a
# per-account default and applies it whenever the request leaves the
# parameter out, but its own public profile pages render with 15.
# Inheriting the account value published totals about a third below what
# the profile advertised, so this is always sent explicitly now.
DEFAULT_KEYSTROKE_TIMEOUT = 15

# Attempts, and the total seconds they may spend asleep between them.
# Only a keystroke timeout WakaTime has already computed answers at once;
# any other comes back `202` with `percent_calculated: 0` and needs real
# time, which the previous budget of three seconds never gave it.
DEFAULT_RETRIES = 6
RETRY_BUDGET_SECONDS = 30.0

UNAUTHORIZED = 401
FORBIDDEN = 403
SECONDS_PER_HOUR = 3600.0
COMPLETE = 100.0


class StaleStats(Exception):
    """WakaTime is still recomputing, so no value can be trusted yet.

    Free plans recompute ranges of a year or more on first request. The
    documented advice is to check `is_up_to_date` and retry; when the
    retries run out we raise this rather than write a number we do not
    believe.

    `is_up_to_date` alone is not enough to tell that apart from a final
    answer -- see `_settled`.
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


def _settled(payload: dict[str, Any]) -> bool:
    """Say whether a stats payload is final enough to publish.

    WakaTime computes long ranges lazily, and while it works it answers
    `200` with real-looking but partial numbers. `is_up_to_date` can
    already be true while `percent_calculated` is still climbing, so
    both have to agree before the answer is worth writing down.

    Example:
        >>> _settled({'is_up_to_date': True, 'percent_calculated': 100})
        True
        >>> _settled({'is_up_to_date': True, 'percent_calculated': 67})
        False
        >>> _settled({})
        False
    """
    if not payload:
        return False
    if not payload.get('is_up_to_date', True):
        return False
    return float(payload.get('percent_calculated', COMPLETE)) >= COMPLETE


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
        retries: int = DEFAULT_RETRIES,
        sleep: Callable[[float], None] | None = None,
        keystroke_timeout: int = DEFAULT_KEYSTROKE_TIMEOUT,
        budget: float = RETRY_BUDGET_SECONDS,
    ) -> None:
        """Prepare the client without contacting anything yet."""
        self.base_url = base_url
        self.retries = retries
        self.keystroke_timeout = keystroke_timeout
        self.budget = budget
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

    def _poll(self, range_name: str) -> dict[str, Any]:
        """Ask once, answering with `{}` when there is nothing usable."""
        # Sent on every request rather than left to the account default:
        # the default is what made the published totals disagree with the
        # profile page they were supposed to mirror.
        query = urllib.parse.urlencode({'timeout': self.keystroke_timeout})
        response = self._client.request(
            'GET', f'/users/current/stats/{range_name}?{query}'
        )
        if response.status in (UNAUTHORIZED, FORBIDDEN):
            raise self._client.fail(
                'WakaTime rejected the API key', response.status
            )
        if response.status >= ACCEPTED:
            return {}
        return (response.body or {}).get('data') or {}

    def _fetch(self, range_name: str) -> Stats:
        """Request a range, retrying while the answer is not settled."""
        seen = 'an unknown share'
        spent = 0.0
        for attempt in range(self.retries):
            payload = self._poll(range_name)
            if _settled(payload):
                return _stats(payload)
            share = payload.get('percent_calculated')
            if share is not None:
                seen = f'{share}%'
            spent = self._wait(attempt, spent)

        raise StaleStats(
            f'WakaTime is still computing {range_name!r} at keystroke '
            f'timeout {self.keystroke_timeout} after {self.retries} '
            f'attempts across {spent:.0f}s; the last answer covered '
            f'{seen} of the range, not {COMPLETE:.0f}%'
        )

    def _wait(self, attempt: int, spent: float) -> float:
        """Back off, never after the last attempt nor past the budget.

        Returns the seconds slept so far, so the caller can report how
        long it actually waited before giving up.
        """
        if attempt >= self.retries - 1:
            return spent
        delay = min(2.0**attempt, self.budget - spent)
        if delay <= 0:
            return spent
        self._sleep(delay)
        return spent + delay


def unavailable(error: Exception) -> bool:
    """Say whether an error means "no trustworthy data right now".

    Those are the failures that exit 0 with a warning by default, rather
    than failing the whole workflow.

    Example:
        >>> unavailable(StaleStats('still computing'))
        True
    """
    return isinstance(error, (StaleStats, HttpError))
