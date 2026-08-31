#!/usr/bin/env python3
"""Finding placeholders and replacing what sits between them.

Everything is resolved before a single character is spliced. That
ordering is the whole point: if one placeholder cannot be resolved, the
caller gets an exception and the file it was going to write is never
built, so a broken marker can never leave a half-updated document behind.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import blocks, metrics
from .blocks import ChartOptions
from .formatters import is_format
from .formatters import render as render_value
from .metrics import Context, MetricError

MARKER = re.compile(
    r'<!--\s*wr:(?P<spec>[^>]+?)\s*-->'
    r'(?P<body>.*?)'
    r'<!--\s*/wr\s*-->',
    re.DOTALL,
)

MAX_PARTS = 3


@dataclass(frozen=True)
class Placeholder:
    """One marker pair and what it asks for.

    Example:
        >>> found = find('a <!--wr:top_lang-->x<!--/wr--> b')
        >>> found[0].name
        'top_lang'
    """

    spec: str
    name: str
    arg: str | None
    format_name: str | None
    body: str
    body_start: int
    body_end: int


@dataclass(frozen=True)
class Resolution:
    """What one placeholder turned into."""

    placeholder: Placeholder
    rendered: str

    @property
    def changed(self) -> bool:
        """Whether this placeholder's content actually moved."""
        return self.rendered != self.placeholder.body


@dataclass(frozen=True)
class Rewrite:
    """The finished text, and what it took to get there."""

    text: str
    changed: bool
    resolutions: tuple[Resolution, ...]


def _part(parts: list[str], index: int) -> str | None:
    """Read one colon-separated field, treating blank as absent."""
    if len(parts) <= index:
        return None
    value = parts[index].strip()
    return value or None


def _fields(parts: list[str]) -> tuple[str | None, str | None]:
    """Split the tail of a spec into its argument and its format.

    Two fields are ambiguous on their own: `top_lang:2` names a rank
    while `total_hours:1f` names a format. Reading the second field as
    an argument unconditionally left a metric that takes no argument
    with no way to ask for a format at all, and dropped the request in
    silence -- `total_hours:1f` rendered 1920 where the author asked for
    1920.0. A known format name settles it; anything else is an
    argument, and `metric::format` stays available to be explicit.

    Example:
        >>> _fields(['total_hours', '1f'])
        (None, '1f')
        >>> _fields(['top_lang', '2'])
        ('2', None)
    """
    arg, format_name = _part(parts, 1), _part(parts, 2)
    if format_name is None and arg is not None and is_format(arg):
        return None, arg
    return arg, format_name


def find(text: str) -> tuple[Placeholder, ...]:
    """Locate every marker pair, in the order they appear."""
    found = []
    for match in MARKER.finditer(text):
        spec = match.group('spec').strip()
        parts = spec.split(':', MAX_PARTS - 1)
        name = parts[0].strip()
        if not name:
            raise MetricError(f'placeholder has no name: {spec!r}')
        body_start, body_end = match.span('body')
        arg, format_name = _fields(parts)
        found.append(
            Placeholder(
                spec=spec,
                name=name,
                arg=arg,
                format_name=format_name,
                body=match.group('body'),
                body_start=body_start,
                body_end=body_end,
            )
        )
    return tuple(found)


def uses_wakatime(placeholders: tuple[Placeholder, ...]) -> bool:
    """Whether anything here needs a WakaTime credential.

    Example:
        >>> uses_wakatime(find('<!--wr:gh_stars-->1<!--/wr-->'))
        False
    """
    return any(not metrics.needs_github(item.name) for item in placeholders)


def uses_github(placeholders: tuple[Placeholder, ...]) -> bool:
    """Whether anything here needs GitHub metric data."""
    return any(metrics.needs_github(item.name) for item in placeholders)


def _render_one(
    context: Context, placeholder: Placeholder, options: ChartOptions
) -> str:
    """Turn one placeholder into the text that replaces its body."""
    if blocks.is_block(placeholder.name):
        if placeholder.format_name:
            raise MetricError(
                f'{placeholder.name} renders a block and takes no format, '
                f'received {placeholder.format_name!r}'
            )
        return blocks.render(
            context, placeholder.name, placeholder.arg, options
        )
    value = metrics.resolve(context, placeholder.name, placeholder.arg)
    return render_value(value, placeholder.format_name)


def _splice(text: str, resolutions: tuple[Resolution, ...]) -> str:
    """Rebuild the document with every resolved body swapped in."""
    pieces: list[str] = []
    cursor = 0
    for resolution in resolutions:
        placeholder = resolution.placeholder
        pieces.append(text[cursor : placeholder.body_start])
        pieces.append(resolution.rendered)
        cursor = placeholder.body_end
    pieces.append(text[cursor:])
    return ''.join(pieces)


def apply(
    text: str,
    context: Context,
    options: ChartOptions | None = None,
) -> Rewrite:
    """Resolve every placeholder, then produce the updated text.

    Raises whatever a resolver raises, before any splicing happens, so a
    caller that writes only on success cannot write a partial document.

    Example:
        >>> apply('nothing here', Context(None, None, 'all_time')).changed
        False
    """
    options = options or ChartOptions()
    found = find(text)

    # Resolve the lot up front. A failure here leaves `text` untouched
    # because the new document has not been assembled yet.
    resolutions = tuple(
        Resolution(placeholder, _render_one(context, placeholder, options))
        for placeholder in found
    )

    updated = _splice(text, resolutions)
    return Rewrite(
        text=updated,
        changed=updated != text,
        resolutions=resolutions,
    )
