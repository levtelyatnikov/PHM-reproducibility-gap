from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


_RAW_SOURCE_DIR_MAP = {
    "phm": "phm_conf_society",
    "phm_conf_society": "phm_conf_society",
    "ijphm": "ijphm",
}


@dataclass
class StorageLayout:
    root: Path

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    @property
    def interim_dir(self) -> Path:
        return self.root / "interim"

    @property
    def processed_dir(self) -> Path:
        return self.root / "processed"

    def prepare(self) -> None:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.interim_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def raw_year_dir(self, source: str, year: int) -> Path:
        try:
            source_dir = _RAW_SOURCE_DIR_MAP[source]
        except KeyError as exc:
            raise ValueError(f"Unsupported raw source directory mapping: {source}") from exc
        return self.raw_dir / source_dir / str(year)

    def processed_year_dir(self, collection: str, year: int) -> Path:
        return self.processed_dir / collection / str(year)

    def processed_year_audit_dir(self, collection: str, year: int) -> Path:
        return self.processed_year_dir(collection, year) / "audit"

    def write_text(self, relative_path: str, content: str) -> Path:
        destination = self.root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        return destination

    def write_bytes(self, relative_path: str, content: bytes) -> Path:
        destination = self.root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return destination

    @staticmethod
    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
