from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


_CATEGORIES = ("A1", "A2", "A3", "A4", "A5")
_CHANNELS = ("Code", "Data")
_STACKED_FIGURE_CONFIGS = (
    ("phm_society_conf", "PHM Society Conference"),
    ("ijphm", "IJPHM"),
)
_POOLED_CATEGORIES = (
    "Neither publicly available",
    "Only data publicly available",
    "Only code publicly available",
    "Both code and data publicly available",
)
_STACK_COLORS = {
    "A1": "#203864",
    "A2": "#5b7db1",
    "A3": "#92714a",
    "A4": "#c58a43",
    "A5": "#d9dde3",
}
_OVERVIEW_COLORS = {
    "Neither publicly available": "#b63a28",
    "Only data publicly available": "#d17b49",
    "Only code publicly available": "#d17b49",
    "Both code and data publicly available": "#8d2217",
}
_CONTEXT_COLORS = {
    "Strict data A1": "#203864",
    "Named benchmark": "#8b6c42",
    "External public data": "#d17b49",
}


@dataclass(frozen=True, slots=True)
class PlotRecord:
    figure_key: str
    year: int
    channel: str
    category: str
    count: int
    total: int
    proportion: float


@dataclass(frozen=True, slots=True)
class PooledAvailabilityRecord:
    category: str
    count: int
    total: int
    proportion: float


@dataclass(frozen=True, slots=True)
class PublicDataContextRecord:
    scope: str
    category: str
    count: int
    total: int
    proportion: float


def _read_audit_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _load_source_rows(
    *,
    processed_root: Path,
    years: Iterable[int],
) -> dict[str, dict[int, list[dict[str, str]]]]:
    years = tuple(years)
    source_rows: dict[str, dict[int, list[dict[str, str]]]] = {
        "phm_society_conf": {},
        "ijphm": {},
    }
    for source in source_rows:
        for year in years:
            audit_path = processed_root / source / str(year) / "audit" / "audit_results.csv"
            source_rows[source][year] = _read_audit_rows(audit_path) if audit_path.exists() else []
    return source_rows


def collect_plot_records(
    *,
    processed_root: Path,
    years: Iterable[int] = (2022, 2023, 2024, 2025),
) -> list[PlotRecord]:
    records: list[PlotRecord] = []
    years = tuple(years)
    source_rows = _load_source_rows(processed_root=processed_root, years=years)

    for figure_key, _ in _STACKED_FIGURE_CONFIGS:
        for year in years:
            rows = source_rows[figure_key][year]
            for channel in _CHANNELS:
                label_key = "code_label" if channel == "Code" else "data_label"
                total = len(rows)
                for category in _CATEGORIES:
                    count = sum(1 for row in rows if row.get(label_key) == category)
                    proportion = (count / total) if total else 0.0
                    records.append(
                        PlotRecord(
                            figure_key=figure_key,
                            year=year,
                            channel=channel,
                            category=category,
                            count=count,
                            total=total,
                            proportion=proportion,
                        )
                    )
    return records


def collect_pooled_availability_records(
    *,
    processed_root: Path,
    years: Iterable[int] = (2022, 2023, 2024, 2025),
) -> list[PooledAvailabilityRecord]:
    years = tuple(years)
    source_rows = _load_source_rows(processed_root=processed_root, years=years)
    rows = []
    for source in source_rows:
        for year in years:
            rows.extend(source_rows[source][year])

    total = len(rows)
    counts = {category: 0 for category in _POOLED_CATEGORIES}
    for row in rows:
        code_public = row.get("code_label") == "A1"
        data_public = row.get("data_label") == "A1"
        if code_public and data_public:
            counts["Both code and data publicly available"] += 1
        elif code_public:
            counts["Only code publicly available"] += 1
        elif data_public:
            counts["Only data publicly available"] += 1
        else:
            counts["Neither publicly available"] += 1

    return [
        PooledAvailabilityRecord(
            category=category,
            count=counts[category],
            total=total,
            proportion=(counts[category] / total) if total else 0.0,
        )
        for category in _POOLED_CATEGORIES
    ]


def collect_public_data_context_records(
    *,
    processed_root: Path,
    years: Iterable[int] = (2022, 2023, 2024, 2025),
) -> list[PublicDataContextRecord]:
    years = tuple(years)
    source_rows = _load_source_rows(processed_root=processed_root, years=years)

    def _rows_for(source_key: str | None) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for source in source_rows:
            if source_key is not None and source != source_key:
                continue
            for year in years:
                rows.extend(source_rows[source][year])
        return rows

    scopes = [
        ("Pooled", None),
        ("PHM Society Conference", "phm_society_conf"),
        ("IJPHM", "ijphm"),
    ]
    records: list[PublicDataContextRecord] = []
    for label, source_key in scopes:
        rows = _rows_for(source_key)
        total = len(rows)
        named_benchmark = sum(
            row.get("data_named_public_benchmark", "").lower() in {"1", "true", "yes"} for row in rows
        )
        external_public = sum(
            row.get("data_public_external_dataset", "").lower() in {"1", "true", "yes"} for row in rows
        )
        strict_data_a1 = sum(row.get("data_label") == "A1" for row in rows)
        for category, count in (
            ("Strict data A1", strict_data_a1),
            ("Named benchmark", named_benchmark),
            ("External public data", external_public),
        ):
            records.append(
                PublicDataContextRecord(
                    scope=label,
                    category=category,
                    count=count,
                    total=total,
                    proportion=(count / total) if total else 0.0,
                )
            )
    return records


