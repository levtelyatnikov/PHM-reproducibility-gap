from __future__ import annotations

import re
from collections.abc import Iterable

from engine.evidence import extract_evidence_windows
from shared.schemas import EvidenceWindow, RuleAssessment


STANDARD_TOOL_DOMAINS = {
    "pytorch.org",
    "tensorflow.org",
    "scikit-learn.org",
    "sklearn.org",
}
STANDARD_BENCHMARK_HINTS = {
    "cmapss",
    "c-mapss",
    "cwru",
    "mnist",
}
PUBLIC_BENCHMARK_PATTERNS = (
    ("C-MAPSS", (r"\bc-?mapss\b",)),
    ("N-CMAPSS", (r"\bn-?cmapss\b",)),
    ("CWRU", (r"\bcwru\b", r"\bcase western reserve\b")),
    ("IMS", (r"\bims dataset\b", r"\bims bearing\b")),
    ("CALCE", (r"\bcalce\b",)),
    ("PRONOSTIA", (r"\bpronostia\b", r"\bfemto-?st\b")),
    ("Paderborn", (r"\bpaderborn\b",)),
    ("XJTU-SY", (r"\bxjtu-?sy\b",)),
    ("SEU", (r"\bsoutheast university\b", r"\bseu bearing\b")),
    ("3W", (r"\b3w database\b",)),
    ("MIMII", (r"\bmimii\b",)),
)
CODE_ARTIFACT_HINTS = {
    "code",
    "source code",
    "package",
    "tool",
    "library",
    "software",
    "implementation",
    "repository",
    "repo",
}
DATA_ARTIFACT_HINTS = {
    "dataset",
    "data set",
    "corpus",
    "benchmark",
    "ontology",
    "rdf",
    "labels",
}
DATA_OWNERSHIP_HINTS = {
    "this work describes the collection",
    "collection and properties of a publicly available",
    "dataset described in this work",
    "our dataset",
    "our data set",
    "novel dataset",
    "novel data set",
    "new dataset",
    "new data set",
    "the data is collected from",
    "these data will be made available",
    "we provide the dataset",
    "we provide the data",
    "we release the dataset",
    "we release the data",
}
OWNERSHIP_HINTS = {
    "a pre-release version of the framework is available at",
    "code to reproduce the results of this paper",
    "code to reproduce the results is available on github",
    "code is available on github",
    "code is available on gitlab",
    "link for the repository containing",
    "repository containing the simulink model",
    "our code",
    "our dataset",
    "our repository",
    "our repo",
    "we release",
    "we provide",
    "publicly available at",
    "supplementary material at",
    "framework is available at",
    "package is available at",
    "tool is available at",
    "implementation is available at",
    "pre-release version of the framework is available at",
}
PUBLIC_CLAIM_HINTS = {
    "publicly available",
    "open source",
    "openly available",
    "released at",
    "available online",
    "supplementary material at",
    "dataset is available at",
    "data is available at",
    "data set is available at",
}
RESTRICTED_HINTS = {
    "available on request",
    "available upon request",
    "upon request",
    "reasonable request",
    "upon requests from the authors",
}
UNAVAILABLE_HINTS = {
    "not publicly available",
    "cannot be shared",
    "will not be shared",
    "unable to share",
    "confidentially labeled data set",
    "confidential dataset",
}
SHARING_CONTEXT_HINTS = {
    "share",
    "shared",
    "available",
    "public",
    "release",
    "request",
    "authors",
}
SECTION_STOP_PATTERNS = [
    re.compile(r"(?:^|\s)\d*\.?\s*REFERENCES\b", re.IGNORECASE),
    re.compile(r"(?:^|\s)\d*\.?\s*ACKNOWLEDGMENTS?\b", re.IGNORECASE),
    re.compile(r"(?:^|\s)\d*\.?\s*BIOGRAPH(?:Y|IES)\b", re.IGNORECASE),
]


def _contains_any(text: str, phrases: Iterable[str]) -> bool:
    lowered = text.lower()
    for phrase in phrases:
        escaped = re.escape(phrase.lower())
        if re.search(rf"(?<!\w){escaped}(?!\w)", lowered):
            return True
    return False


