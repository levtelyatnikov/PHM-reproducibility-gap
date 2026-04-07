from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.element import Tag

from parsers.phm_ojs import parse_article_html as parse_article_html
from parsers.phm_ojs import parse_issue_html as parse_ojs_issue_html
from shared.normalize import build_paper_id


_ISSUE_YEAR_PATTERN = re.compile(r"\((\d{4})\)")


@dataclass(slots=True)
class JournalIssueRef:
    year: int
    label: str
    issue_url: str


def parse_archive_html(html: str, *, archive_url: str, years: set[int]) -> list[JournalIssueRef]:
    soup = BeautifulSoup(html, "html.parser")
    issues: list[JournalIssueRef] = []
    seen_urls: set[str] = set()
    for link in soup.select("a[href]"):
        href = link.get("href", "")
        if "/issue/view/" not in href:
            continue
        label = " ".join(link.get_text(" ", strip=True).split())
        if _ISSUE_YEAR_PATTERN.search(label) is None:
            label = _archive_issue_context(link)
        year_match = _ISSUE_YEAR_PATTERN.search(label)
        if year_match is None:
            continue
        year = int(year_match.group(1))
        if year not in years:
            continue
        issue_url = urljoin(archive_url, href)
        if issue_url in seen_urls:
            continue
        seen_urls.add(issue_url)
        issues.append(JournalIssueRef(year=year, label=label, issue_url=issue_url))
    return issues


def _archive_issue_context(link: Tag) -> str:
    for parent in (link.parent, link.find_parent(class_="media-heading"), link.find_parent(class_="issue-summary")):
        if parent is None:
            continue
        text = " ".join(parent.get_text(" ", strip=True).split())
        if _ISSUE_YEAR_PATTERN.search(text):
            return text
    return " ".join(link.get_text(" ", strip=True).split())


def parse_issue_html(html: str, *, issue_url: str, year: int):
    papers = parse_ojs_issue_html(html, issue_url=issue_url, year=year)
    for paper in papers:
        paper.source = "ijphm"
        paper.paper_id = build_paper_id("ijphm", year, paper.title, article_id=paper.article_id, doi=paper.doi)
    return papers
