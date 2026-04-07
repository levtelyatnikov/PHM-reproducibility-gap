from parsers.phm_ojs import filter_main_papers, parse_article_html, parse_issue_html


ISSUE_HTML = """
<html>
  <body>
    <div class="section">
      <h2>Technical Research Papers</h2>
      <div class="obj_article_summary">
        <div class="title">
          <a href="https://papers.phmsociety.org/index.php/phmconf/article/view/3144">
            A Dataset for Fault Classification in Rock Drills
          </a>
        </div>
        <div class="meta">
          <div class="authors">Jane Doe, John Roe</div>
          <a href="https://doi.org/10.36001/phmconf.2022.v14i1.3144">https://doi.org/10.36001/phmconf.2022.v14i1.3144</a>
        </div>
        <ul class="galleys_links">
          <li><a href="https://papers.phmsociety.org/index.php/phmconf/article/download/3144/phmc_22_3144">PDF</a></li>
          <li><a href="https://papers.phmsociety.org/index.php/phmconf/article/download/3144/slides_3144">Slides (PDF)</a></li>
        </ul>
      </div>
    </div>
    <div class="section">
      <h2>Poster Presentations</h2>
      <div class="obj_article_summary">
        <div class="title">
          <a href="https://papers.phmsociety.org/index.php/phmconf/article/view/3199">
            Poster on Bearings
          </a>
        </div>
        <div class="meta">
          <div class="authors">Alex Smith</div>
        </div>
        <ul class="galleys_links">
          <li><a href="https://papers.phmsociety.org/index.php/phmconf/article/download/3199/poster_3199">PDF (Extended Abstract)</a></li>
        </ul>
      </div>
    </div>
  </body>
</html>
"""

ARTICLE_HTML = """
<html>
  <body>
    <section class="item doi">
      <a href="https://doi.org/10.36001/phmconf.2022.v14i1.3144">10.36001/phmconf.2022.v14i1.3144</a>
    </section>
    <section class="item published">
      <div class="value">2022-11-15</div>
    </section>
    <ul class="galleys_links">
      <li><a href="https://papers.phmsociety.org/index.php/phmconf/article/download/3144/phmc_22_3144">PDF</a></li>
      <li><a href="https://papers.phmsociety.org/index.php/phmconf/article/download/3144/slides_3144">Slides (PDF)</a></li>
      <li><a href="https://papers.phmsociety.org/index.php/phmconf/article/download/3144/presentation_3144">Presentation</a></li>
    </ul>
  </body>
</html>
"""


def test_parse_issue_html_extracts_tracks_and_attachments() -> None:
    papers = parse_issue_html(
        ISSUE_HTML,
        issue_url="https://papers.phmsociety.org/index.php/phmconf/issue/view/59",
        year=2022,
    )

    assert len(papers) == 2
    assert papers[0].track == "Technical Research Papers"
    assert papers[0].source == "phm"
    assert papers[0].article_id == "3144"
    assert papers[0].attachments[0].label == "PDF"
    assert papers[0].attachments[1].role == "slides"

    assert papers[1].track == "Poster Presentations"
    assert papers[1].attachments[0].role == "extended_abstract"


def test_parse_article_html_extracts_metadata_and_attachment_roles() -> None:
    details = parse_article_html(ARTICLE_HTML)

    assert details.doi == "10.36001/phmconf.2022.v14i1.3144"
    assert details.published_at == "2022-11-15"
    assert [attachment.role for attachment in details.attachments] == [
        "paper",
        "slides",
        "presentation",
    ]


def test_filter_main_papers_keeps_only_research_paper_tracks() -> None:
    papers = parse_issue_html(
        ISSUE_HTML,
        issue_url="https://papers.phmsociety.org/index.php/phmconf/issue/view/59",
        year=2022,
    )

    filtered = filter_main_papers(papers)

    assert len(filtered) == 1
    assert filtered[0].track == "Technical Research Papers"
