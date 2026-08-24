# Contributing

Thanks for taking the time. This is a small project, so the process is light.

## Setup

You need [uv](https://docs.astral.sh/uv/). Everything else is installed for you.

```console
$ git clone https://github.com/mmaachado/wakatime-readme.git
$ cd wakatime-readme
$ uv sync
$ uv run pre-commit install
```

## Everyday commands

The task runner is [taskipy](https://github.com/taskipy/taskipy).

| Command                 | Does                                   |
| ----------------------- | -------------------------------------- |
| `uv run task lint`      | `ruff check` plus a formatting check   |
| `uv run task format`    | applies both fixes                     |
| `uv run task typecheck` | `mypy src` in strict mode              |
| `uv run task test`      | runs lint, then `pytest` with coverage |

`task test` runs `task lint` first, so a lint error stops you before the suite
does.

## House rules

The ones that come up most:

- **79 columns, single quotes.** `ruff format` enforces both; do not argue with
  it by hand.
- **No runtime dependencies.** The tool is stdlib-only on purpose: it keeps the
  container small and the supply chain empty. Proposing one is a discussion to
  open in an issue, not a line to add in a pull request.
- **All network access lives in `http.py`, `wakatime.py` and `github.py`.** No
  other module imports `urllib`, and every request goes through the single
  `_fetch_json()` seam. That seam is what the tests monkeypatch, which is why
  there is no HTTP mocking library in the dev dependencies.
- **Secrets stay in the `Authorization` header.** Both the WakaTime key and the
  GitHub token. Never a query string, a log line, or an exception message.
- **Type hints on every signature.** `mypy --strict` has to pass.
- Every new function gets a test; every bug fix gets a regression test.

## Adding a metric, a block, or a format

All three are module-level `dict` registries - `metrics.py`, `blocks.py` and
`formatters.py`. Add a pure function, add its entry, add a test. If your change
needs the placeholder parser modified, something has gone wrong; say so in the
pull request and let's talk about it.

A metric that reads GitHub rather than WakaTime takes the `gh_` prefix and pulls
from the client passed in on the context. Keep it lazy: a metric must not fetch
anything the file did not ask for.

## Pull requests

- One concern per pull request.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/).
- Update `CHANGELOG.md` under `## [Unreleased]`.
- CI has to be green.
