from __future__ import annotations

import unittest
from dataclasses import dataclass
from email.message import Message
from urllib import error

from shared.http import FetchResult, HttpClient


@dataclass
class FakeResponse:
    body: bytes
    status: int = 200
    url: str = "https://example.com"

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    @property
    def headers(self) -> Message:
        message = Message()
        message["Content-Type"] = "text/plain; charset=utf-8"
        return message

    def read(self) -> bytes:
        return self.body


class FakeOpener:
    def __init__(self, response: FakeResponse | Exception) -> None:
        self.response = response
        self.requests = []

    def open(self, req, timeout: float | None = None):
        self.requests.append((req, timeout))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class HttpClientTests(unittest.TestCase):
    def test_fetch_returns_structured_success_result(self) -> None:
        opener = FakeOpener(FakeResponse(b"hello"))
        client = HttpClient(opener=opener)
        result = client.fetch("https://example.com")
        self.assertTrue(result.ok)
        self.assertEqual(result.text(), "hello")
        self.assertEqual(result.headers["Content-Type"], "text/plain; charset=utf-8")

    def test_fetch_converts_http_error_to_result(self) -> None:
        http_error = error.HTTPError(
            url="https://example.com",
            code=404,
            msg="Not Found",
            hdrs=Message(),
            fp=None,
        )
        opener = FakeOpener(http_error)
        client = HttpClient(opener=opener)
        result = client.fetch("https://example.com")
        self.assertEqual(result.status_code, 404)
        self.assertFalse(result.ok)
        self.assertIn("Not Found", result.error or "")


if __name__ == "__main__":
    unittest.main()