def _plot_records_for(records: list[PlotRecord], figure_key: str) -> list[PlotRecord]:
    return [record for record in records if record.figure_key == figure_key]


def _write_plot_data(output_dir: Path, records: list[PlotRecord]) -> Path:
    output_path = output_dir / "plot_data.csv"
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["figure_key", "year", "channel", "category", "count", "total", "proportion"],
        )
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))
    return output_path


def _write_pooled_overview_data(output_dir: Path, records: list[PooledAvailabilityRecord]) -> Path:
    output_path = output_dir / "pooled_overview_data.csv"
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["category", "count", "total", "proportion"])
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))
    return output_path


def _write_public_data_context_data(output_dir: Path, records: list[PublicDataContextRecord]) -> Path:
    output_path = output_dir / "public_data_context_data.csv"
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["scope", "category", "count", "total", "proportion"])
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))
    return output_path


def _render_pooled_overview_figure(records: list[PooledAvailabilityRecord], *, output_prefix: Path) -> list[Path]:
    ordered = list(records)
    categories = [record.category.replace(" publicly available", "\npublicly available") for record in ordered]
    proportions = [record.proportion for record in ordered]
    y_positions = list(range(len(ordered)))

    fig, ax = plt.subplots(figsize=(6.2, 3.15))
    ax.barh(
        y_positions,
        proportions,
        color=[_OVERVIEW_COLORS[record.category] for record in ordered],
        height=0.64,
        edgecolor="none",
    )

    ax.set_yticks(y_positions, categories)
    ax.invert_yaxis()
    ax.set_xlim(0.0, 1.06)
    ax.set_xlabel("")
    ax.xaxis.set_visible(False)
    ax.tick_params(axis="y", length=0, pad=8, labelsize=10.5)
    for spine in ("top", "right", "bottom", "left"):
        ax.spines[spine].set_visible(False)
    ax.axvline(0.0, color="#dfe3e8", linewidth=1.1)

    for idx, proportion in enumerate(proportions):
        percentage = f"{proportion * 100:.1f}%"
        label_x = proportion + 0.015 if proportion > 0 else 0.015
        ax.text(
            label_x,
            idx,
            percentage,
            va="center",
            ha="left",
            fontsize=10.5,
            color="#2b2f33",
            fontweight="semibold" if proportion > 0.05 else "normal",
        )

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    fig.tight_layout()

    pdf_path = output_prefix.with_suffix(".pdf")
    png_path = output_prefix.with_suffix(".png")
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return [pdf_path, png_path]


def _render_stacked_figure(records: list[PlotRecord], *, title: str, output_prefix: Path) -> list[Path]:
    years = sorted({record.year for record in records})
    fig, ax = plt.subplots(figsize=(8.8, 4.6))

    x_positions: list[float] = []
    x_labels: list[str] = []
    year_centers: list[float] = []
    current_x = 0.0
    bar_width = 0.74
    year_gap = 0.85

    for year in years:
        code_x = current_x
        data_x = current_x + 1.0
        x_positions.extend([code_x, data_x])
        x_labels.extend(["Code", "Data"])
        year_centers.append((code_x + data_x) / 2)
        current_x += 2.0 + year_gap

    bottoms = [0.0] * len(x_positions)
    for category in _CATEGORIES:
        heights: list[float] = []
        for year in years:
            for channel in _CHANNELS:
                matching = next(
                    record
                    for record in records
                    if record.year == year and record.channel == channel and record.category == category
                )
                heights.append(matching.proportion)
        ax.bar(
            x_positions,
            heights,
            bar_width,
            bottom=bottoms,
            color=_STACK_COLORS[category],
            edgecolor="white",
            linewidth=0.8,
            label=category,
        )
        bottoms = [bottom + height for bottom, height in zip(bottoms, heights)]

    ax.set_ylim(0, 1.0)
    ax.set_xlim(min(x_positions) - 0.7, max(x_positions) + 0.7)
    ax.set_ylabel("Share of papers")
    ax.set_xticks(x_positions, x_labels)
    ax.set_title(title, fontsize=13, fontweight="semibold", pad=14)
    ax.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0], ["0%", "25%", "50%", "75%", "100%"])
    ax.grid(axis="y", color="#e7eaef", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", labelsize=10)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    for center, year in zip(year_centers, years):
        ax.text(center, 1.03, str(year), ha="center", va="bottom", fontsize=10, transform=ax.get_xaxis_transform())

    legend_handles = [Patch(facecolor=_STACK_COLORS[category], edgecolor="white", label=category) for category in _CATEGORIES]
    ax.legend(
        handles=legend_handles,
        ncol=5,
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.16),
        columnspacing=1.1,
        handlelength=1.25,
    )

    fig.tight_layout()
    pdf_path = output_prefix.with_suffix(".pdf")
    png_path = output_prefix.with_suffix(".png")
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return [pdf_path, png_path]