def _channel_keywords(channel: str) -> tuple[str, ...]:
    if channel == "code":
        return tuple(CODE_ARTIFACT_HINTS | {"github", "gitlab"})
    return tuple(DATA_ARTIFACT_HINTS | {"data"})


def _strip_non_signal_sections(text: str) -> str:
    cutoff = len(text)
    for pattern in SECTION_STOP_PATTERNS:
        match = pattern.search(text)
        if match:
            cutoff = min(cutoff, match.start())
    return text[:cutoff]


def _normalize_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"-\n(?=[a-z])", "", text)
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _split_sentences(text: str) -> list[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return []
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", normalized) if sentence.strip()]


def _looks_like_reference_citation(sentence: str) -> bool:
    normalized = _normalize_text(sentence)
    lowered = normalized.lower()
    has_url = bool(re.search(r"(?:https?://|www\.)", normalized)) or "url http" in lowered
    if not has_url:
        return False

    release_markers = (
        "available at",
        "available on",
        "our code",
        "our repository",
        "our repo",
        "we release",
        "we provide",
        "code is available",
        "framework is available",
        "implementation is available",
        "package is available",
        "tool is available",
        "supplementary material",
    )
    if any(marker in lowered for marker in release_markers):
        return False

    author_hits = len(re.findall(r"\b[A-Z][a-zA-Z-]+,\s*[A-Z]\.", normalized))
    year_hit = bool(re.search(r"\(\d{4}\)", normalized))
    citation_markers = author_hits >= 2 or normalized.count(";") >= 2 or "doi" in lowered or "vol." in lowered or "pp." in lowered
    return has_url and year_hit and citation_markers


def _candidate_sentences(channel: str, text: str) -> list[str]:
    sentences = _split_sentences(_strip_non_signal_sections(text))
    candidates: list[str] = []
    for sentence in sentences:
        if _looks_like_reference_citation(sentence):
            continue
        if _sentence_matches_channel(channel, sentence):
            candidates.append(sentence)
    return candidates


def _sentence_evidence_score(channel: str, sentence: str, label: str) -> int:
    lowered = sentence.lower()
    score = 0

    if _sentence_matches_channel(channel, sentence):
        score += 4
    if _sentence_urls(sentence):
        score += 2

    if label == "A1":
        if _artifact_owned(sentence, channel):
            score += 10
        if "available at" in lowered:
            score += 4
    elif label == "A2":
        if _contains_any(lowered, PUBLIC_CLAIM_HINTS):
            score += 8
        if "only currently available public data set" in lowered or "only currently available public dataset" in lowered:
            score += 8
        if "public data set" in lowered or "public dataset" in lowered:
            score += 5
        if "publicly available" in lowered or "openly available" in lowered or "open source" in lowered:
            score += 4
        if "available at" in lowered:
            score += 2
    elif label == "A3":
        if _contains_any(lowered, RESTRICTED_HINTS):
            score += 10
        if "authors" in lowered:
            score += 2
    elif label == "A4":
        if _contains_any(lowered, UNAVAILABLE_HINTS):
            score += 10
        if "publicly" in lowered:
            score += 2

    if "abstract" in lowered:
        score -= 8
    if sentence.count("@") >= 1:
        score -= 6
    if len(sentence) > 320:
        score -= 4

    return score


def _best_sentence(
    channel: str,
    sentences: list[str],
    *,
    label: str,
) -> str | None:
    if label == "A2":
        candidates = [
            sentence
            for sentence in sentences
            if _contains_any(sentence.lower(), PUBLIC_CLAIM_HINTS)
            or (_availability_context(sentence) and ("public" in sentence.lower() or "open" in sentence.lower()))
        ]
    elif label == "A3":
        candidates = [sentence for sentence in sentences if _contains_any(sentence.lower(), RESTRICTED_HINTS)]
    elif label == "A4":
        candidates = [sentence for sentence in sentences if _contains_any(sentence.lower(), UNAVAILABLE_HINTS)]
    else:
        candidates = [sentence for sentence in sentences if _sentence_matches_channel(channel, sentence)]

    if not candidates:
        return None

    return _clean_note(
        max(
            candidates,
            key=lambda sentence: (
                _sentence_evidence_score(channel, sentence, label),
                -len(sentence),
            ),
        )
    )


def _sentence_urls(sentence: str) -> list[str]:
    urls: list[str] = []
    for match in re.findall(r"(?:https?://|www\.)[^\s)\]>]+", sentence):
        cleaned = match.rstrip(".,;")
        if cleaned.startswith("www."):
            cleaned = f"https://{cleaned}"
        urls.append(cleaned)
    return urls


def _claim_text_for_window(window: EvidenceWindow) -> str:
    normalized = _normalize_text(window.context)
    if not normalized:
        return normalized
    if window.url:
        return normalized

    lowered = normalized.lower()
    phrase_anchors = (
        "pre-release version of the framework is available at",
        "framework is available at",
        "implementation is available at",
        "package is available at",
        "tool is available at",
        "publicly available at",
        "supplementary material at",
        "dataset is available at",
        "data is available at",
        "data available at",
    )
    anchors = [anchor for anchor in phrase_anchors if anchor in lowered]
    anchors.extend(marker for marker in (window.url, window.domain, "available at", "github", "gitlab") if marker)
    index = -1
    for anchor in anchors:
        haystack = lowered if anchor in phrase_anchors else lowered
        needle = anchor.lower()
        index = haystack.find(needle)
        if index != -1:
            break
    if index == -1:
        return normalized

    start_candidates = [normalized.rfind(marker, 0, index) for marker in ".!?"]
    start = max(start_candidates)
    start = 0 if start == -1 else start + 1

    end_candidates = [normalized.find(marker, index) for marker in ".!?"]
    end_candidates = [candidate for candidate in end_candidates if candidate != -1]
    end = min(end_candidates) + 1 if end_candidates else len(normalized)

    snippet = normalized[start:end].strip()
    return snippet or normalized


def _clean_note(sentence: str | None) -> str | None:
    if sentence is None:
        return None
    cleaned = _normalize_text(sentence)
    cleaned = re.sub(r"^\d+(?=[A-Z])", "", cleaned)
    return cleaned or None


def _ownership_note(sentence: str, url: str | None) -> str | None:
    cleaned = _clean_note(sentence)
    if cleaned is None:
        return None
    lowered = cleaned.lower()
    starts = [lowered.find(phrase) for phrase in OWNERSHIP_HINTS if lowered.find(phrase) != -1]
    if starts:
        cleaned = cleaned[min(starts):]
    if url:
        url_index = cleaned.find(url)
        if url_index != -1:
            cleaned = cleaned[: url_index + len(url)]
        else:
            available_at_index = cleaned.lower().find("available at")
            if available_at_index != -1:
                cleaned = f"{cleaned[: available_at_index + len('available at')].strip()} {url}"
    return cleaned


def _availability_context(sentence: str) -> bool:
    lowered = sentence.lower()
    return (
        "available" in lowered
        or "open access" in lowered
        or any(token in lowered for token in ("github", "gitlab", "drive.google", "link for the repository", "link to the repository"))
        or _contains_any(lowered, PUBLIC_CLAIM_HINTS | RESTRICTED_HINTS | UNAVAILABLE_HINTS)
    )


def _sentence_matches_channel(channel: str, sentence: str) -> bool:
    lowered = sentence.lower()
    if channel == "code":
        strong_code_hint = any(
            hint in lowered
            for hint in ("code", "source code", "implementation", "software", "package", "library", "tool")
        )
        repo_hint = "repository" in lowered or "repo" in lowered
        framework_hint = "framework" in lowered
        platform_hint = any(token in lowered for token in ("github", "gitlab", "drive.google"))

        if strong_code_hint:
            return True
        if repo_hint:
            return platform_hint or any(token in lowered for token in ("code", "model", "simulink", "software", "implementation"))
        if framework_hint:
            return any(
                token in lowered
                for token in ("source code", "available at", "available on", "github", "gitlab", "repository", "implementation")
            )
        if platform_hint:
            return True
        if not any(hint in lowered for hint in CODE_ARTIFACT_HINTS):
            return False
        has_data_hint = any(hint in lowered for hint in DATA_ARTIFACT_HINTS) or "data available at" in lowered
        if has_data_hint and not strong_code_hint:
            return False
        return True
    if any(hint in lowered for hint in DATA_ARTIFACT_HINTS):
        return True
    if _availability_context(sentence) and re.search(r"\bdata\b", lowered):
        explicit_data_context = any(
            phrase in lowered
            for phrase in (
                "data available",
                "data is available",
                "data are available",
                "made available",
                "data set available",
                "dataset available",
                "experimental data",
                "public data",
                "public dataset",
                "publicly available dataset",
                "not publicly available",
                "open data",
                "open access",
                "share the data",
                "release the data",
                "data cannot be shared",
                "data not publicly available",
                "data are not publicly available",
            )
        )
        if any(code_hint in lowered for code_hint in CODE_ARTIFACT_HINTS):
            return any(
                phrase in lowered
                for phrase in (
                    "code and data",
                    "implementation and data",
                    "software and data",
                    "experimental data",
                )
            )
        return explicit_data_context
    return False


def _artifact_owned(sentence: str, channel: str) -> bool:
    lowered = sentence.lower()
    if _contains_any(lowered, OWNERSHIP_HINTS):
        return True
    if "we welcome" in lowered and "contribut" in lowered:
        return True
    artifact_terms = _channel_keywords(channel)
    if "available at" in lowered and any(term in lowered for term in artifact_terms):
        return True
    if "supplementary material at" in lowered and any(term in lowered for term in artifact_terms):
        return True
    return False


def _paper_claims_owned_data(text: str) -> bool:
    lowered = _normalize_text(_strip_non_signal_sections(text)).lower()
    if any(hint in lowered for hint in DATA_OWNERSHIP_HINTS):
        return True
    if "this data set" in lowered and ("collection" in lowered or "collected" in lowered):
        return True
    return False


def _owned_public_data_sentence(sentence: str) -> bool:
    lowered = sentence.lower()
    ownership_markers = (
        "our data collection",
        "this data set",
        "this dataset",
        "our dataset",
        "our data set",
        "these data",
        "dataset we collected",
        "data we collected",
        "we collected",
        "we provide",
        "we release",
        "we welcome contributors",
        "dataset described in this work",
        "this is the only currently available public data set",
        "this is the only currently available public dataset",
    )
    return any(marker in lowered for marker in ownership_markers)


def _external_public_data_sentence(sentence: str) -> bool:
    lowered = sentence.lower()
    if _contains_any(lowered, STANDARD_BENCHMARK_HINTS):
        return True
    external_markers = (
        "dataset provided by",
        "provided by",
        "developed by",
        "ims dataset",
        "calce dataset",
        "3w database",
    )
    return any(marker in lowered for marker in external_markers)


def _is_standard_resource(channel: str, sentence: str, url: str | None) -> bool:
    lowered = sentence.lower()
    domain = None
    if url:
        from shared.normalize import domain_from_url

        domain = domain_from_url(url)
    if domain in STANDARD_TOOL_DOMAINS:
        return True
    if channel == "data":
        if _contains_any(lowered, STANDARD_BENCHMARK_HINTS):
            return True
        if domain and any(token in domain for token in ("nasa", "kaggle", "ti.arc.nasa.gov", "cwru")):
            if "our dataset" not in lowered and "this dataset" not in lowered:
                return True
    return False


def detect_named_public_benchmark_data(text: str) -> tuple[bool, str | None, str | None]:
    signal_text = _strip_non_signal_sections(text)
    sentences = _candidate_sentences("data", signal_text) or _split_sentences(_normalize_text(signal_text))
    best_name: str | None = None
    best_sentence: str | None = None
    best_score = -1

    for sentence in sentences:
        lowered = sentence.lower()
        matched_name = None
        for name, patterns in PUBLIC_BENCHMARK_PATTERNS:
            if any(re.search(pattern, lowered) for pattern in patterns):
                matched_name = name
                break
        if matched_name is None:
            continue

        score = 0
        if "dataset" in lowered or "data set" in lowered or "benchmark" in lowered:
            score += 4
        if "public" in lowered or "publicly" in lowered:
            score += 2
        if "used" in lowered or "evaluate" in lowered or "experiment" in lowered:
            score += 1
        if "available" in lowered:
            score += 1
        if len(sentence) < 280:
            score += 1

        if score > best_score:
            best_score = score
            best_name = matched_name
            best_sentence = sentence

    return (best_name is not None, best_name, _clean_note(best_sentence))


def detect_public_external_dataset(text: str) -> tuple[bool, str | None, str | None]:
    benchmark_flag, benchmark_name, benchmark_note = detect_named_public_benchmark_data(text)
    if benchmark_flag:
        return True, "named_benchmark", benchmark_note

    signal_text = _strip_non_signal_sections(text)
    sentences = _split_sentences(_normalize_text(signal_text))
    patterns = (
        (r"\bpublicly available\b.*\bdataset\b", "public_dataset_claim"),
        (r"\bpublic datasets?\b", "public_dataset_claim"),
        (r"\bopen access\b", "open_access_claim"),
        (r"\bopen[- ]source benchmark\b", "public_dataset_claim"),
        (r"\bprognostics data repository\b", "public_repository_reference"),
    )
    for sentence in sentences:
        lowered = sentence.lower()
        for pattern, kind in patterns:
            if re.search(pattern, lowered):
                return True, kind, _clean_note(sentence)
    return False, None, None


def _relevant_text(channel: str, text: str, windows: list[EvidenceWindow]) -> str:
    keywords = _channel_keywords(channel)
    fragments: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in keywords):
            fragments.append(sentence)
    for window in windows:
        lowered = window.context.lower()
        if any(keyword in lowered for keyword in keywords):
            fragments.append(window.context)
    return "\n".join(fragments)


