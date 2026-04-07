from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable

from shared.http import HttpClient
from shared.schemas import EvidenceWindow, JudgeVote, RuleAssessment


@dataclass(slots=True)
class OpenRouterClient:
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    http_client: HttpClient | None = None
    transport: Callable[[str, bytes, dict[str, str]], tuple[int, str]] | None = None

    def chat(self, model: str, messages: list[dict[str, str]]) -> dict[str, Any]:
        payload = {"model": model, "messages": messages, "temperature": 0}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://phm-reproducibility-gap.invalid",
            "X-Title": "PHM Repro Audit",
        }
        if self.transport is not None:
            status, text = self.transport(self.base_url, json.dumps(payload).encode("utf-8"), headers)
            if status >= 400:
                raise RuntimeError(f"OpenRouter transport error: {status}")
            return json.loads(text)
        if self.http_client is None:
            raise RuntimeError("OpenRouterClient requires either http_client or transport")
        url = self.base_url
        if not url.endswith("/chat/completions"):
            url = f"{url.rstrip('/')}/chat/completions"
        return self.http_client.post_json(url, payload, headers=headers)

    def judge(
        self,
        *,
        model: str,
        channel: str,
        text: str,
        evidence_windows: list[EvidenceWindow],
        deterministic: RuleAssessment,
    ) -> JudgeVote:
        prompt = _build_prompt(channel, text, evidence_windows, deterministic)
        response = self.chat(
            model,
            [
                {
                    "role": "system",
                    "content": "Classify reproducibility evidence into A1-A5 conservatively and return JSON.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = extract_response_text(response)
        parsed = _parse_judge_payload(content)
        return JudgeVote(
            model=model,
            channel=channel,
            label=parsed["label"],
            confidence=float(parsed["confidence"]),
            rationale=parsed["rationale"],
        )


def extract_response_text(response: dict[str, Any]) -> str:
    return response["choices"][0]["message"]["content"]


def _build_prompt(
    channel: str,
    text: str,
    evidence_windows: list[EvidenceWindow],
    deterministic: RuleAssessment,
) -> str:
    snippets = "\n".join(
        f"- url={window.url!r} context={window.context[:220]!r}" for window in evidence_windows[:5]
    )
    return (
        f"Channel: {channel}\n"
        f"Deterministic label: {deterministic.label}\n"
        f"Deterministic reasons: {deterministic.reasons}\n"
        f"Evidence windows:\n{snippets}\n"
        "Return JSON with keys label, confidence, rationale.\n"
        f"Text excerpt:\n{text[:2500]}"
    )


def _parse_judge_payload(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except Exception:
        return {"label": "A5", "confidence": 0.2, "rationale": content[:500]}


def build_stub_votes(channel: str, deterministic: RuleAssessment, models: list[str]) -> list[JudgeVote]:
    return [
        JudgeVote(
            model=model,
            channel=channel,
            label=deterministic.label,
            confidence=max(0.51, deterministic.confidence - index * 0.05),
            rationale="stub vote mirroring deterministic baseline",
        )
        for index, model in enumerate(models)
    ]


def require_api_key(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
