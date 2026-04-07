from engine.evidence import extract_evidence_windows
from engine.rules import (
    classify_channel,
    detect_named_public_benchmark_data,
    detect_public_external_dataset,
)


def test_code_a1_requires_owned_repository_link() -> None:
    text = """
    Our code is publicly available at https://github.com/acme-lab/rul-transformer .
    We release the training and evaluation pipeline in our repository.
    """

    assessment = classify_channel("code", text, extract_evidence_windows(text))

    assert assessment.label == "A1"
    assert assessment.rule_hits["ownership_link"]


def test_standard_tool_links_are_not_misclassified_as_a1() -> None:
    text = """
    The implementation uses PyTorch and is based on https://pytorch.org/get-started/locally/ .
    """

    assessment = classify_channel("code", text, extract_evidence_windows(text))

    assert assessment.label != "A1"
    assert assessment.rule_hits["standard_tool_link"]


def test_available_on_request_is_classified_as_restricted() -> None:
    text = "The dataset is available from the authors upon reasonable request."

    assessment = classify_channel("data", text, extract_evidence_windows(text))

    assert assessment.label == "A3"


def test_explicitly_unavailable_is_classified_as_a4() -> None:
    text = "The source code cannot be shared because of customer confidentiality constraints."

    assessment = classify_channel("code", text, extract_evidence_windows(text))

    assert assessment.label == "A4"


def test_code_channel_ignores_dataset_public_claims_and_nda_substrings() -> None:
    text = """
    This work describes a publicly available rock drill fault classification data set.
    The data is collected from a carefully instrumented hydraulic rock drill, operating in a test cell.
    The standard evaluation pipeline is described in the appendix.
    """

    assessment = classify_channel("code", text, extract_evidence_windows(text))

    assert assessment.label == "A5"


def test_data_channel_accepts_mixed_code_and_data_public_link() -> None:
    text = """
    Simulator, code and data available at https://github.com/xylhal/PHM-LLMFaultDiagnosis .
    """

    assessment = classify_channel("data", text, extract_evidence_windows(text))

    assert assessment.label == "A1"
    assert "github.com/xylhal/PHM-LLMFaultDiagnosis" in (assessment.note or "")


def test_data_channel_accepts_supplementary_material_data_release() -> None:
    text = """
    The complete numerical implementation and corresponding experimental data are available as supplementary material at https://portal.ijs.si/nextcloud/s/xTa2cmtfxXn2jSz .
    """

    assessment = classify_channel("data", text, extract_evidence_windows(text))

    assert assessment.label == "A1"
    assert "supplementary material at" in (assessment.note or "")
    assert "https://portal.ijs.si/nextcloud/s/xTa2cmtfxXn2jSz" in assessment.supporting_urls


def test_detect_named_public_benchmark_data_flags_common_dataset_mentions() -> None:
    text = """
    We evaluate the approach on the C-MAPSS dataset and compare the results to prior work.
    """

    flagged, name, note = detect_named_public_benchmark_data(text)

    assert flagged is True
    assert name == "C-MAPSS"
    assert "C-MAPSS dataset" in (note or "")


def test_code_channel_accepts_www_github_links_as_a1() -> None:
    text = """
    The code to reproduce the results of this paper is available on GitHub: www.github.com/tilman151/self-supervised-ssl .
    """

    assessment = classify_channel("code", text, extract_evidence_windows(text))

    assert assessment.label == "A1"
    assert "github.com/tilman151/self-supervised-ssl" in "".join(assessment.supporting_urls)


def test_code_channel_accepts_drive_repository_links_as_a1() -> None:
    text = """
    Link for the repository containing the Simulink model for the case study:
    https://drive.google.com/drive/folders/1MDzJ8g7lI92xbhBn_UW-xXoilcMRTaYu?usp=sharing
    """

    assessment = classify_channel("code", text, extract_evidence_windows(text))

    assert assessment.label == "A1"
    assert "drive.google.com" in "".join(assessment.supporting_urls)


def test_code_channel_ignores_public_dataset_framework_mentions() -> None:
    text = """
    Su and Lee provide detailed insights into leveraging publicly available PHM datasets for diagnostic modeling,
    while Lee and Su present a unified conceptual framework for industrial AI in maintenance systems.
    """

    assessment = classify_channel("code", text, extract_evidence_windows(text))

    assert assessment.label == "A5"


def test_data_channel_ignores_generic_data_exchange_upon_request_language() -> None:
    text = """
    Type 2 reactive shells incorporate APIs that enable real-time data exchange between assets and external systems upon request.
    """

    assessment = classify_channel("data", text, extract_evidence_windows(text))

    assert assessment.label == "A5"


def test_detect_public_external_dataset_flags_public_benchmark_usage() -> None:
    text = """
    The proposed method is evaluated on the publicly available IMS bearing dataset from the NASA Ames Prognostics Data Repository.
    """

    flagged, kind, note = detect_public_external_dataset(text)

    assert flagged is True
    assert kind == "named_benchmark"
    assert "IMS" in (note or "")


def test_code_channel_ignores_reference_section_github_links() -> None:
    text = """
    The proposed classifier performs well on the target task.
    6. REFERENCES
    Makerere AI Lab. Bean disease dataset. https://github.com/AI-Lab-Makerere/ibean/
    """

    assessment = classify_channel("code", text, extract_evidence_windows(text))

    assert assessment.label == "A5"


def test_data_channel_detects_not_publicly_available_even_with_such_data_wording() -> None:
    text = """
    However, such data and the design of the experiment are not publicly available.
    """

    assessment = classify_channel("data", text, extract_evidence_windows(text))

    assert assessment.label == "A4"


def test_data_channel_accepts_owned_open_access_claim_without_link_as_a2() -> None:
    text = """
    We are continuously updating our data collection with new information and data,
    and we welcome contributors who wish to share new data with us for open access.
    """

    assessment = classify_channel("data", text, extract_evidence_windows(text))

    assert assessment.label == "A2"
