from __future__ import annotations

from pathlib import Path

from scripts.manual_validation import build_manual_validation_bundle


def main() -> None:
    sample_path, snippets_path = build_manual_validation_bundle(
        Path("."),
        Path("data/validation"),
        source="phm",
    )
    print(sample_path)
    print(snippets_path)


if __name__ == "__main__":
    main()
