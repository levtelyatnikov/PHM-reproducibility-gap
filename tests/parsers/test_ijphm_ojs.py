from parsers.ijphm_ojs import parse_archive_html, parse_issue_html
from parsers.phm_ojs import filter_main_papers


ARCHIVE_HTML = """
<html>
  <body>
    <ul class="issues_archive">
      <li><a href="/index.php/ijphm/issue/view/75">Vol 16, No 4 (2025)</a></li>
      <li><a href="/index.php/ijphm/issue/view/71">Vol 15, No 2 (2024)</a></li>
      <li><a href="/index.php/ijphm/issue/view/69">Vol 14, No 2 (2023)</a></li>
      <li><a href="/index.php/ijphm/issue/view/67">Vol 13, No 1 (2022)</a></li>
      <li><a href="/index.php/ijphm/issue/view/55">Vol 12, No 4 (2021)</a></li>
    </ul>
  </body>
</html>
"""


ISSUE_HTML = """
<html>
  <body>
    <div class="section">
      <h2>Technical Papers</h2>
      <div class="obj_article_summary">
        <div class="title">
          <a href="https://papers.phmsociety.org/index.php/ijphm/article/view/3093">
            Ensemble Deep Learning for Detecting Onset of Abnormal Operation
          </a>
        </div>
        <div class="meta">
          <div class="authors">Jane Doe, John Roe</div>
          <a href="https://doi.org/10.36001/ijphm.2022.v13i1.3093">https://doi.org/10.36001/ijphm.2022.v13i1.3093</a>
        </div>
        <ul class="galleys_links">
          <li><a href="https://papers.phmsociety.org/index.php/ijphm/article/download/3093/1982">PDF</a></li>
        </ul>
      </div>
    </div>
    <div class="section">
      <h2>Technical Briefs</h2>
      <div class="obj_article_summary">
        <div class="title">
          <a href="https://papers.phmsociety.org/index.php/ijphm/article/view/3094">
            A Brief on Sensor Diagnostics
          </a>
        </div>
        <div class="meta">
          <div class="authors">Alex Smith</div>
        </div>
        <ul class="galleys_links">
          <li><a href="https://papers.phmsociety.org/index.php/ijphm/article/download/3094/1983">PDF</a></li>
        </ul>
      </div>
    </div>
  </body>
</html>
"""


def test_parse_archive_html_filters_to_requested_years() -> None:
    issues = parse_archive_html(
        ARCHIVE_HTML,
        archive_url="https://papers.phmsociety.org/index.php/ijphm/issue/archive",
        years={2022, 2024},
    )

    assert [issue.year for issue in issues] == [2024, 2022]
    assert issues[0].issue_url == "https://papers.phmsociety.org/index.php/ijphm/issue/view/71"
    assert issues[1].label == "Vol 13, No 1 (2022)"


def test_parse_ijphm_issue_html_sets_ijphm_source() -> None:
    papers = parse_issue_html(
        ISSUE_HTML,
        issue_url="https://papers.phmsociety.org/index.php/ijphm/issue/view/67",
        year=2022,
    )

    assert len(papers) == 2
    assert papers[0].source == "ijphm"
    assert papers[0].track == "Technical Papers"
    assert papers[0].paper_id == "ijphm-2022-3093"
    assert papers[0].pdf_url == "https://papers.phmsociety.org/index.php/ijphm/article/download/3093/1982"


def test_filter_main_papers_keeps_only_technical_papers_for_ijphm() -> None:
    papers = parse_issue_html(
        ISSUE_HTML,
        issue_url="https://papers.phmsociety.org/index.php/ijphm/issue/view/67",
        year=2022,
    )

    filtered = filter_main_papers(papers)

    assert len(filtered) == 1
    assert filtered[0].track == "Technical Papers"
