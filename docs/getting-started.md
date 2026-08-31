# Getting started

## 1. Put placeholders in your file

A placeholder is a pair of HTML comments. Whatever sits between them is replaced
on every run, the comments stay put.

```markdown
I have <!--wr:lang_hours:Python:floor50-->+800<!--/wr--> hours of Python.
```

What you leave in there now is the **fallback**: it is what readers see until the
first successful run, and what survives a run that refuses to write.

See [Placeholders](placeholders.md) for the full grammar.

## 2. Get your WakaTime API key

From [wakatime.com/api-key](https://wakatime.com/api-key). Store it as a
repository secret named `WAKATIME_API_KEY`.

It is only ever sent as an `Authorization` header *— never in a URL, never in a
log line, never in an exception message*.

!!! tip "Only if you use WakaTime placeholders:"

    A file containing nothing but `gh_*` placeholders never calls WakaTime and
    needs no key at all. The reverse holds too.

## 3. Add the workflow

/// tab | As a GitHub Action

Copy this to `.github/workflows/readme.yml` in the repository that holds the
file. Nothing else is needed: no `actions/checkout`, no commit step, no bot
account.

```yaml
name: 'Refresh README metrics'

on:
  schedule:
    # 03:00 UTC daily. Pick an odd minute; the top of the hour is the
    # busiest slot on GitHub's shared cron queue and gets delayed most.
    - cron: '17 3 * * *'
  workflow_dispatch:

# The action commits through the Contents API, so it needs write here.
permissions:
  contents: write

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: mmaachado/wakatime-readme@v1
        with:
          wakatime_api_key: ${{ secrets.WAKATIME_API_KEY }}
```

A copy of this file lives in
[`examples/workflow.yml`](https://github.com/mmaachado/wakatime-readme/blob/master/examples/workflow.yml),
with every optional input listed at its default.

///

/// tab | As a CLI

```console
$ export WAKATIME_API_KEY=waka_...
$ uvx wakatime-readme --readme README.md --dry-run
```

`--dry-run` prints what each placeholder would resolve to and writes nothing *—
the fastest way to check a placeholder before committing it*.

Without `--repo`, the CLI reads and writes your local file directly instead of
going through the GitHub API.

///

## 4. Check the numbers

Run it once by hand with `workflow_dispatch`, then compare the result against
your WakaTime profile.

If the totals come out roughly a third below what your profile shows, that is a
known and documented cause with a one-line fix *— see
[Matching WakaTime](matching-wakatime.md)*.

## Writing to a different repository

To edit a profile README that lives in another repository, pass a personal
access token with `contents: write` as `github_token` and set `repository`:

```yaml
- uses: mmaachado/wakatime-readme@v1
  with:
    wakatime_api_key: ${{ secrets.WAKATIME_API_KEY }}
    github_token: ${{ secrets.PROFILE_PAT }}
    repository: 'yourname/yourname'
```

A PAT produces an ordinary commit. The **Verified** signature only comes with
the workflow's own `GITHUB_TOKEN`.
