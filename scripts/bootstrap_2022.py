from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from engine.consensus import build_consensus
from engine.evidence import extract_evidence_windows
from engine.judges import OpenRouterClient, build_stub_votes, require_api_key
from engine.rules import (
    classify_channel,
    detect_named_public_benchmark_data,
    detect_public_external_dataset,
)
from engine.scoring import build_output_rows
from parsers.ijphm_ojs import (
    parse_archive_html as parse_ijphm_archive_html,
    parse_article_html as parse_ijphm_article_html,
    parse_issue_html as parse_ijphm_issue_html,
)
from parsers.phm_ojs import filter_main_papers, parse_article_html, parse_issue_html
from shared.http import FetchError, HttpClient
from shared.manifest import write_csv, write_jsonl
from shared.normalize import normalized_pdf_name
from shared.pdf_extract import extract_text_from_pdf
from shared.rate_limit import RateLimiter
from shared.schemas import ArticlePageDetails, PaperRecord
from shared.settings import AppConfig, load_config
from shared.storage import StorageLayout


_YEARLY_AUDIT_COLLECTIONS = {
    "phm": "phm_society_conf",
    "ijphm": "ijphm",
}
_FULL_TEXT_REQUIRED_SOURCES = frozenset({"phm", "ijphm"})


@dataclass(slots=True)
class AnalysisTextSelection:
    text: str
    source: str
    policy_passed: bool
    note: str


def _progress(message: str) -> None:
    print(f"[bootstrap] {message}", flush=True)


def _judge_votes(
    *,
    judge_client: OpenRouterClient | None,
    channel: str,
    text: str,
    evidence: list,
    deterministic,
    models: list[str],
):
    if judge_client is None:
        return build_stub_votes(channel, deterministic, models)
    votes = []
    for model in models:
        try:
            votes.append(
                judge_client.judge(
                    model=model,
                    channel=channel,
                    text=text,
                    evidence_windows=evidence,
                    deterministic=deterministic,
                )
            )
        except Exception as exc:  # noqa: BLE001
            votes.append(
                build_stub_votes(channel, deterministic, [f"{model}:fallback"])[0]
            )
            votes[-1].rationale = f"fallback after judge failure: {exc}"
            votes[-1].confidence = min(votes[-1].confidence, 0.4)
    return votes


def _analysis_text_selection(
    paper: PaperRecord,
    *,
    allow_abstract_fallback: bool = False,
) -> AnalysisTextSelection:
    extracted_text = str(paper.metadata.get("extracted_text", "") or "").strip()
    if extracted_text:
        selection = AnalysisTextSelection(
            text=extracted_text,
            source="full_text",
            policy_passed=True,
            note="Final labels were computed from extracted full paper text.",
        )
    elif allow_abstract_fallback and (paper.abstract or "").strip():
        selection = AnalysisTextSelection(
            text=(paper.abstract or "").strip(),
            source="abstract_fallback",
            policy_passed=False,
            note="Abstract fallback is preview/debug only and must not be used for final PHM/IJPHM statistics.",
        )
    else:
        selection = AnalysisTextSelection(
            text="",
            source="missing_full_text",
            policy_passed=False,
            note="No usable extracted full paper text was available for final PHM/IJPHM classification.",
        )

    paper.metadata["analysis_text_source"] = selection.source
    paper.metadata["analysis_text_policy_passed"] = selection.policy_passed
    paper.metadata["analysis_text_policy_note"] = selection.note

    if paper.source in _FULL_TEXT_REQUIRED_SOURCES:
        eligible = selection.policy_passed and paper.retrieval_status == "full_text"
        paper.metadata["repro_audit_eligible"] = eligible
    else:
        paper.metadata.setdefault(
            "repro_audit_eligible",
            selection.policy_passed and paper.retrieval_status == "full_text",
        )

    return selection


def _select_analysis_text(
    paper: PaperRecord,
    *,
    allow_abstract_fallback: bool = False,
) -> str:
    return _analysis_text_selection(
        paper,
        allow_abstract_fallback=allow_abstract_fallback,
    ).text


