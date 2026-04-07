from shared.normalize import build_paper_id, guess_attachment_role, slugify


def test_slugify_normalizes_text() -> None:
    assert slugify("RUL Prediction: A Study!") == "rul-prediction-a-study"


def test_attachment_role_detection() -> None:
    assert guess_attachment_role("Slides (PDF)") == "slides"
    assert guess_attachment_role("PDF (Extended Abstract)") == "extended_abstract"
    assert guess_attachment_role("Presentation") == "presentation"
    assert guess_attachment_role("PDF") == "paper"


def test_build_paper_id_prefers_article_id() -> None:
    assert build_paper_id("phm", 2022, "Example", article_id="3144") == "phm-2022-3144"

