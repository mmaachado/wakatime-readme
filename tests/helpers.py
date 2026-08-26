#!/usr/bin/env python3
"""Named fakes and fixture loading, shared across the test modules."""

from __future__ import annotations

import base64
import json
import pathlib
import urllib.request
from typing import Any

from wakatime_readme import http

FIXTURES = pathlib.Path(__file__).parent / 'fixtures'

# A decoded API response. Naming the shapes keeps bare `Any` out of every
# test signature without pretending we know more than we do.
Payload = dict[str, Any]
Listing = list[Payload]
Json = Payload | Listing


def load_object(name: str) -> Payload:
    """Read a captured response that is a JSON object."""
    text = (FIXTURES / name).read_text(encoding='utf-8')
    decoded: Payload = json.loads(text)
    return decoded


def load_array(name: str) -> Listing:
    """Read a captured response that is a JSON array."""
    text = (FIXTURES / name).read_text(encoding='utf-8')
    decoded: Listing = json.loads(text)
    return decoded


def load_text(name: str) -> str:
    """Read a fixture that is plain text rather than JSON."""
    return (FIXTURES / name).read_text(encoding='utf-8')


def ok(body: Json | None, status: int = 200) -> http.Response:
    """Stage one response for the fake transport."""
    return http.Response(status, body)


def contents(text: str, sha: str = 'blob-sha') -> Payload:
    """Shape a Contents API response the way GitHub returns one.

    Example:
        >>> contents('hi', sha='abc')['sha']
        'abc'
    """
    encoded = base64.b64encode(text.encode('utf-8')).decode('ascii')
    return {'content': encoded, 'encoding': 'base64', 'sha': sha}


class FakeTransport:
    """Stands in for the single network seam and records every call.

    Responses are consumed strictly in order. Asking for one more than was
    staged fails the test rather than silently repeating the last answer,
    which is how a test can prove something was fetched only once.
    """

    def __init__(self, *responses: http.Response) -> None:
        self._queue = list(responses)
        self.requests: list[urllib.request.Request] = []

    def __call__(
        self, request: urllib.request.Request, timeout: float
    ) -> http.Response:
        self.requests.append(request)
        if not self._queue:
            message = f'unexpected extra request to {request.full_url}'
            raise AssertionError(message)
        return self._queue.pop(0)

    @property
    def calls(self) -> list[tuple[str, str]]:
        """Method and URL of each request, in the order they were made."""
        return [
            (request.get_method(), request.full_url)
            for request in self.requests
        ]

    @property
    def call_count(self) -> int:
        """How many requests actually went through the seam."""
        return len(self.requests)

    def sent(self, index: int = 0) -> Payload:
        """The JSON body that went out with one request."""
        data = self.requests[index].data
        if not isinstance(data, bytes):
            message = f'request {index} carried no body'
            raise AssertionError(message)
        decoded: Payload = json.loads(data.decode('utf-8'))
        return decoded

    def header(self, name: str, index: int = 0) -> str | None:
        """One header of a request, or None when it was not sent."""
        return self.requests[index].get_header(name.capitalize())


class NeverCalled:
    """A seam that fails the test the moment anything touches it.

    Used to prove that a provider nobody asked for is never contacted.
    """

    def __call__(
        self, request: urllib.request.Request, timeout: float
    ) -> http.Response:
        message = (
            f'network used when it should not have been: {request.full_url}'
        )
        raise AssertionError(message)
