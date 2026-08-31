# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-08-31

A `1.0.2` was prepared but never tagged or published, so its entries are folded
in here rather than kept as a release nobody could install.

### Added

- `keystroke_timeout`, the minutes of pause that still count as coding. It is
  now always sent to WakaTime instead of being left to the account default, and
  defaults to `15` — the value wakatime.com's own profile pages render with.
- A documentation site at <https://mmaachado.github.io/wakatime-readme/>, built
  with MkDocs. It is now the reference for placeholders, configuration and
  behaviour; the README keeps the why, a quickstart and links. It leads with
  **Matching WakaTime**, the guide to the keystroke timeout and why a profile
  and a dashboard report different totals.
- The documentation is versioned with `mike`. A tag publishes its `major.minor`
  series and moves the `latest` alias, which the bare site URL redirects to, so
  the docs for a release stay readable after the next one lands. `master`
  publishes `dev`, which is never the default.

### Fixed

- Published WakaTime totals disagreed with the numbers on wakatime.com. The
  stats request never sent `timeout`, so WakaTime applied the account default
  while its own public profile pages use `15`. On the account this was found
  with, that published 622 hours of Python where the profile advertised 898, and
  an all-time total of 1,248 hours against the profile's 1,918 — every figure
  about a third low, and every one of them plausible enough to go unnoticed.
- Retrying gave up after about three seconds. The backoff slept `2**attempt`
  only while `attempt < retries - 1`, so the default of three attempts waited
  one second and then two. A keystroke timeout WakaTime has not computed before
  answers `202` with `percent_calculated: 0` and needs far longer than that.
- A format was dropped in silence when the metric took no argument.
  `<!--wr:total_hours:1f-->` read `1f` as the argument and fell back to `int`,
  rendering `1920` where the author had asked for `1920.0`. A second field that
  names a known format is now read as the format; `top_lang:2` is still a rank,
  and `metric::format` still works.
- The WakaTime client accepted a partially computed range as final. WakaTime
  answers a request for a range it is still computing with `200` and
  real-looking but incomplete totals: `is_up_to_date` is already `true` while
  `percent_calculated` is still climbing. Both signals now have to agree, and
  the `StaleStats` message names the share it stopped at.
- An empty `data` object counted as a settled answer, because every freshness
  flag defaulted to "fine" when absent. It resolved every metric to zero.
- `pre-commit` could not find its configuration. It had moved to `.github/`,
  where `pre-commit` does not look, so the `uv run pre-commit install` in
  `CONTRIBUTING.md` failed on a contributor's first command.
- `__init__.py` declared version `1.0.0` while `pyproject.toml` had moved on,
  which would have shipped a package whose metadata contradicted its own module.
  A test now fails the moment the two disagree.
- `examples/` was missing from `.prettierignore`, and `examples/workflow.yml`
  had already been requoted to double quotes by a format-on-save — the exact
  damage that file exists to prevent.

### Changed

- **Published numbers will move on the first run after upgrading.** They now
  match wakatime.com's profile pages. Set `keystroke_timeout` to your own
  WakaTime account setting to keep the previous values instead.
- Exhausted retries now exit `2` even without `--strict`. Nothing was written,
  and exiting `0` let a README go on publishing a wrong total with every
  scheduled run green. Failing to *reach* an API is unchanged: still `0` unless
  `--strict`.
- `retries` now defaults to `6`, spending at most 30 seconds asleep between
  attempts rather than 3.

## [1.0.1] - 2026-08-26

### Changed

- The action pulls `ghcr.io/mmaachado/wakatime-readme:v1` instead of building
  the Dockerfile on every run, so a consumer's workflow no longer pays for a
  Docker build.

### Added

- Regression test for invariant 9: a commit rejected with `409` costs exactly
  one re-read and one commit, against the sha the re-read returned.
- Chart parity acceptance test: `activity_chart` is rendered end to end, from
  the HTTP seam through the client to the fence.
- `examples/` with a ready-to-copy profile README and workflow.
- `.prettierignore` and `.gitattributes` covering `tests/fixtures/`, so a
  Markdown formatter cannot reflow the chart alignment the parity test asserts
  and a Windows checkout cannot turn it into CRLF.

### Fixed

- The CI self-test builds the image from the commit under test rather than
  running the published action, and fails unless a placeholder actually
  resolves. It previously stayed green on a container that reached no data.
- `make_graph` documented its `+ 0.5 / markers` term as a rounding bias that
  changes the bar. It does not: for every percentage at every width the bar is
  identical without it. The term is kept for line-by-line comparability with
  the tool this replaces, and the docstring now says so.
- The package advertised itself as alpha after the 1.0.0 release.

## [1.0.0] - 2026-08-24

### Added

- Placeholder engine: `<!--wr:name[:arg][:format]-->` pairs are resolved and
  the text between them replaced, with the markers left in place.
- WakaTime metrics: `lang_hours`, `lang_percent`, `lang_text`, `total_hours`,
  `top_lang`, `daily_average`, `since`.
- GitHub metrics: `gh_followers`, `gh_repos`, `gh_stars`, `gh_top_repo`,
  `gh_repo_stars`, `gh_latest_release`.
- Formats: `floor10`, `floor50`, `floor100`, `int`, `1f`, `raw`.
- `activity_chart` block, rendering the language bar chart.
- Commits through the GitHub Contents API, so a workflow needs neither a
  checkout nor a commit step, and the resulting commit is signed by GitHub.
- Command line interface with `--dry-run` and `--strict`.
- Container action, published image, and release automation.
- Project scaffolding: packaging metadata, tooling configuration, CI and
  community health files.

[Unreleased]: https://github.com/mmaachado/wakatime-readme/compare/v1.0.2...HEAD
[1.0.2]: https://github.com/mmaachado/wakatime-readme/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/mmaachado/wakatime-readme/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/mmaachado/wakatime-readme/releases/tag/v1.0.0
