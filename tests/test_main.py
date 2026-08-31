#!/usr/bin/env python3
"""End-to-end tests over the command line, against a file on disk."""

from __future__ import annotations

import io
from collections.abc import Callable
from pathlib import Path

from tests.helpers import FakeTransport, Payload, contents, ok
from wakatime_readme.main import main

Install = Callable[..., FakeTransport]

KEY_ONLY = {'WAKATIME_API_KEY': 'waka_test-key'}

SENTENCE = (
    "I'm a prolific Python developer with "
    '<!--wr:lang_hours:Python:floor50-->**_+800_**<!--/wr--> hours.\n'
)


class Run:
    """One invocation and everything it printed."""

    def __init__(self, code: int, out: str, err: str) -> None:
        self.code = code
        self.out = out
        self.err = err


def run(argv: list[str], env: dict[str, str] | None = None) -> Run:
    """Call the entry point with captured streams."""
    out, err = io.StringIO(), io.StringIO()
    code = main(argv, env or {}, out, err)
    return Run(code, out.getvalue(), err.getvalue())


def readme(tmp_path: Path, text: str) -> Path:
    """Write a document to disk without translating line endings."""
    path = tmp_path / 'README.md'
    path.write_bytes(text.encode('utf-8'))
    return path


def test_fills_the_sentence_from_live_numbers(
    tmp_path: Path, transport: Install, all_time: Payload
) -> None:
    path = readme(tmp_path, SENTENCE)
    transport(ok(all_time))

    result = run(['--readme', str(path)], KEY_ONLY)

    assert result.code == 0
    assert '+850' in path.read_text(encoding='utf-8')


def test_dry_run_reports_without_touching_the_file(
    tmp_path: Path, transport: Install, all_time: Payload
) -> None:
    path = readme(tmp_path, SENTENCE)
    before = path.read_bytes()
    transport(ok(all_time))

    result = run(['--readme', str(path), '--dry-run'], KEY_ONLY)

    assert result.code == 0
    assert '+850' in result.out
    assert path.read_bytes() == before


def test_a_bad_placeholder_leaves_the_file_byte_identical(
    tmp_path: Path, transport: Install, all_time: Payload
) -> None:
    # The first and third placeholders resolve perfectly well. Neither of
    # them may reach the disk, because the middle one cannot.
    original = (
        '<!--wr:top_lang-->a<!--/wr-->\n'
        '<!--wr:lang_hours:Brainfuck-->b<!--/wr-->\n'
        '<!--wr:total_hours-->c<!--/wr-->\n'
    )
    path = readme(tmp_path, original)
    transport(ok(all_time))

    result = run(['--readme', str(path)], KEY_ONLY)

    assert result.code == 1
    assert path.read_bytes() == original.encode('utf-8')
    assert 'Brainfuck' in result.err


def test_a_second_run_changes_nothing(
    tmp_path: Path, transport: Install, all_time: Payload
) -> None:
    path = readme(tmp_path, SENTENCE)
    transport(ok(all_time), ok(all_time))

    run(['--readme', str(path)], KEY_ONLY)
    after_first = path.read_bytes()
    result = run(['--readme', str(path)], KEY_ONLY)

    assert result.code == 0
    assert path.read_bytes() == after_first
    assert 'up to date' in result.err


def test_line_endings_survive_a_rewrite(
    tmp_path: Path, transport: Install, all_time: Payload
) -> None:
    path = readme(tmp_path, SENTENCE.replace('\n', '\r\n'))
    transport(ok(all_time))

    run(['--readme', str(path)], KEY_ONLY)

    assert b'\r\n' in path.read_bytes()
    assert b'\n\n' not in path.read_bytes()


def test_waka_placeholders_without_a_key_stop_before_the_network(
    tmp_path: Path, transport: Install
) -> None:
    # Nothing is staged on the transport, so any request would fail the
    # test. The point is that it never gets that far.
    path = readme(tmp_path, SENTENCE)
    transport()

    result = run(['--readme', str(path)], {})

    assert result.code == 1
    assert 'WAKATIME_API_KEY' in result.err


def test_a_file_of_github_metrics_needs_no_wakatime_key(
    tmp_path: Path, transport: Install, gh_user: Payload
) -> None:
    path = readme(tmp_path, 'followers: <!--wr:gh_followers-->0<!--/wr-->\n')
    transport(ok(gh_user))

    result = run(['--readme', str(path), '--username', 'octocat'], {})

    assert result.code == 0
    # The markers stay put; only the value between them is replaced.
    assert '<!--wr:gh_followers-->42<!--/wr-->' in path.read_text(
        encoding='utf-8'
    )


