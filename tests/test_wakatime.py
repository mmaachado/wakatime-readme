#!/usr/bin/env python3
"""Tests for the WakaTime client, against a real captured response."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.helpers import FakeTransport, Payload, ok
from wakatime_readme.http import HttpError
from wakatime_readme.wakatime import StaleStats, WakaTimeClient

Install = Callable[..., FakeTransport]

API_KEY = 'waka_secret-key-value'


def client(retries: int = 3) -> WakaTimeClient:
    """Build a client whose backoff never actually sleeps."""
    return WakaTimeClient(API_KEY, retries=retries, sleep=lambda _s: None)


def test_parses_the_real_payload(
    transport: Install, all_time: Payload
) -> None:
    transport(ok(all_time))

    python = client().stats().language('Python')

    # Fixture values, chosen so the arithmetic is easy to check by
    # hand when this fails: 3.1M seconds is 861.11 hours.
    assert python.total_seconds == pytest.approx(3_100_000.0)
    assert python.hours == pytest.approx(861.1111, abs=1e-3)
    assert python.percent == pytest.approx(57.41)
    assert python.text == '861 hrs 6 mins'


def test_reads_the_overall_total(
    transport: Install, all_time: Payload
) -> None:
    transport(ok(all_time))

    assert client().stats().hours == pytest.approx(1500.0, abs=0.01)


def test_since_falls_back_to_the_prose_range(
    transport: Install, all_time: Payload
) -> None:
    # Regression: the all_time response carries `start: null` and states
    # the range only as 'since Mar 30 2023'. Reading `start` blindly used
    # to render the literal string 'None' into the README.
    transport(ok(all_time))

    assert client().stats().since == 'Jan 01 2020'


def test_language_lookup_ignores_case(
    transport: Install, all_time: Payload
) -> None:
    transport(ok(all_time))

    assert client().stats().language('python').name == 'Python'


def test_missing_language_names_what_was_available(
    transport: Install, all_time: Payload
) -> None:
    transport(ok(all_time))
    stats = client().stats()

    with pytest.raises(LookupError) as caught:
        stats.language('Brainfuck')

    message = str(caught.value)
    assert "'Brainfuck'" in message
    assert 'Python' in message


def test_ranks_languages_by_time(
    transport: Install, all_time: Payload
) -> None:
    transport(ok(all_time))
    stats = client().stats()

    assert stats.ranked(1).name == 'Python'
    assert stats.ranked(2).name == 'Markdown'


def test_rank_beyond_the_end_says_how_many_there_were(
    transport: Install, all_time: Payload
) -> None:
    transport(ok(all_time))
    stats = client().stats()

    with pytest.raises(LookupError) as caught:
        stats.ranked(9999)

    assert '9999' in str(caught.value)


def test_a_range_is_fetched_only_once(
    transport: Install, all_time: Payload
) -> None:
    # Only one response is staged; a second request would fail the fake.
    fake = transport(ok(all_time))
    waka = client()

    waka.stats()
    waka.stats()

    assert fake.call_count == 1


def test_different_ranges_are_fetched_separately(
    transport: Install, all_time: Payload
) -> None:
    fake = transport(ok(all_time), ok(all_time))
    waka = client()

    waka.stats('all_time')
    waka.stats('last_7_days')

    assert fake.call_count == 2
    assert fake.calls[1][1].endswith('/stats/last_7_days')


def test_the_key_never_reaches_the_url(
    transport: Install, all_time: Payload
) -> None:
    # Credentials travel in the Authorization header and nowhere else.
    fake = transport(ok(all_time))

    client().stats()

    assert API_KEY not in fake.calls[0][1]


def test_rejected_key_is_reported_without_leaking_it(
    transport: Install,
) -> None:
    # The secret must not survive into the error message.
    transport(ok({'error': 'Unauthorized'}, status=401))

    with pytest.raises(HttpError) as caught:
        client().stats()

    assert API_KEY not in str(caught.value)
    assert caught.value.status == 401


def test_stale_data_is_retried_then_refused(
    transport: Install, all_time: Payload
) -> None:
    # A stale README beats a wrong one.
    stale = {'data': {**all_time['data'], 'is_up_to_date': False}}
    fake = transport(ok(stale), ok(stale), ok(stale))

    with pytest.raises(StaleStats):
        client(retries=3).stats()

    assert fake.call_count == 3


def test_stale_then_settled_returns_the_settled_answer(
    transport: Install, all_time: Payload
) -> None:
    stale = {'data': {**all_time['data'], 'is_up_to_date': False}}
    transport(ok(stale), ok(all_time))

    assert client(retries=3).stats().language('Python').hours > 0


def test_accepted_status_is_retried(
    transport: Install, all_time: Payload
) -> None:
    # WakaTime answers 202 while it recomputes a long range.
    fake = transport(ok(None, status=202), ok(all_time))

    client(retries=3).stats()

    assert fake.call_count == 2