def _build_rows(
    papers: Iterable[PaperRecord],
    models: list[str],
    *,
    judge_client: OpenRouterClient | None = None,
) -> tuple[list[dict], list[dict], list[dict]]:
    results: list[dict] = []
    traces: list[dict] = []
    reviews: list[dict] = []
    papers = list(papers)
    total = len(papers)
    for index, paper in enumerate(papers, start=1):
        if index == 1 or index % 25 == 0 or index == total:
            _progress(f"analyzing paper {index}/{total}: {paper.paper_id}")
        text = _select_analysis_text(paper)
        benchmark_flag, benchmark_name, benchmark_note = detect_named_public_benchmark_data(text)
        external_flag, external_type, external_note = detect_public_external_dataset(text)
        paper.metadata["data_named_public_benchmark"] = benchmark_flag
        paper.metadata["data_public_benchmark_name"] = benchmark_name or ""
        paper.metadata["data_public_benchmark_note"] = benchmark_note or ""
        paper.metadata["data_public_external_dataset"] = external_flag
        paper.metadata["data_public_external_dataset_type"] = external_type or ""
        paper.metadata["data_public_external_dataset_note"] = external_note or ""
        code_evidence = extract_evidence_windows(text)
        data_evidence = extract_evidence_windows(text)
        code_deterministic = classify_channel("code", text, code_evidence)
        data_deterministic = classify_channel("data", text, data_evidence)
        code_votes = _judge_votes(
            judge_client=judge_client,
            channel="code",
            text=text,
            evidence=code_evidence,
            deterministic=code_deterministic,
            models=models,
        )
        data_votes = _judge_votes(
            judge_client=judge_client,
            channel="data",
            text=text,
            evidence=data_evidence,
            deterministic=data_deterministic,
            models=models,
        )
        code_decision = build_consensus(
            channel="code",
            deterministic_label=code_deterministic.label,
            deterministic_confidence=code_deterministic.confidence,
            deterministic_reasons=code_deterministic.reasons,
            deterministic_note=code_deterministic.note,
            deterministic_urls=code_deterministic.supporting_urls,
            votes=code_votes,
        )
        data_decision = build_consensus(
            channel="data",
            deterministic_label=data_deterministic.label,
            deterministic_confidence=data_deterministic.confidence,
            deterministic_reasons=data_deterministic.reasons,
            deterministic_note=data_deterministic.note,
            deterministic_urls=data_deterministic.supporting_urls,
            votes=data_votes,
        )
        result_row, trace_row, review_row = build_output_rows(paper, code_decision, data_decision)
        results.append(result_row)
        traces.append(trace_row)
        if review_row is not None:
            reviews.append(review_row)
    return results, traces, reviews


def _paper_manifest_rows(papers: list[PaperRecord]) -> list[dict[str, object]]:
    return [
        {
            "paper_id": paper.paper_id,
            "source": paper.source,
            "year": paper.year,
            "track": paper.track,
            "title": paper.title,
            "doi": paper.doi or "",
            "article_url": paper.article_url,
            "pdf_url": paper.pdf_url or "",
            "retrieval_status": paper.retrieval_status,
            "repro_audit_eligible": paper.metadata.get(
                "repro_audit_eligible",
                paper.retrieval_status == "full_text",
            ),
            "analysis_text_source": paper.metadata.get("analysis_text_source", ""),
            "analysis_text_policy_passed": paper.metadata.get("analysis_text_policy_passed", False),
            "analysis_text_policy_note": paper.metadata.get("analysis_text_policy_note", ""),
            "text_provider": paper.metadata.get("text_provider", ""),
            "artifact_count": len(paper.metadata.get("artifact_paths", [])),
        }
        for paper in papers
    ]


def _public_paper_payload(paper: PaperRecord) -> dict[str, object]:
    payload = paper.to_dict()
    metadata = dict(payload.get("metadata", {}))
    metadata.pop("extracted_text", None)
    metadata.pop("artifact_paths", None)
    metadata.pop("article_payload_path", None)
    metadata.pop("pdf_warnings", None)
    payload["metadata"] = metadata
    return payload