def test_stale_data_fails_the_run_even_without_strict(
    tmp_path: Path, transport: Install, all_time: Payload, no_sleep: None
) -> None:
    """Exhausted retries are a failure whether or not `strict` was asked.

    This used to exit 0. WakaTime did answer and said it has no final
    number, so nothing was written and the file kept publishing whatever
    it already held. Reporting success there is exactly how a README
    went on advertising a wrong total with every run green.
    """
    stale = {'data': {**all_time['data'], 'is_up_to_date': False}}
    path = readme(tmp_path, SENTENCE)
    before = path.read_bytes()
    transport(ok(stale), ok(stale), ok(stale))

    result = run(['--readme', str(path), '--retries', '3'], KEY_ONLY)

    assert result.code == 2
    # Invariant 5 still holds: refusing to write is the point, and the
    # exit code is what makes the refusal visible.
    assert path.read_bytes() == before
    assert 'warning' in result.err


def test_an_unreachable_api_stays_green_unless_strict(
    tmp_path: Path, transport: Install
) -> None:
    """A brief outage is not an incident; asking for strictness makes it one.

    The distinction that survives: the API answering "not final yet" is a
    failure, while not reaching the API at all is the transient case a
    nightly cron should ride out.
    """
    path = readme(tmp_path, SENTENCE)
    before = path.read_bytes()
    transport(ok(None, 401))

    result = run(['--readme', str(path)], KEY_ONLY)

    assert result.code == 0
    assert path.read_bytes() == before

    transport(ok(None, 401))
    strict = run(['--readme', str(path), '--strict'], KEY_ONLY)

    assert strict.code == 2


def test_a_workflow_gets_an_annotation_instead_of_plain_text(
    tmp_path: Path, transport: Install
) -> None:
    path = readme(tmp_path, 'no markers here\n')
    transport()

    result = run(
        ['--readme', str(path)], {'GITHUB_ACTIONS': 'true', **KEY_ONLY}
    )

    assert result.code == 0
    assert result.err.startswith('::warning::')


def test_a_missing_file_is_a_configuration_failure(tmp_path: Path) -> None:
    result = run(['--readme', str(tmp_path / 'absent.md')], KEY_ONLY)

    assert result.code == 1
    assert 'absent.md' in result.err


def test_a_half_written_commit_identity_is_refused(
    tmp_path: Path,
) -> None:
    path = readme(tmp_path, SENTENCE)

    result = run(['--readme', str(path), '--committer-name', 'bot'], KEY_ONLY)

    assert result.code == 1
    assert 'name and an email' in result.err


def test_action_inputs_are_read_from_the_environment(
    tmp_path: Path, transport: Install, all_time: Payload
) -> None:
    # A container action receives its inputs as INPUT_* variables rather
    # than as arguments.
    path = readme(tmp_path, SENTENCE)
    transport(ok(all_time))

    result = run(
        [],
        {
            'INPUT_README_PATH': str(path),
            'INPUT_WAKATIME_API_KEY': 'waka_test-key',
        },
    )

    assert result.code == 0
    assert '+850' in path.read_text(encoding='utf-8')


def test_a_rejected_commit_costs_one_reread_and_one_commit(
    transport: Install, gh_user: Payload
) -> None:
    """Invariant 9: never PUT without the sha from this run's GET.

    A 409 means the blob moved between the read and the write. The run
    re-reads once, resolves again on top of whatever arrived, commits
    once more, and stops there.
    """
    document = 'followers: <!--wr:gh_followers-->0<!--/wr-->\n'
    fake = transport(
        ok(contents(document, sha='before')),
        ok(gh_user),
        ok({'message': 'is at another sha'}, status=409),
        ok(contents(document, sha='after')),
        ok(gh_user),
        ok({'commit': {'sha': 'committed'}}),
    )

    result = run(
        ['--readme', 'README.md', '--repo', 'octocat/octocat'],
        {'GITHUB_TOKEN': 'ghs_fake-token'},
    )

    assert result.code == 0
    commits = [url for method, url in fake.calls if method == 'PUT']
    rereads = [
        url
        for method, url in fake.calls
        if method == 'GET' and '/contents/' in url
    ]
    assert len(rereads) == 2
    assert len(commits) == 2

    # The retry commits against the sha the re-read handed back, never
    # the stale one GitHub just rejected.
    assert fake.sent(5)['sha'] == 'after'
