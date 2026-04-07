from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from shared.rate_limit import RateLimiter


class FetchError(RuntimeError):
    """Raised when an HTTP request fails."""


@dataclass(slots=True)
class FetchResult:
    url: str
    status_code: int
    headers: dict[str, str]
    body: bytes
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status_code < 400

    def text(self, encoding: str = "utf-8") -> str:
        return self.body.decode(encoding, errors="replace")


@dataclass
class HttpClient:
    user_agent: str = "PHMReproAudit/0.1"
    timeout_seconds: int = 30
    default_headers: dict[str, str] = field(default_factory=dict)
    rate_limiter: RateLimiter | None = None
    opener: Any | None = None

    def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> FetchResult:
        if self.rate_limiter is not None:
            self.rate_limiter.wait()
        merged_headers = {"User-Agent": self.user_agent, **self.default_headers}
        if headers:
            merged_headers.update(headers)
        request = Request(url, method=method, data=body, headers=merged_headers)
        opener = self.opener.open if self.opener is not None else urlopen
        try:
            with opener(request, timeout=self.timeout_seconds) as response:
                payload = response.read()
                headers_map = {key: value for key, value in response.headers.items()}
                return FetchResult(
                    url=response.geturl() if hasattr(response, "geturl") else getattr(response, "url", url),
                    status_code=response.status,
                    body=payload,
                    headers=headers_map,
                )
        except HTTPError as exc:
            payload = exc.read() if exc.fp is not None else b""
            return FetchResult(
                url=url,
                status_code=exc.code,
                body=payload,
                headers=dict(exc.headers.items()) if exc.headers is not None else {},
                error=f"{exc.code} {exc.reason}",
            )
        except URLError as exc:
            return FetchResult(
                url=url,
                status_code=0,
                body=b"",
                headers={},
                error=f"Failed to reach {url}: {exc.reason}",
            )

    def get_text(self, url: str, *, headers: dict[str, str] | None = None) -> str:
        artifact = self.fetch(url, headers=headers)
        if not artifact.ok:
            raise FetchError(artifact.error or f"Request failed with status {artifact.status_code}")
        content_type = artifact.headers.get("Content-Type", artifact.headers.get("content-type", ""))
        encoding = content_type.split("charset=")[-1] if "charset=" in content_type else "utf-8"
        return artifact.body.decode(encoding, errors="replace")

    def get_bytes(self, url: str, *, headers: dict[str, str] | None = None) -> bytes:
        artifact = self.fetch(url, headers=headers)
        if not artifact.ok:
            raise FetchError(artifact.error or f"Request failed with status {artifact.status_code}")
        return artifact.body

    def get_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        artifact = self.fetch(url, headers=headers)
        if not artifact.ok:
            raise FetchError(artifact.error or f"Request failed with status {artifact.status_code}")
        return json.loads(artifact.body.decode("utf-8"))

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        merged_headers = {"Content-Type": "application/json"}
        if headers:
            merged_headers.update(headers)
        artifact = self.fetch(
            url,
            method="POST",
            headers=merged_headers,
            body=json.dumps(payload).encode("utf-8"),
        )
        if not artifact.ok:
            raise FetchError(artifact.error or f"Request failed with status {artifact.status_code}")
        return json.loads(artifact.body.decode("utf-8"))
