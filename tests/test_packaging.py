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
