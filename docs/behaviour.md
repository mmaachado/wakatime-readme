# Behaviour

The guarantees that make this safe to run unattended on a daily cron.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success, or nothing to do. Also an unreachable API **without** `--strict`. |
| `1` | Configuration error *— missing key, unreadable file, unknown metric or format*. |
| `2` | Stale WakaTime data, always. An unreachable API **only** with `--strict`. |

The line between `0` and `2` is deliberate. **Not reaching** an API is a blip a
nightly cron should ride out, so it stays green unless you ask for `--strict`.
WakaTime **answering that it has no final number** is different: nothing was
written, and a green run there hides a README that has quietly stopped being
true.

!!! note "This changed in 1.1.0:"

    Exhausted retries used to exit `0`. That silence is what let a wrong total
    publish for days with every scheduled run green.

## All or nothing

Every placeholder is resolved in memory before a single character is written,
and everything lands in one commit. A broken placeholder leaves the file
untouched rather than half-filled *— you never get a README where the first three
numbers updated and the fourth is a stack trace*.

## It never writes a number it does not believe

WakaTime computes long ranges lazily. While it works it answers `202`, or `200`
with real-looking but partial totals *— `is_up_to_date` goes true while
`percent_calculated` is still climbing, so both signals have to agree before an
answer is worth writing down*.

If they do not agree, the client retries within a **30-second budget** across six
attempts, then gives up without touching the file. A stale README beats a wrong
one.

## It only fetches what you use

A file with no `gh_*` placeholder never calls GitHub for metrics. A file with no
WakaTime placeholder never calls WakaTime. You are never asked for a credential
you do not need.

## No write, no diff

If the rendered output matches what is already in the file, nothing is written,
so there is no empty commit. Combined with `floor50` and friends, a profile
README can go weeks without a commit and then pick one up when a milestone
actually moves.

## One commit, with the right parent

Reading remembers the blob `sha`, and the write is rejected without it. If the
file moved under the run *— you edited it by hand while the cron was going —* the
Contents API answers `409`, and the tool re-reads and re-resolves exactly once so
the retry lands on top of your change rather than overwriting it. After that it
gives up rather than fight you.

## Secrets

Both credentials travel in the `Authorization` header and nowhere else: never in
a URL query string, never in a log line, never in an exception message.
Redaction happens in the transport, so there is one place to audit rather than
one per caller.

## Line endings

A file that arrives with CRLF goes back with CRLF. A run that silently reflowed
every line would turn a one-word change into an enormous diff.

## Logging

Diagnostics go to stderr as plain text; stdout carries only the `--dry-run`
table, so you can pipe one without the other. Inside GitHub Actions, warnings use
the `::warning::` workflow command and show up as annotations on the run.
