#!/usr/bin/env python3
"""Tests for the activity chart, pinned to a real rendered profile."""

from __future__ import annotations

import pytest

from wakatime_readme.blocks import ChartOptions, _body, make_graph
from wakatime_readme.wakatime import Language, Stats

PALETTE = '⣀⣄⣤⣦⣶⣷⣿'
FULL = '⣿'
EMPTY = '⣀'

# The five rows below were read off a profile that the original tool had
# rendered, so they are the yardstick for "nothing reflows when you
# switch". Each one is percentage in, exact bar out.
REAL_BARS = [
    (45.03, FULL * 11 + '⣤' + EMPTY * 13),
    (20.30, FULL * 5 + EMPTY * 20),
    (17.73, FULL * 4 + '⣦' + EMPTY * 20),
    (6.01, FULL * 1 + '⣦' + EMPTY * 23),
    (2.09, '⣦' + EMPTY * 24),
]


@pytest.mark.parametrize(('percent', 'expected'), REAL_BARS)
def test_bar_matches_the_rendered_profile(
    percent: float, expected: str
) -> None:
    assert make_graph(PALETTE, percent, 25) == expected


@pytest.mark.parametrize(('percent', 'expected'), REAL_BARS)
def test_bar_is_always_the_requested_width(
    percent: float, expected: str
) -> None:
    assert len(make_graph(PALETTE, percent, 25)) == 25


def test_zero_percent_draws_an_empty_bar() -> None:
    assert make_graph(PALETTE, 0.0, 25) == EMPTY * 25


def test_full_percent_draws_a_solid_bar() -> None:
    assert make_graph(PALETTE, 100.0, 25) == FULL * 25


def test_a_palette_of_one_character_is_refused() -> None:
    # Without at least two characters there is no empty-to-full range to
    # interpolate across, and the arithmetic would divide by zero.
    with pytest.raises(ValueError, match='at least two'):
        make_graph('x', 50.0, 25)


def sample() -> Stats:
    """Build the range the rendered profile was showing."""
    languages = (
        Language('Markdown', 16200.0, 45.03, '4 hrs 30 mins'),
        Language('Python', 7260.0, 20.30, '2 hrs 1 min'),
        Language('HTML', 6360.0, 17.73, '1 hr 46 mins'),
        Language('Bash', 2160.0, 6.01, '36 mins'),
        Language('JavaScript', 720.0, 2.09, '12 mins'),
        # Never displayed: it is filtered out below. It exists to prove
        # the name column is padded against everything the API returned,
        # not against the handful that survive the filter.
        Language('CoffeeScript', 60.0, 0.16, '1 min'),
    )
    return Stats(36000.0, 5142.0, None, 'Last 7 Days', languages)


def test_row_matches_the_rendered_profile_byte_for_byte() -> None:
    options = ChartOptions(
        lang_count=5, ignored_languages=frozenset({'CoffeeScript'})
    )

    first = _body(sample(), options).splitlines()[2]

    assert first == (
        'Markdown       4 hrs 30 mins         '
        + FULL * 11
        + '⣤'
        + EMPTY * 13
        + '   45.03 %'
    )


def test_name_column_is_padded_against_the_whole_response() -> None:
    # 'CoffeeScript' is 12 characters and is filtered out, yet it is what
    # sets the column width. Padding against only the visible rows would
    # shift every line four characters left.
    options = ChartOptions(
        lang_count=5, ignored_languages=frozenset({'CoffeeScript'})
    )

    rows = _body(sample(), options).splitlines()[2:]

    assert all(
        row.startswith(row.split()[0].ljust(12) + '   ') for row in rows
    )


def test_total_header_leads_the_chart() -> None:
    lines = _body(sample(), ChartOptions()).splitlines()

    assert lines[0] == 'Total Time: 10 hrs'
    assert lines[1] == ''


def test_total_header_can_be_turned_off() -> None:
    lines = _body(sample(), ChartOptions(show_total=False)).splitlines()

    assert lines[0].startswith('Markdown')


def test_language_count_limits_the_rows() -> None:
    options = ChartOptions(lang_count=2, show_total=False)

    assert len(_body(sample(), options).splitlines()) == 2


def test_ignored_languages_are_skipped() -> None:
    options = ChartOptions(
        ignored_languages=frozenset({'Markdown'}), show_total=False
    )

    assert not _body(sample(), options).startswith('Markdown')


def test_stop_at_other_truncates_the_list() -> None:
    languages = (
        Language('Python', 100.0, 50.0, '1 min'),
        Language('Other', 100.0, 50.0, '1 min'),
        Language('Rust', 10.0, 5.0, '1 min'),
    )
    stats = Stats(210.0, 30.0, None, 'Last 7 Days', languages)

    rows = _body(stats, ChartOptions(show_total=False)).splitlines()

    assert len(rows) == 3
    rows = _body(
        stats, ChartOptions(show_total=False, stop_at_other=True)
    ).splitlines()
    assert len(rows) == 1


def test_an_empty_range_says_so_instead_of_rendering_nothing() -> None:
    empty = Stats(0.0, 0.0, None, 'Last 7 Days', ())

    assert 'No activity' in _body(empty, ChartOptions())
