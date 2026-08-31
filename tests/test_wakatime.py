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
    assert '/stats/last_7_days?' in fake.calls[1][1]


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


def test_a_partially_computed_range_is_never_published(
    transport: Install, all_time: Payload
) -> None:
    """A `200` is not a promise that the numbers are final.

    WakaTime answers a request for a range it is still computing with
    real-looking but partial totals: `is_up_to_date` is already true
    while `percent_calculated` climbs. Trusting the first flag alone
    publishes a fraction of a total as though it were the whole thing,
    and the number looks plausible enough that nobody notices.
    """
    partial = {
        'data': {
            **all_time['data'],
            'is_up_to_date': True,
            'percent_calculated': 67,
        }
    }
    fake = transport(ok(partial), ok(partial), ok(partial))

    with pytest.raises(StaleStats) as caught:
        client(retries=3).stats()

    assert fake.call_count == 3
    # The share it stopped at belongs in the message: without it, the
    # only symptom of this bug was a number that looked plausible.
    assert '67%' in str(caught.value)


def test_a_range_that_finishes_computing_is_used(
    transport: Install, all_time: Payload
) -> None:
    partial = {
        'data': {
            **all_time['data'],
            'is_up_to_date': True,
            'percent_calculated': 67,
        }
    }
    transport(ok(partial), ok(all_time))

    hours = client(retries=3).stats().language('Python').hours

    # The complete answer, not the 67% one that arrived first.
    assert hours == pytest.approx(861.1111, abs=1e-3)


def test_an_empty_body_is_not_mistaken_for_a_settled_answer(
    transport: Install,
) -> None:
    # Defaulting the freshness flags to "fine" made `{}` look final and
    # resolve every metric to zero.
    fake = transport(ok({'data': {}}), ok({'data': {}}), ok({'data': {}}))

    with pytest.raises(StaleStats):
        client(retries=3).stats()

    assert fake.call_count == 3


def test_accepted_status_is_retried(
    transport: Install, all_time: Payload
) -> None:
    # WakaTime answers 202 while it recomputes a long range.
    fake = transport(ok(None, status=202), ok(all_time))

    client(retries=3).stats()

    assert fake.call_count == 2


def test_the_keystroke_timeout_is_always_sent(
    transport: Install, all_time: Payload
) -> None:
    """Regression: the parameter has to be on the wire, not inherited.

    WakaTime applies the account's own keystroke timeout when a request
    omits `timeout`, but renders its public profile pages with 15. This
    account defaults to 5, and the gap published 622 hours of Python
    where the profile advertised 897 -- a third of the total missing,
    from a value that looked perfectly plausible in the README.
    """
    fake = transport(ok(all_time))

    client().stats()

    assert 'timeout=15' in fake.calls[0][1]


def test_the_keystroke_timeout_is_configurable(
    transport: Install, all_time: Payload
) -> None:
    # Anyone whose account is set to something other than 15 needs to be
    # able to say so, or their README disagrees with their own dashboard.
    fake = transport(ok(all_time))

    WakaTimeClient(API_KEY, keystroke_timeout=5, sleep=lambda _s: None).stats()

    assert 'timeout=5' in fake.calls[0][1]


def test_waiting_stays_inside_the_budget(transport: Install) -> None:
    """The retry budget is a promise about wall time, not an attempt count.

    The old backoff slept `2**attempt` while `attempt < retries - 1`,
    which with three attempts came to one second plus two: no use at all
    against a range WakaTime computes on first request.
    """
    slept: list[float] = []
    stale = ok({'data': {'is_up_to_date': False}})
    fake = transport(*[stale] * 6)

    waka = WakaTimeClient(API_KEY, retries=6, sleep=slept.append, budget=30.0)
    with pytest.raises(StaleStats) as caught:
        waka.stats()

    assert fake.call_count == 6
    # Five gaps between six attempts, and never a sleep after the last.
    assert len(slept) == 5
    assert sum(slept) == pytest.approx(30.0)
    # The message has to say how long it actually waited, so a failing
    # run is diagnosable from the log alone.
    assert '30s' in str(caught.value)
    assert 'keystroke timeout 15' in str(caught.value)
