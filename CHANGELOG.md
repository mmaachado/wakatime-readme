# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/mmaachado/wakatime-readme/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/mmaachado/wakatime-readme/releases/tag/v1.0.0