def _render_label_distribution_figure(records: list[PlotRecord], *, output_prefix: Path) -> list[Path]:
    scopes = [
        ("Pooled", None),
        ("PHM Society Conference", "phm_society_conf"),
        ("IJPHM", "ijphm"),
    ]
    rows: list[tuple[str, str, list[float]]] = []
    for scope_label, figure_key in scopes:
        for channel in _CHANNELS:
            if figure_key is None:
                relevant = [record for record in records if record.channel == channel]
            else:
                relevant = [record for record in records if record.figure_key == figure_key and record.channel == channel]
            total = sum(record.count for record in relevant)
            proportions = []
            for category in _CATEGORIES:
                count = sum(record.count for record in relevant if record.category == category)
                proportions.append((count / total) if total else 0.0)
            rows.append((scope_label, channel, proportions))

    y_positions = list(range(len(rows)))
    labels = [f"{scope}\n{channel}" for scope, channel, _ in rows]
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    lefts = [0.0] * len(rows)
    for category_idx, category in enumerate(_CATEGORIES):
        widths = [row[2][category_idx] for row in rows]
        ax.barh(
            y_positions,
            widths,
            left=lefts,
            color=_STACK_COLORS[category],
            edgecolor="white",
            linewidth=0.8,
            height=0.72,
            label=category,
        )
        lefts = [left + width for left, width in zip(lefts, widths)]

    ax.set_xlim(0, 1.0)
    ax.set_yticks(y_positions, labels)
    ax.invert_yaxis()
    ax.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel("Share of papers")
    ax.grid(axis="x", color="#e7eaef", linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(ncol=5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.14), columnspacing=1.0, handlelength=1.2)
    fig.tight_layout()

    pdf_path = output_prefix.with_suffix(".pdf")
    png_path = output_prefix.with_suffix(".png")
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return [pdf_path, png_path]


def _render_public_data_context_figure(records: list[PublicDataContextRecord], *, output_prefix: Path) -> list[Path]:
    scopes = ["Pooled", "PHM Society Conference", "IJPHM"]
    categories = ["Strict data A1", "Named benchmark", "External public data"]
    fig, ax = plt.subplots(figsize=(6.9, 3.6))

    y_positions = list(range(len(scopes)))
    offsets = [-0.24, 0.0, 0.24]
    bar_height = 0.2
    for offset, category in zip(offsets, categories, strict=False):
        widths = [
            next(
                record.proportion
                for record in records
                if record.scope == scope and record.category == category
            )
            for scope in scopes
        ]
        ax.barh(
            [y + offset for y in y_positions],
            widths,
            height=bar_height,
            color=_CONTEXT_COLORS[category],
            edgecolor="none",
            label=category,
        )

    ax.set_yticks(y_positions, scopes)
    ax.invert_yaxis()
    ax.set_xlim(0, 0.35)
    ax.set_xticks([0.0, 0.1, 0.2, 0.3], ["0%", "10%", "20%", "30%"])
    ax.set_xlabel("Share of papers")
    ax.grid(axis="x", color="#e7eaef", linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.2), columnspacing=1.2, handlelength=1.3)
    fig.tight_layout()

    pdf_path = output_prefix.with_suffix(".pdf")
    png_path = output_prefix.with_suffix(".png")
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return [pdf_path, png_path]


def build_all_figures(
    *,
    processed_root: Path,
    output_dir: Path,
    years: Iterable[int] = (2022, 2023, 2024, 2025),
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    detailed_records = collect_plot_records(processed_root=processed_root, years=years)
    pooled_records = collect_pooled_availability_records(processed_root=processed_root, years=years)
    public_data_context_records = collect_public_data_context_records(processed_root=processed_root, years=years)
    generated: list[Path] = []
    generated.append(_write_plot_data(output_dir, detailed_records))
    generated.append(_write_pooled_overview_data(output_dir, pooled_records))
    generated.append(_write_public_data_context_data(output_dir, public_data_context_records))
    generated.extend(
        _render_pooled_overview_figure(
            pooled_records,
            output_prefix=output_dir / "pooled_reproducibility_2022_2025",
        )
    )
    generated.extend(
        _render_label_distribution_figure(
            detailed_records,
            output_prefix=output_dir / "strict_label_distribution_2022_2025",
        )
    )
    generated.extend(
        _render_public_data_context_figure(
            public_data_context_records,
            output_prefix=output_dir / "public_data_context_2022_2025",
        )
    )
    for figure_key, title in _STACKED_FIGURE_CONFIGS:
        output_prefix = output_dir / f"{figure_key}_reproducibility_2022_2025"
        generated.extend(_render_stacked_figure(_plot_records_for(detailed_records, figure_key), title=title, output_prefix=output_prefix))
    return generated


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    processed_root = project_root / "data" / "processed"
    output_dir = project_root / "plots" / "output"
    generated = build_all_figures(processed_root=processed_root, output_dir=output_dir)
    for path in generated:
        print(path)


if __name__ == "__main__":
    main()
