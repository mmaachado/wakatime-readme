#!/usr/bin/env python3
"""Pytest fixtures. The fakes themselves live in `tests.helpers`."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.helpers import (
    FakeTransport,
    Listing,
    Payload,
    load_array,
    load_object,
)
from wakatime_readme import http, wakatime


@pytest.fixture
def transport(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[..., FakeTransport]:
    """Install a fake network seam, returning it so tests can inspect it."""

    def install(*responses: http.Response) -> FakeTransport:
        fake = FakeTransport(*responses)
        monkeypatch.setattr(http, '_fetch_json', fake)
        return fake

    return install


@pytest.fixture
def all_time() -> Payload:
    """The real all-time stats response captured from the live API."""
    return load_object('wakatime_all_time.json')


@pytest.fixture
def gh_user() -> Payload:
    """The real profile response captured from the live API."""
    return load_object('github_user.json')


@pytest.fixture
def gh_repos() -> Listing:
    """The real repository listing captured from the live API."""
    return load_array('github_repos.json')


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Collapse the retry backoff so a test does not wait on real time."""
    monkeypatch.setattr(wakatime.time, 'sleep', lambda _seconds: None)