def _audit_summary(
    papers: list[PaperRecord],
    results: list[dict[str, object]],
    *,
    source_group: str | None = None,
    year: int | None = None,
) -> dict[str, object]:
    eligible_rows = [row for row in results if bool(row.get("repro_audit_eligible", False))]
    return {
        "source_group": source_group or "combined",
        "year": year,
        "paper_count": len(papers),
        "repro_audit_eligible_count": len(eligible_rows),
        "track_counts": dict(Counter(paper.track for paper in papers)),
        "retrieval_status_counts": dict(Counter(paper.retrieval_status for paper in papers)),
        "analysis_text_source_counts": dict(
            Counter(str(row.get("analysis_text_source", "")) for row in results)
        ),
        "code_label_counts": dict(Counter(str(row["code_label"]) for row in results)),
        "data_label_counts": dict(Counter(str(row["data_label"]) for row in results)),
        "eligible_code_label_counts": dict(Counter(str(row["code_label"]) for row in eligible_rows)),
        "eligible_data_label_counts": dict(Counter(str(row["data_label"]) for row in eligible_rows)),
        "data_named_public_benchmark_count": sum(
            bool(row.get("data_named_public_benchmark", False)) for row in results
        ),
        "eligible_data_named_public_benchmark_count": sum(
            bool(row.get("data_named_public_benchmark", False)) for row in eligible_rows
        ),
        "data_public_external_dataset_count": sum(
            bool(row.get("data_public_external_dataset", False)) for row in results
        ),
        "eligible_data_public_external_dataset_count": sum(
            bool(row.get("data_public_external_dataset", False)) for row in eligible_rows
        ),
        "data_public_benchmark_name_counts": dict(
            Counter(
                str(row["data_public_benchmark_name"])
                for row in results
                if row.get("data_public_benchmark_name")
            )
        ),
        "data_public_external_dataset_type_counts": dict(
            Counter(
                str(row["data_public_external_dataset_type"])
                for row in results
                if row.get("data_public_external_dataset_type")
            )
        ),
        "review_required_count": sum(bool(row["review_required"]) for row in results),
    }


