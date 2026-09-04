#!/usr/bin/env python3
"""Guards on what the built package claims about itself."""

from __future__ import annotations

import pathlib
import tomllib

import wakatime_readme

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_the_package_version_matches_the_project_version() -> None:
    """Two places state the version, so they can disagree -- and did.

    `__init__.py` sat at 1.0.0 while `pyproject.toml` had moved twice,
    which would have shipped a wheel whose metadata contradicted its own
    module. Bumping a release means editing both; this fails the moment
    only one of them moves.
    """
    pyproject = tomllib.loads(
        (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    )

    assert wakatime_readme.__version__ == pyproject['project']['version']


def test_the_action_metadata_sits_where_the_runner_looks() -> None:
    """`uses: owner/repo@ref` reads action.yml at the root and nowhere else.

    1.1.0 moved this into `.github/`. The runner found no metadata but a
    Dockerfile, fell back to a Dockerfile action, and so never read
    `inputs:` -- which dropped `github_token`'s default, the one input
    with no fallback in `config.py`. Every consumer's commit went out
    unauthenticated and every run stayed green.
    """
    metadata = ROOT / 'action.yml'

    assert metadata.is_file()
    # A copy left behind would drift from the one that is actually read.
    assert not (ROOT / '.github' / 'action.yml').exists()

    text = metadata.read_text(encoding='utf-8')
    assert 'github_token:' in text
    assert '${{ github.token }}' in text
