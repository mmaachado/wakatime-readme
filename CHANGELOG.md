# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2026-08-26

### Changed

- The action pulls `ghcr.io/mmaachado/wakatime-readme:v1` instead of building
  the Dockerfile on every run, so a consumer's workflow no longer pays for a
  Docker build.

### Added

- Regression test for invariant 9: a commit rejected with `409` costs exactly
  one re-read and one commit, against the sha the re-read returned.
- Chart parity acceptance test: `activity_chart` is rendered end to end, from
  the HTTP seam through the client to the fence, and compared byte for byte
  against the block `athul/waka-readme` had left in a profile README.
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

[Unreleased]: https://github.com/mmaachado/wakatime-readme/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/mmaachado/wakatime-readme/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/mmaachado/wakatime-readme/releases/tag/v1.0.0
