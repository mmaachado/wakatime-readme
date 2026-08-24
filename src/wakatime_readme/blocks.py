#!/usr/bin/env python3
"""Multi-line placeholders: the language activity chart.

The chart reproduces the layout people already have in their profiles,
so swapping tools does not reflow a single line. Two details of that
layout are easy to get wrong and are pinned by tests:

- The partial block is chosen with a rounding bias, not a plain floor.
- The name column is padded to the longest language in the *whole*
  response, not to the longest of the few that end up displayed.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field

from .metrics import Context, MetricError
from .wakatime import Language, Stats

DEFAULT_BLOCKS = '⣀⣄⣤⣦⣶⣷⣿'
GRAPH_LENGTH = 25
PREFIX_LENGTH = 22
OTHER = 'Other'


@dataclass(frozen=True)
class ChartOptions:
    """How the chart should look.

    Named after the settings people already have in their workflows, so
    migrating is a copy rather than a translation.

    Example:
        >>> ChartOptions().lang_count
        5
    """

    blocks: str = DEFAULT_BLOCKS
    code_lang: str = 'markdown'
    lang_count: int = 5
    ignored_languages: frozenset[str] = field(default_factory=frozenset)
    stop_at_other: bool = False
    show_time: bool = True
    show_total: bool = True
    graph_length: int = GRAPH_LENGTH
    prefix_length: int = PREFIX_LENGTH


def make_graph(blocks: str, percent: float, length: int) -> str:
    """Draw one proportional bar.

    The `+ 0.5 / markers` and `+ 0.5` are deliberate rounding biases: a
    language at 45.03% of a 25-wide bar gets eleven full blocks and a
    three-quarter one, not eleven and a quarter.

    Example:
        >>> make_graph('⣀⣄⣤⣦⣶⣷⣿', 45.03, 25).count('⣿')
        11
    """
    markers = len(blocks) - 1
    if markers < 1:
        raise MetricError(
            f'the block palette needs at least two characters, '
            f'received {blocks!r}'
        )
    proportion = percent / 100 * length
    bar = blocks[-1] * int(proportion + 0.5 / markers)
    remainder = int((proportion - len(bar)) * markers + 0.5)
    if remainder > 0:
        bar += blocks[remainder]
    return bar + blocks[0] * (length - len(bar))


def _displayed(
    languages: Sequence[Language], options: ChartOptions
) -> Iterator[Language]:
    """Walk the languages that survive filtering and truncation."""
    shown = 0
    for language in languages:
        if language.name in options.ignored_languages:
            continue
        if options.stop_at_other and language.name == OTHER:
            return
        yield language
        shown += 1
        if shown >= options.lang_count:
            return


def _line(language: Language, pad: int, options: ChartOptions) -> str:
    """Format one language row."""
    bar = make_graph(options.blocks, language.percent, options.graph_length)
    time = (
        f'{language.text: <{options.prefix_length}}'
        if options.show_time
        else ''
    )
    percent = f'{language.percent:.2f}'.zfill(5)
    return f'{language.name.ljust(pad)}   {time}{bar}   {percent} %'


def _body(stats: Stats, options: ChartOptions) -> str:
    """Build the chart text, header included."""
    if not stats.languages:
        return 'No activity tracked for this range.'

    # Padded against every language the range returned, including the
    # ones filtered out below, which is what keeps the column where
    # people are used to seeing it.
    pad = max(len(language.name) for language in stats.languages)

    lines = [
        _line(language, pad, options)
        for language in _displayed(stats.languages, options)
    ]
    if options.show_total:
        total = f'Total Time: {_human(stats.total_seconds)}'
        return '\n'.join([total, '', *lines])
    return '\n'.join(lines)


def _human(seconds: float) -> str:
    """Phrase a duration the way the activity summaries do.

    Example:
        >>> _human(36000.0)
        '10 hrs'
        >>> _human(3660.0)
        '1 hr 1 min'
    """
    hours, minutes = divmod(int(seconds) // 60, 60)
    parts = []
    if hours:
        parts.append(f'{hours} hr' + ('s' if hours != 1 else ''))
    if minutes:
        parts.append(f'{minutes} min' + ('s' if minutes != 1 else ''))
    return ' '.join(parts) if parts else '0 mins'


def _stats_for(context: Context, arg: str | None) -> Stats:
    """Pull the range the placeholder named, or the configured default."""
    if context.wakatime is None:
        raise MetricError(
            'the activity chart needs WakaTime data; '
            'set WAKATIME_API_KEY to use it'
        )
    return context.wakatime.stats(arg or context.range_name)


def _activity_chart(
    context: Context, arg: str | None, options: ChartOptions
) -> str:
    """Render the fenced chart that goes between the markers."""
    body = _body(_stats_for(context, arg), options)
    if options.code_lang:
        return f'\n```{options.code_lang}\n{body}\n```\n'
    return f'\n{body}\n'


BlockRenderer = Callable[[Context, str | None, ChartOptions], str]

BLOCKS: dict[str, BlockRenderer] = {
    'activity_chart': _activity_chart,
}


def is_block(name: str) -> bool:
    """Say whether a placeholder name renders multiple lines.

    Example:
        >>> is_block('activity_chart'), is_block('lang_hours')
        (True, False)
    """
    return name in BLOCKS


def render(
    context: Context, name: str, arg: str | None, options: ChartOptions
) -> str:
    """Look up one block renderer and run it."""
    renderer = BLOCKS.get(name)
    if renderer is None:
        raise MetricError(f'unknown block: {name!r}')
    return renderer(context, arg, options)
