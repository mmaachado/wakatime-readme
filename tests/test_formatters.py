#!/usr/bin/env python3
"""Tests for the format registry."""

from __future__ import annotations

import pytest

from wakatime_readme.formatters import FORMATTERS, FormatError, render


@pytest.mark.parametrize(
    ('format_name', 'expected'),
    [
        ('floor10', '+890'),
        ('floor50', '+850'),
        ('floor100', '+800'),
        ('int', '892'),
        ('1f', '892.5'),
    ],
)
def test_renders_the_documented_example(
    format_name: str, expected: str
) -> None:
    # 892.4977 hours is the real all-time Python figure the project was
    # built around; the README documents exactly these outputs.
    assert render(892.4977, format_name) == expected


def test_floor_does_not_round_up_across_the_milestone() -> None:
    # 899 must still read +850, never +900. Flooring is the whole point.
    assert render(899.99, 'floor50') == '+850'


def test_floor_lands_exactly_on_a_multiple() -> None:
    assert render(850.0, 'floor50') == '+850'


def test_numbers_default_to_whole_hours() -> None:
    assert render(892.4977, None) == '892'


def test_strings_default_to_passing_through() -> None:
    assert render('Python', None) == 'Python'


def test_raw_keeps_the_full_precision() -> None:
    assert render(892.4977, 'raw') == '892.4977'


def test_unknown_format_names_itself_and_the_alternatives() -> None:
    with pytest.raises(FormatError) as caught:
        render(1.0, 'floor7')

    message = str(caught.value)
    assert "'floor7'" in message
    assert 'floor50' in message


def test_numeric_format_on_a_string_names_both_culprits() -> None:
    with pytest.raises(FormatError) as caught:
        render('Python', 'floor50')

    message = str(caught.value)
    assert "'floor50'" in message
    assert "'Python'" in message


def test_every_registered_format_is_reachable_through_render() -> None:
    # Guards against a formatter being added to the dict under a name the
    # dispatcher cannot actually resolve.
    for format_name in FORMATTERS:
        assert render(100.0, format_name)
