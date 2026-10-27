"""The one place the pipeline talks to the network."""

from __future__ import annotations

import json
from http.client import HTTPException
from urllib.request import Request, urlopen

from brief.config import HTTP_TIMEOUT_SECONDS, MAX_RESPONSE_BYTES, USER_AGENT


class FetchFailed(Exception):
    def __init__(self, url: str, reason: str) -> None:
        super().__init__(f"{url}: {reason}")
        self.url = url
        self.reason = reason


def fetch_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            return response.read(MAX_RESPONSE_BYTES)
    except (OSError, HTTPException) as error:
        raise FetchFailed(url, str(error)) from error


def fetch_json(url: str) -> object:
    payload = fetch_bytes(url)
    try:
        return json.loads(payload)
    except json.JSONDecodeError as error:
        raise FetchFailed(url, f"invalid JSON: {error}") from error
