#!/usr/bin/env python3
"""How a resolved value becomes the text that lands in the file.

A registry of pure functions. Adding a format is one function plus one
entry in `FORMATTERS` - never a change to the parser.
"""

from __future__ import annotations

import math
from collections.abc import Callable

Value = float | str
Formatter = Callable[[Value], str]

# Used when a placeholder names no format. Numbers read better rounded;
# strings are already what the author wants.
DEFAULT_NUMERIC = 'int'


class FormatError(ValueError):
    """A format was asked to render a value it cannot render."""


def _as_float(value: Value, format_name: str) -> float:
    """Coerce to a number, naming both culprits when it cannot."""
    if isinstance(value, str):
        raise FormatError(
            f'format {format_name!r} needs a number, received {value!r}'
        )
    return float(value)


def _floor_to(step: int) -> Formatter:
    """Build a formatter that floors a number to a multiple of `step`.

    The point of flooring is churn: a milestone only moves every `step`
    hours, so the file picks up a commit a few times a year rather than
    daily.

    Example:
        >>> _floor_to(50)(892.5)
        '+850'
    """

    def formatter(value: Value) -> str:
        number = _as_float(value, f'floor{step}')
        return f'+{int(math.floor(number / step) * step)}'

    return formatter


def _as_int(value: Value) -> str:
    """Render a number with no decimal part.

    Example:
        >>> _as_int(892.5)
        '892'
    """
    return str(int(_as_float(value, 'int')))


def _one_decimal(value: Value) -> str:
    """Render a number with a single decimal place.

    Example:
        >>> _one_decimal(892.4977)
        '892.5'
    """
    return f'{_as_float(value, "1f"):.1f}'


def _raw(value: Value) -> str:
    """Render whatever came in, untouched.

    Example:
        >>> _raw('Python')
        'Python'
    """
    return str(value)


FORMATTERS: dict[str, Formatter] = {
    'floor10': _floor_to(10),
    'floor50': _floor_to(50),
    'floor100': _floor_to(100),
    'int': _as_int,
    '1f': _one_decimal,
    'raw': _raw,
}


def is_format(name: str) -> bool:
    """Say whether a name refers to a known format.

    The parser asks this to read a two-field placeholder: in
    `total_hours:1f` the second field is a format, while in `top_lang:2`
    it is an argument. Answering here rather than in the parser is what
    keeps adding a format to one function plus one entry.

    Example:
        >>> is_format('1f'), is_format('Python')
        (True, False)
    """
    return name in FORMATTERS


def render(value: Value, format_name: str | None) -> str:
    """Apply a named format, choosing a sensible one when none was given.

    Example:
        >>> render(892.5, 'floor50')
        '+850'
        >>> render('Python', None)
        'Python'
    """
    if format_name is None:
        format_name = 'raw' if isinstance(value, str) else DEFAULT_NUMERIC

    formatter = FORMATTERS.get(format_name)
    if formatter is None:
        raise FormatError(
            f'unknown format: {format_name!r}, '
            f'expected one of {sorted(FORMATTERS)}'
        )
    return formatter(value)
