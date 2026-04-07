from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(slots=True)
class OpenRouterSettings:
    base_url: str
    models: list[str]


@dataclass(slots=True)
class PhmSettings:
    issue_urls: dict[int, str]


@dataclass(slots=True)
class IjphmSettings:
    archive_url: str


@dataclass(slots=True)
class PipelineSettings:
    timeout_seconds: int
    user_agent: str


@dataclass(slots=True)
class AppConfig:
    storage_root: str
    openrouter: OpenRouterSettings
    phm: PhmSettings
    ijphm: IjphmSettings
    pipeline: PipelineSettings


def load_config(path: str | Path) -> AppConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return AppConfig(
        storage_root=payload["storage_root"],
        openrouter=OpenRouterSettings(**payload["openrouter"]),
        phm=PhmSettings(
            issue_urls={int(year): url for year, url in payload["phm"]["issue_urls"].items()}
        ),
        ijphm=IjphmSettings(**payload["ijphm"]),
        pipeline=PipelineSettings(**payload["pipeline"]),
    )