def _write_audit_bundle(
    output_dir: Path,
    papers: list[PaperRecord],
    models: list[str],
    *,
    judge_client: OpenRouterClient | None = None,
    source_group: str | None = None,
    year: int | None = None,
) -> dict[str, Path]:
    scope = source_group or "combined"
    scope_label = f"{scope} {year}" if year is not None else scope
    _progress(f"writing audit bundle for {scope_label} ({len(papers)} papers)")
    results, traces, reviews = _build_rows(papers, models, judge_client=judge_client)
    papers_jsonl = write_jsonl(output_dir / "papers.jsonl", [_public_paper_payload(paper) for paper in papers])
    audit_results = write_csv(output_dir / "audit_results.csv", results)
    audit_trace = write_csv(output_dir / "audit_trace.csv", traces)
    review_fields = ["paper_id", "source", "year", "title", "code_label", "data_label", "reasons"]
    manual_review = write_csv(output_dir / "manual_review_queue.csv", reviews, fieldnames=review_fields)
    paper_manifest = write_csv(output_dir / "paper_manifest.csv", _paper_manifest_rows(papers))
    summary_path = output_dir / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(
            _audit_summary(papers, results, source_group=source_group, year=year),
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return {
        "audit_results": audit_results,
        "audit_trace": audit_trace,
        "manual_review": manual_review,
        "papers_jsonl": papers_jsonl,
        "paper_manifest": paper_manifest,
        "summary": summary_path,
    }


def _write_grouped_yearly_audits(
    storage: StorageLayout,
    papers: list[PaperRecord],
    models: list[str],
    *,
    judge_client: OpenRouterClient | None = None,
) -> dict[tuple[str, int], dict[str, Path]]:
    grouped: dict[tuple[str, int], list[PaperRecord]] = defaultdict(list)
    for paper in papers:
        grouped[(paper.source, paper.year)].append(paper)

    outputs: dict[tuple[str, int], dict[str, Path]] = {}
    for (source, year), grouped_papers in sorted(grouped.items()):
        collection = _YEARLY_AUDIT_COLLECTIONS[source]
        output_dir = storage.processed_year_audit_dir(collection, year)
        outputs[(source, year)] = _write_audit_bundle(
            output_dir,
            grouped_papers,
            models,
            judge_client=judge_client,
            source_group=collection,
            year=year,
        )
    return outputs


def _write_outputs(
    storage: StorageLayout,
    papers: list[PaperRecord],
    models: list[str],
    *,
    judge_client: OpenRouterClient | None = None,
) -> dict[str, Path]:
    write_jsonl(storage.interim_dir / "papers.jsonl", [_public_paper_payload(paper) for paper in papers])
    outputs = _write_audit_bundle(storage.processed_dir, papers, models, judge_client=judge_client)
    _write_grouped_yearly_audits(storage, papers, models, judge_client=judge_client)
    return outputs


def bootstrap_fixture_run(root: Path) -> dict[str, Path]:
    storage = StorageLayout(root / "data")
    storage.prepare()
    paper = PaperRecord(
        paper_id="phm-2022-fixture",
        source="phm",
        year=2022,
        track="Technical Research Papers",
        title="Fixture Paper",
        authors=["Jane Doe"],
        article_url="https://example.com/phm-2022-fixture",
        retrieval_status="full_text",
        metadata={
            "extracted_text": (
                "Introduction. Our framework is available at https://github.com/acme-lab/fixture . "
                "The benchmark dataset is C-MAPSS."
            ),
            "text_provider": "fixture",
            "repro_audit_eligible": True,
            "evidence_pointer": "data/interim/papers.jsonl#phm-2022-fixture",
        },
    )
    return _write_outputs(storage, [paper], ["model-a", "model-b", "model-c"])


def _validate_environment(*, require_openrouter: bool) -> str | None:
    if require_openrouter:
        return require_api_key("OPENROUTER_API_KEY")
    return os.environ.get("OPENROUTER_API_KEY")


def _download_ojs_artifacts(
    http_client: HttpClient,
    storage: StorageLayout,
    paper: PaperRecord,
    *,
    raw_source: str,
) -> PaperRecord:
    artifact_dir = storage.raw_year_dir(raw_source, paper.year) / paper.paper_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    downloaded_paths: list[str] = []
    for attachment in paper.attachments:
        try:
            payload = http_client.get_bytes(attachment.url)
        except FetchError as exc:
            paper.metadata.setdefault("download_errors", []).append(str(exc))
            continue
        suffix = ".pdf" if "pdf" in attachment.label.lower() or attachment.url.lower().endswith(".pdf") else ".bin"
        filename = normalized_pdf_name(paper.year, paper.authors, paper.title) if attachment.role == "paper" else f"{attachment.role}{suffix}"
        destination = artifact_dir / filename
        destination.write_bytes(payload)
        downloaded_paths.append(str(destination))
        if attachment.role == "paper" and "extracted_text" not in paper.metadata:
            extraction = extract_text_from_pdf(destination)
            paper.metadata["extracted_text"] = extraction.text
            paper.metadata["pdf_backend"] = extraction.backend
            paper.metadata["pdf_warnings"] = extraction.warnings
            paper.metadata["text_provider"] = extraction.backend
            paper.retrieval_status = "full_text" if extraction.text else "pdf_downloaded"
            paper.metadata["repro_audit_eligible"] = paper.retrieval_status == "full_text"
    paper.metadata["artifact_paths"] = downloaded_paths
    if not downloaded_paths and paper.retrieval_status == "discovered":
        paper.retrieval_status = "metadata_only"
        paper.metadata["repro_audit_eligible"] = False
    return paper


def _merge_article_details(paper: PaperRecord, details: ArticlePageDetails) -> PaperRecord:
    paper.doi = paper.doi or details.doi
    paper.published_at = details.published_at
    known_urls = {attachment.url for attachment in paper.attachments}
    for attachment in details.attachments:
        if attachment.url not in known_urls:
            paper.attachments.append(attachment)
    return paper


def _hydrate_ojs_paper_from_raw(
    paper: PaperRecord,
    paper_root: Path,
    *,
    evidence_pointer: str,
) -> PaperRecord:
    artifact_paths = []
    if paper_root.exists():
        artifact_paths = [
            str(path)
            for path in sorted(paper_root.iterdir())
            if path.is_file() and path.name != "article.html"
        ]
    paper.metadata["artifact_paths"] = artifact_paths
    paper.metadata["evidence_pointer"] = evidence_pointer

    normalized_paper_path = paper_root / normalized_pdf_name(paper.year, paper.authors, paper.title)
    pdf_candidates = sorted(path for path in paper_root.glob("*.pdf")) if paper_root.exists() else []
    paper_pdf_path = normalized_paper_path if normalized_paper_path.exists() else (pdf_candidates[0] if pdf_candidates else None)

    if paper_pdf_path is not None:
        extraction = extract_text_from_pdf(paper_pdf_path)
        paper.metadata["extracted_text"] = extraction.text
        paper.metadata["pdf_backend"] = extraction.backend
        paper.metadata["pdf_warnings"] = extraction.warnings
        paper.metadata["text_provider"] = extraction.backend
        paper.retrieval_status = "full_text" if extraction.text else "pdf_downloaded"
        paper.metadata["repro_audit_eligible"] = paper.retrieval_status == "full_text"
    else:
        paper.retrieval_status = "metadata_only"
        paper.metadata["text_provider"] = "missing"
        paper.metadata["repro_audit_eligible"] = False
    return paper


def collect_phm_2022(
    http_client: HttpClient,
    storage: StorageLayout,
    issue_url: str,
    *,
    year: int = 2022,
) -> list[PaperRecord]:
    issue_html = http_client.get_text(issue_url)
    issue_slug = issue_url.rstrip("/").split("/")[-1]
    issue_path = storage.raw_year_dir("phm", year) / f"issue_{issue_slug}.html"
    issue_path.parent.mkdir(parents=True, exist_ok=True)
    issue_path.write_text(issue_html, encoding="utf-8")
    papers = filter_main_papers(parse_issue_html(issue_html, issue_url=issue_url, year=year))
    collected: list[PaperRecord] = []
    for paper in papers:
        try:
            article_html = http_client.get_text(paper.article_url)
        except FetchError as exc:
            paper.metadata["article_fetch_error"] = str(exc)
            paper.metadata["repro_audit_eligible"] = False
            collected.append(paper)
            continue
        article_path = storage.raw_year_dir("phm", year) / paper.paper_id / "article.html"
        article_path.parent.mkdir(parents=True, exist_ok=True)
        article_path.write_text(article_html, encoding="utf-8")
        details = parse_article_html(article_html)
        _merge_article_details(paper, details)
        paper.metadata["evidence_pointer"] = f"data/interim/papers.jsonl#{paper.paper_id}"
        collected.append(_download_ojs_artifacts(http_client, storage, paper, raw_source="phm"))
    return collected


def collect_phm_years(
    http_client: HttpClient,
    storage: StorageLayout,
    issue_urls: dict[int, str],
    *,
    years: Iterable[int],
) -> list[PaperRecord]:
    collected: list[PaperRecord] = []
    for year in years:
        issue_url = issue_urls[year]
        collected.extend(collect_phm_2022(http_client, storage, issue_url, year=year))
    return collected


def load_phm_year_from_raw(storage: StorageLayout, issue_url: str, *, year: int) -> list[PaperRecord]:
    _progress(f"loading PHM raw corpus for {year}")
    year_root = storage.raw_year_dir("phm", year)
    issue_slug = issue_url.rstrip("/").split("/")[-1]
    issue_path = year_root / f"issue_{issue_slug}.html"
    issue_html = issue_path.read_text(encoding="utf-8")
    papers = filter_main_papers(parse_issue_html(issue_html, issue_url=issue_url, year=year))

    total = len(papers)
    for index, paper in enumerate(papers, start=1):
        paper_root = year_root / paper.paper_id
        article_path = paper_root / "article.html"
        if article_path.exists():
            details = parse_article_html(article_path.read_text(encoding="utf-8"))
            _merge_article_details(paper, details)
        _hydrate_ojs_paper_from_raw(
            paper,
            paper_root,
            evidence_pointer=f"data/processed/phm_society_conf/{year}/audit/papers.jsonl#{paper.paper_id}",
        )
        if index == 1 or index % 25 == 0 or index == total:
            _progress(f"hydrated PHM {year} paper {index}/{total}: {paper.paper_id}")

    return papers


def load_phm_years_from_raw(
    storage: StorageLayout,
    issue_urls: dict[int, str],
    *,
    years: Iterable[int],
) -> list[PaperRecord]:
    papers: list[PaperRecord] = []
    for year in years:
        papers.extend(load_phm_year_from_raw(storage, issue_urls[year], year=year))
    return papers


def collect_ijphm_years(
    http_client: HttpClient,
    storage: StorageLayout,
    archive_url: str,
    *,
    years: Iterable[int],
) -> list[PaperRecord]:
    year_set = set(years)
    archive_html = http_client.get_text(archive_url)
    archive_root = storage.raw_dir / "ijphm"
    archive_root.mkdir(parents=True, exist_ok=True)
    (archive_root / "archive.html").write_text(archive_html, encoding="utf-8")
    issues = parse_ijphm_archive_html(archive_html, archive_url=archive_url, years=year_set)

    collected: list[PaperRecord] = []
    for issue in issues:
        issue_html = http_client.get_text(issue.issue_url)
        issue_slug = issue.issue_url.rstrip("/").split("/")[-1]
        issue_path = storage.raw_year_dir("ijphm", issue.year) / f"issue_{issue_slug}.html"
        issue_path.parent.mkdir(parents=True, exist_ok=True)
        issue_path.write_text(issue_html, encoding="utf-8")
        papers = filter_main_papers(parse_ijphm_issue_html(issue_html, issue_url=issue.issue_url, year=issue.year))
        for paper in papers:
            try:
                article_html = http_client.get_text(paper.article_url)
            except FetchError as exc:
                paper.metadata["article_fetch_error"] = str(exc)
                paper.metadata["repro_audit_eligible"] = False
                collected.append(paper)
                continue
            article_path = storage.raw_year_dir("ijphm", issue.year) / paper.paper_id / "article.html"
            article_path.parent.mkdir(parents=True, exist_ok=True)
            article_path.write_text(article_html, encoding="utf-8")
            details = parse_ijphm_article_html(article_html)
            _merge_article_details(paper, details)
            paper.metadata["evidence_pointer"] = f"data/interim/papers.jsonl#{paper.paper_id}"
            collected.append(_download_ojs_artifacts(http_client, storage, paper, raw_source="ijphm"))
    return collected


def load_ijphm_years_from_raw(
    storage: StorageLayout,
    archive_url: str,
    *,
    years: Iterable[int],
) -> list[PaperRecord]:
    _progress("loading IJPHM raw corpus")
    archive_path = storage.raw_dir / "ijphm" / "archive.html"
    archive_html = archive_path.read_text(encoding="utf-8")
    issues = parse_ijphm_archive_html(archive_html, archive_url=archive_url, years=set(years))
    collected: list[PaperRecord] = []

    for issue in issues:
        _progress(f"processing IJPHM issue for {issue.year}: {issue.issue_url}")
        issue_slug = issue.issue_url.rstrip("/").split("/")[-1]
        issue_path = storage.raw_year_dir("ijphm", issue.year) / f"issue_{issue_slug}.html"
        issue_html = issue_path.read_text(encoding="utf-8")
        papers = filter_main_papers(parse_ijphm_issue_html(issue_html, issue_url=issue.issue_url, year=issue.year))
        total = len(papers)
        for index, paper in enumerate(papers, start=1):
            paper_root = storage.raw_year_dir("ijphm", issue.year) / paper.paper_id
            article_path = paper_root / "article.html"
            if article_path.exists():
                details = parse_ijphm_article_html(article_path.read_text(encoding="utf-8"))
                _merge_article_details(paper, details)
            _hydrate_ojs_paper_from_raw(
                paper,
                paper_root,
                evidence_pointer=f"data/processed/ijphm/{issue.year}/audit/papers.jsonl#{paper.paper_id}",
            )
            collected.append(paper)
            if index == 1 or index % 25 == 0 or index == total:
                _progress(f"hydrated IJPHM {issue.year} paper {index}/{total}: {paper.paper_id}")
    return collected


def run_live_bootstrap(
    config: AppConfig,
    sources: list[str],
    phm_issue_urls: dict[int, str],
    phm_years: list[int],
    ijphm_years: list[int],
    *,
    use_llm: bool = True,
) -> dict[str, Path]:
    openrouter_key = _validate_environment(require_openrouter=use_llm)
    storage = StorageLayout(Path(config.storage_root))
    storage.prepare()
    http_client = HttpClient(
        user_agent=config.pipeline.user_agent,
        timeout_seconds=config.pipeline.timeout_seconds,
        rate_limiter=RateLimiter(0.3),
    )
    judge_client = None
    if use_llm and openrouter_key:
        judge_client = OpenRouterClient(
            api_key=openrouter_key,
            base_url=config.openrouter.base_url,
            http_client=http_client,
        )

    papers: list[PaperRecord] = []
    if "phm" in sources:
        papers.extend(collect_phm_years(http_client, storage, phm_issue_urls, years=phm_years))
    if "ijphm" in sources:
        papers.extend(collect_ijphm_years(http_client, storage, config.ijphm.archive_url, years=ijphm_years))
    return _write_outputs(storage, papers, config.openrouter.models, judge_client=judge_client)


def run_raw_bootstrap(
    config: AppConfig,
    sources: list[str],
    phm_issue_urls: dict[int, str],
    phm_years: list[int],
    ijphm_years: list[int],
    *,
    use_llm: bool = True,
) -> dict[str, Path]:
    openrouter_key = _validate_environment(require_openrouter=use_llm)
    storage = StorageLayout(Path(config.storage_root))
    storage.prepare()
    judge_client = None
    if use_llm and openrouter_key:
        http_client = HttpClient(
            user_agent=config.pipeline.user_agent,
            timeout_seconds=config.pipeline.timeout_seconds,
            rate_limiter=RateLimiter(0.3),
        )
        judge_client = OpenRouterClient(
            api_key=openrouter_key,
            base_url=config.openrouter.base_url,
            http_client=http_client,
        )

    papers: list[PaperRecord] = []
    if "phm" in sources:
        _progress(f"starting raw rebuild for PHM years: {', '.join(map(str, phm_years))}")
        papers.extend(load_phm_years_from_raw(storage, phm_issue_urls, years=phm_years))
    if "ijphm" in sources:
        _progress(f"starting raw rebuild for IJPHM years: {', '.join(map(str, ijphm_years))}")
        papers.extend(load_ijphm_years_from_raw(storage, config.ijphm.archive_url, years=ijphm_years))
    _progress(f"loaded {len(papers)} papers from raw corpora; building outputs")
    return _write_outputs(storage, papers, config.openrouter.models, judge_client=judge_client)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap the PHM/IJPHM reproducibility audit.")
    parser.add_argument("--sources", default="phm,ijphm", help="Comma-separated sources to collect.")
    parser.add_argument("--phm-issue-url", default="", help="PHM issue URL override.")
    parser.add_argument(
        "--phm-years",
        default="2022,2023,2024,2025",
        help="Comma-separated PHM Society Conference publication years.",
    )
    parser.add_argument(
        "--ijphm-years",
        default="2022,2023,2024,2025",
        help="Comma-separated IJPHM publication years.",
    )
    parser.add_argument("--config", default="config/pilot_2022.yaml", help="Path to YAML config.")
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip OpenRouter judging and emit deterministic baseline outputs.",
    )
    parser.add_argument(
        "--fixture-run",
        action="store_true",
        help="Use built-in fixture data instead of live network access.",
    )
    parser.add_argument(
        "--from-raw",
        action="store_true",
        help="Rebuild outputs from existing local raw corpora instead of downloading papers again.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    sources = [part.strip() for part in args.sources.split(",") if part.strip()]
    unsupported = sorted(set(sources) - set(_YEARLY_AUDIT_COLLECTIONS))
    if unsupported:
        raise ValueError(f"Unsupported sources: {', '.join(unsupported)}")
    if args.fixture_run or os.environ.get("PHM_AUDIT_FIXTURE_RUN") == "1":
        bootstrap_fixture_run(Path("."))
        return
    phm_years = [int(value.strip()) for value in args.phm_years.split(",") if value.strip()]
    phm_issue_urls = {year: config.phm.issue_urls[year] for year in phm_years}
    if args.phm_issue_url:
        if len(phm_years) != 1:
            raise ValueError("--phm-issue-url can only be used when a single PHM year is requested.")
        phm_issue_urls[phm_years[0]] = args.phm_issue_url
    runner: Callable[..., dict[str, Path]] = run_raw_bootstrap if args.from_raw else run_live_bootstrap
    _progress(
        f"mode={'from-raw' if args.from_raw else 'live'} sources={','.join(sources)} "
        f"llm={'off' if args.skip_llm else 'on'}"
    )
    runner(
        config,
        sources,
        phm_issue_urls,
        phm_years,
        [int(value.strip()) for value in args.ijphm_years.split(",") if value.strip()],
        use_llm=not args.skip_llm,
    )


if __name__ == "__main__":
    main()