def _relevant_windows(channel: str, windows: list[EvidenceWindow]) -> list[EvidenceWindow]:
    if channel == "code":
        hints = ("code", "repository", "repo", "github", "gitlab", "implementation")
    else:
        hints = ("data", "dataset", "database", "benchmark", "corpus")
    matching = [window for window in windows if any(hint in window.context.lower() for hint in hints)]
    return matching or windows


def classify_channel(channel: str, text: str, evidence_windows: list[EvidenceWindow]) -> RuleAssessment:
    signal_text = _strip_non_signal_sections(text)
    windows = _relevant_windows(channel, extract_evidence_windows(_normalize_text(signal_text)))
    relevant_text = _relevant_text(channel, signal_text, windows)
    lowered = relevant_text.lower()
    sentences = _candidate_sentences(channel, signal_text)
    rule_hits = {
        "ownership_link": False,
        "standard_tool_link": False,
        "standard_benchmark_link": False,
        "available_on_request": False,
        "explicitly_unavailable": False,
        "ambiguous_public_claim": False,
        "public_link_no_ownership": False,
    }
    reasons: list[str] = []
    snippets: list[str] = []
    urls: list[str] = []

    restricted_sentence = _best_sentence(channel, sentences, label="A3")
    if restricted_sentence:
        rule_hits["available_on_request"] = True
        return RuleAssessment(
            channel=channel,
            label="A3",
            confidence=0.92,
            reasons=["available_on_request"],
            rule_hits=rule_hits,
            evidence_snippets=[restricted_sentence[:240]],
            supporting_urls=_sentence_urls(restricted_sentence),
            note=restricted_sentence,
        )

    unavailable_sentence = _best_sentence(channel, sentences, label="A4")
    if unavailable_sentence:
        rule_hits["explicitly_unavailable"] = True
        return RuleAssessment(
            channel=channel,
            label="A4",
            confidence=0.95,
            reasons=["explicitly_unavailable"],
            rule_hits=rule_hits,
            evidence_snippets=[unavailable_sentence[:240]],
            supporting_urls=_sentence_urls(unavailable_sentence),
            note=unavailable_sentence,
        )

    for window in windows:
        claim_text = _claim_text_for_window(window)
        if _looks_like_reference_citation(claim_text):
            continue
        context = claim_text.lower()
        if window.url:
            urls.append(window.url)
        if window.domain in STANDARD_TOOL_DOMAINS:
            rule_hits["standard_tool_link"] = True
            reasons.append("standard_tool_link")
            snippets.append(claim_text[:240])
            continue
        if not _availability_context(claim_text):
            continue
        if _is_standard_resource(channel, claim_text, window.url):
            if window.domain in STANDARD_TOOL_DOMAINS:
                rule_hits["standard_tool_link"] = True
                reasons.append("standard_tool_link")
            else:
                rule_hits["standard_benchmark_link"] = True
                reasons.append("standard_benchmark_link")
            snippets.append(claim_text[:240])
            continue
        if window.domain in STANDARD_TOOL_DOMAINS:
            rule_hits["standard_tool_link"] = True
            reasons.append("standard_tool_link")
            snippets.append(claim_text[:240])
            continue
        owns_artifact = _contains_any(context, OWNERSHIP_HINTS)
        if (
            window.url
            and _sentence_matches_channel(channel, claim_text)
            and (_artifact_owned(claim_text, channel) or owns_artifact)
        ):
            rule_hits["ownership_link"] = True
            note = _ownership_note(claim_text, window.url) or _best_sentence(channel, sentences, label="A1")
            return RuleAssessment(
                channel=channel,
                label="A1",
                confidence=0.92,
                reasons=["ownership_link"],
                rule_hits=rule_hits,
                evidence_snippets=[(note or claim_text)[:240]],
                supporting_urls=[window.url],
                note=note,
            )
        if window.url and not owns_artifact and _sentence_matches_channel(channel, claim_text):
            rule_hits["public_link_no_ownership"] = True
            snippets.append(claim_text[:240])

    public_sentence = _best_sentence(channel, sentences, label="A2")
    if public_sentence:
        sentence_urls = _sentence_urls(public_sentence)
        url = sentence_urls[0] if sentence_urls else None
        if channel == "data" and (
            not _owned_public_data_sentence(public_sentence) or _external_public_data_sentence(public_sentence)
        ):
            public_sentence = None
        elif not url or not _is_standard_resource(channel, public_sentence, url):
            rule_hits["ambiguous_public_claim"] = True
            return RuleAssessment(
                channel=channel,
                label="A2",
                confidence=0.68,
                reasons=["ambiguous_public_claim"],
                rule_hits=rule_hits,
                evidence_snippets=[public_sentence[:240]],
                supporting_urls=sentence_urls,
                note=public_sentence,
            )

    if rule_hits["public_link_no_ownership"]:
        if channel == "data" and not _paper_claims_owned_data(signal_text):
            return RuleAssessment(
                channel=channel,
                label="A5",
                confidence=0.75,
                reasons=reasons or ["not_mentioned"],
                rule_hits=rule_hits,
                evidence_snippets=snippets[:3],
                supporting_urls=urls[:3],
                note=None,
            )
        rule_hits["ambiguous_public_claim"] = True
        return RuleAssessment(
            channel=channel,
            label="A2",
            confidence=0.65,
            reasons=["ambiguous_public_claim"],
            rule_hits=rule_hits,
            evidence_snippets=snippets[:3] or [text.strip()[:240]],
            supporting_urls=urls[:3],
            note=_normalize_text(snippets[0]) if snippets else None,
        )

    return RuleAssessment(
        channel=channel,
        label="A5",
        confidence=0.75,
        reasons=reasons or ["not_mentioned"],
        rule_hits=rule_hits,
        evidence_snippets=snippets[:3],
        supporting_urls=urls[:3],
        note=None,
    )
