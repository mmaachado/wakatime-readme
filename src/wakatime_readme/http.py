#!/usr/bin/env python3
"""JSON over HTTPS.

This module and the two clients built on it are the only places that
touch the network, and every request funnels through the single
`_fetch_json` seam below. Keeping it to one function is what lets the
tests swap the network out without an HTTP mocking library.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

USER_AGENT = 'wakatime-readme'
REDACTED = '***'

# HTTP statuses a caller may reasonably want to retry rather than treat
# as failure: WakaTime answers 202 while it recomputes a long range, and
# the GitHub Contents API answers 409 when the blob moved under us.
ACCEPTED = 202
CONFLICT = 409


class HttpError(Exception):
    """A request failed.

    The message is scrubbed before it reaches here, so it is always safe to
    print or re-raise.

    Example:
        >>> raise HttpError('unauthorized', status=401)
        Traceback (most recent call last):
        HttpError: unauthorized
    """

    def __init__(self, message: str, status: int | None = None) -> None:
        """Record the failure and, when there was one, the HTTP status."""
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Response:
    """One HTTP response with its body already parsed.

    Example:
        >>> Response(200, {'ok': True}).body['ok']
        True
    """

    status: int
    # The APIs return arbitrary JSON shapes; each client narrows its own.
    body: Any


@dataclass(frozen=True)
class Redactor:
    """Strips known secrets out of anything on its way to a human.

    Scrubbing belongs to the transport rather than to each caller, so
    there is exactly one place to audit.

    Example:
        >>> Redactor(('hunter2',)).scrub('token=hunter2')
        'token=***'
    """

    secrets: tuple[str, ...] = ()

    def scrub(self, text: str) -> str:
        """Replace every registered secret with a fixed placeholder."""
        for secret in self.secrets:
            if secret:
                text = text.replace(secret, REDACTED)
        return text


def _decode(payload: bytes) -> Any:  # noqa: ANN401 - shape varies per endpoint
    """Parse a JSON body, tolerating the empty body a 204 carries."""
    if not payload:
        return None
    return json.loads(payload.decode('utf-8'))


def _fetch_json(request: urllib.request.Request, timeout: float) -> Response:
    """Send one request and return its status and parsed body.

    The single network seam of the whole project. An HTTP error status comes
    back as a `Response` rather than an exception, because the callers decide
    which statuses are worth retrying; only transport-level failures raise.

    Example:
        >>> _fetch_json.__name__
        '_fetch_json'
    """
    try:
        # S310: the scheme is fixed by the callers, which build every URL from
        # their own base. No user-supplied scheme reaches this point.
        with urllib.request.urlopen(request, timeout=timeout) as raw:  # noqa: S310
            return Response(raw.status, _decode(raw.read()))
    except urllib.error.HTTPError as error:
        return Response(error.code, _decode(error.read()))
    except urllib.error.URLError as error:
        raise HttpError(f'network error: {error.reason}') from error
    except TimeoutError as error:
        raise HttpError(f'request timed out after {timeout}s') from error


@dataclass(frozen=True)
class JsonClient:
    """Issues authenticated JSON requests against one API base URL.

    Example:
        >>> client = JsonClient('https://api.example.com', {}, Redactor())
        >>> client.base_url
        'https://api.example.com'
    """

    base_url: str
    headers: Mapping[str, str]
    redactor: Redactor
    timeout: float = 30.0

    def request(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
    ) -> Response:
        """Call `path` under the base URL and return the parsed response.

        Example:
            >>> JsonClient.request.__name__
            'request'
        """
        payload = None if body is None else json.dumps(body).encode('utf-8')
        request = urllib.request.Request(  # noqa: S310 - scheme fixed by base_url
            url=f'{self.base_url}{path}',
            data=payload,
            method=method,
            headers={
                'Accept': 'application/json',
                'User-Agent': USER_AGENT,
                **({'Content-Type': 'application/json'} if payload else {}),
                **self.headers,
            },
        )
        return _fetch_json(request, self.timeout)

    def fail(self, message: str, status: int | None = None) -> HttpError:
        """Build a scrubbed error, so no caller can leak a secret."""
        return HttpError(self.redactor.scrub(message), status=status)
