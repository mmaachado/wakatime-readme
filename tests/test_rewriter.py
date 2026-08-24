#!/usr/bin/env python3
"""Tests for placeholder parsing and the all-or-nothing rewrite."""

from __future__ import annotations

import pytest

from tests.stubs import ExplodingWakaTime, StubGitHub, StubWakaTime
from wakatime_readme.metrics import Context, MetricError
from wakatime_readme.rewriter import apply, find, uses_github, uses_wakatime

SENTENCE = (
    "I'm a prolific Python developer with "
    '<!--wr:lang_hours:Python:floor50-->**_+800_**<!--/wr--> hours.'
)


def context(
    wakatime: object = None,
    github: object = None,
    range_name: str = 'all_time',
) -> Context:
    """Build a context, defaulting each source to a working stub."""
    return Context(
        wakatime=StubWakaTime() if wakatime is None else wakatime,  # type: ignore[arg-type]
        github=StubGitHub() if github is None else github,  # type: ignore[arg-type]
        range_name=range_name,
    )


def test_parses_name_argument_and_format() -> None:
    found = find(SENTENCE)[0]

    assert found.name == 'lang_hours'
    assert found.arg == 'Python'
    assert found.format_name == 'floor50'


def test_parses_a_bare_name() -> None:
    found = find('<!--wr:total_hours-->0<!--/wr-->')[0]

    assert (found.name, found.arg, found.format_name) == (
        'total_hours',
        None,
        None,
    )


def test_an_argument_may_contain_a_slash() -> None:
    found = find('<!--wr:gh_repo_stars:octocat/hello-world-->0<!--/wr-->')[0]

    assert found.arg == 'octocat/hello-world'


def test_tolerates_whitespace_inside_the_markers() -> None:
    found = find('<!--  wr:top_lang  -->x<!--  /wr  -->')

    assert len(found) == 1
    assert found[0].name == 'top_lang'


def test_text_without_markers_yields_nothing() -> None:
    assert find('just prose') == ()


def test_resolves_the_documented_sentence() -> None:
    result = apply(SENTENCE, context())

    assert '**_+850_**' not in result.text
    assert '+850' in result.text
    assert result.changed


def test_leaves_the_surrounding_prose_alone() -> None:
    result = apply(SENTENCE, context())

    assert result.text.startswith("I'm a prolific Python developer with ")
    assert result.text.endswith(' hours.')


def test_reports_no_change_when_the_value_already_matches() -> None:
    once = apply(SENTENCE, context())

    twice = apply(once.text, context())

    assert twice.text == once.text
    assert not twice.changed


def test_resolves_several_placeholders_in_one_pass() -> None:
    text = (
        '<!--wr:top_lang-->?<!--/wr--> and <!--wr:gh_stars-->?<!--/wr--> stars'
    )

    result = apply(text, context())

    # The markers survive; only what sits between them is replaced, which
    # is what lets the next run find them again.
    assert [item.rendered for item in result.resolutions] == ['Python', '22']
    assert result.text.startswith('<!--wr:top_lang-->Python<!--/wr--> and ')


def test_github_metrics_read_the_profile() -> None:
    text = (
        '<!--wr:gh_followers-->0<!--/wr-->/'
        '<!--wr:gh_repos-->0<!--/wr-->/'
        '<!--wr:gh_top_repo-->x<!--/wr-->'
    )

    result = apply(text, context())

    assert [item.rendered for item in result.resolutions] == [
        '42',
        '8',
        'hello-world',
    ]


def test_a_file_of_github_metrics_never_touches_wakatime() -> None:
    # Nobody should have to supply a credential for data they are not
    # asking for.
    text = '<!--wr:gh_stars-->0<!--/wr-->'

    result = apply(text, context(wakatime=ExplodingWakaTime()))

    assert result.resolutions[0].rendered == '22'


def test_the_range_comes_from_the_context() -> None:
    waka = StubWakaTime()

    apply(
        '<!--wr:total_hours-->0<!--/wr-->',
        context(waka, range_name='last_7_days'),
    )

    assert waka.ranges == ['last_7_days']


def test_provider_detection_reads_the_placeholders() -> None:
    both = find(
        '<!--wr:gh_stars-->0<!--/wr--><!--wr:total_hours-->0<!--/wr-->'
    )

    assert uses_github(both)
    assert uses_wakatime(both)


def test_a_failure_partway_through_writes_nothing() -> None:
    # The middle placeholder cannot resolve. The two around it are
    # perfectly good, and neither may reach the output.
    text = (
        '<!--wr:top_lang-->a<!--/wr-->'
        '<!--wr:lang_hours:Brainfuck-->b<!--/wr-->'
        '<!--wr:gh_stars-->c<!--/wr-->'
    )

    with pytest.raises(LookupError):
        apply(text, context())

    # Nothing was produced at all, so there is no partial document for a
    # caller to accidentally write.
    assert find(text)[0].body == 'a'
    assert find(text)[2].body == 'c'


def test_unknown_metric_names_itself() -> None:
    with pytest.raises(MetricError, match='invented'):
        apply('<!--wr:invented-->x<!--/wr-->', context())


def test_a_block_refuses_a_format() -> None:
    # Formats apply to single values; a chart has no scalar to format.
    with pytest.raises(MetricError, match='takes no format'):
        apply('<!--wr:activity_chart:last_7_days:int-->x<!--/wr-->', context())


def test_a_missing_argument_is_explained() -> None:
    with pytest.raises(MetricError, match='needs an argument'):
        apply('<!--wr:lang_hours-->x<!--/wr-->', context())


def test_a_nameless_placeholder_is_refused() -> None:
    with pytest.raises(MetricError, match='no name'):
        find('<!--wr::Python-->x<!--/wr-->')


def test_the_chart_replaces_a_whole_block() -> None:
    text = '<!--wr:activity_chart:last_7_days-->old<!--/wr-->'

    result = apply(text, context())

    assert '```markdown' in result.text
    assert 'Total Time:' in result.text
    assert 'Python' in result.text
