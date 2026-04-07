from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.element import Tag

from shared.normalize import build_paper_id, guess_attachment_role
from shared.schemas import ArticlePageDetails, AttachmentRecord, PaperRecord


_ARTICLE_ID_PATTERN = re.compile(r"/article/view/(\d+)")
_EXCLUDED_TRACK_HINTS = (
    "poster",
    "doctoral symposium",
    "data challenge",
    "challenge",
    "keynote",
    "panel",
    "tutorial",
    "workshop",
)


def _article_id_from_url(url: str) -> str | None:
    match = _ARTICLE_ID_PATTERN.search(url)
    return match.group(1) if match else None


def _split_authors(raw_authors: str) -> list[str]:
    return [part.strip() for part in raw_authors.split(",") if part.strip()]


def _extract_attachments(container: Tag | BeautifulSoup, base_url: str) -> list[AttachmentRecord]:
    attachments: list[AttachmentRecord] = []
    selectors = [".galleys_links a", ".galleryLinksWrp a", "a.galley-link"]
    seen_urls: set[str] = set()
    for selector in selectors:
        links = container.select(selector)
        if not links:
            continue
        for link in links:
            label = " ".join(link.get_text(" ", strip=True).split())
            href = link.get("href")
            if not href:
                continue
            resolved = urljoin(base_url, href)
            if resolved in seen_urls:
                continue
            seen_urls.add(resolved)
            attachments.append(
                AttachmentRecord(
                    label=label,
                    url=resolved,
                    role=guess_attachment_role(label),
                )
            )
    return attachments


def _section_nodes(soup: BeautifulSoup) -> list[Tag]:
    nodes = soup.select(".issueTocPublishArticles > .section")
    if nodes:
        return [node for node in nodes if isinstance(node, Tag)]
    return [node for node in soup.select(".section") if isinstance(node, Tag)]


def _article_nodes(section: Tag) -> list[Tag]:
    nodes = section.select(".article-summary")
    if nodes:
        return [node for node in nodes if isinstance(node, Tag)]
    return [node for node in section.select(".obj_article_summary") if isinstance(node, Tag)]


def _extract_track(section: Tag) -> str:
    heading = section.select_one(".current_issue_title, h1, h2, h3")
    return heading.get_text(" ", strip=True) if heading else "Unknown"


def _extract_title_link(article: Tag) -> Tag | None:
    return article.select_one(".media-heading a, .title a, h3 a, h4 a")


def _extract_authors(article: Tag) -> list[str]:
    authors_node = article.select_one(".authors")
    if authors_node is None:
        return []
    authors_text = " ".join(authors_node.stripped_strings)
    authors_text = authors_text.replace("glyphicon user", "").replace("glyphicon-user", "")
    authors_text = authors_text.replace("user", "").strip(" ,")
    return _split_authors(authors_text)


def _extract_doi(article: Tag) -> str | None:
    for link in article.select("a[href]"):
        href = link.get("href", "")
        if "doi.org/" in href:
            return href.rsplit("doi.org/", 1)[-1]
    text = article.get_text(" ", strip=True)
    doi_match = re.search(r"10\.\d{4,9}/\S+", text)
    if doi_match:
        return doi_match.group(0).rstrip(".,;")
    return None


def parse_issue_html(html: str, *, issue_url: str, year: int) -> list[PaperRecord]:
    soup = BeautifulSoup(html, "html.parser")
    papers: list[PaperRecord] = []
    for section in _section_nodes(soup):
        track = _extract_track(section)
        for article in _article_nodes(section):
            title_link = _extract_title_link(article)
            if title_link is None or not title_link.get("href"):
                continue
            title = " ".join(title_link.get_text(" ", strip=True).split())
            article_url = urljoin(issue_url, title_link["href"])
            authors = _extract_authors(article)
            doi = _extract_doi(article)
            article_id = _article_id_from_url(article_url)
            attachments = _extract_attachments(article, issue_url)
            pdf_url = next((attachment.url for attachment in attachments if attachment.role == "paper"), None)
            papers.append(
                PaperRecord(
                    paper_id=build_paper_id("phm", year, title, article_id=article_id, doi=doi),
                    source="phm",
                    year=year,
                    track=track,
                    title=title,
                    authors=authors,
                    article_url=article_url,
                    doi=doi,
                    article_id=article_id,
                    issue_url=issue_url,
                    pdf_url=pdf_url,
                    attachments=attachments,
                )
            )
    return papers


def is_main_paper_track(track: str) -> bool:
    normalized = " ".join(track.lower().split())
    if not normalized:
        return False
    if any(hint in normalized for hint in _EXCLUDED_TRACK_HINTS):
        return False
    return "paper" in normalized


def filter_main_papers(papers: list[PaperRecord]) -> list[PaperRecord]:
    return [paper for paper in papers if is_main_paper_track(paper.track)]


def _published_text_fallback(soup: BeautifulSoup) -> str | None:
    combined = " ".join(soup.stripped_strings)
    match = re.search(r"Published\s+([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}|\d{4}-\d{2}-\d{2})", combined)
    if match:
        return match.group(1)
    return None


def parse_article_html(html: str) -> ArticlePageDetails:
    soup = BeautifulSoup(html, "html.parser")
    doi_link = soup.select_one(".item.doi a[href], section.item.doi a[href], a[href*='doi.org/']")
    doi = None
    if doi_link and doi_link.get("href"):
        doi = doi_link["href"].rsplit("doi.org/", 1)[-1]
    published_node = soup.select_one(
        ".item.published .value, section.item.published .value, .published, .article-details .published"
    )
    published_at = published_node.get_text(" ", strip=True) if published_node else _published_text_fallback(soup)
    attachments = _extract_attachments(soup, "https://papers.phmsociety.org")
    return ArticlePageDetails(doi=doi, published_at=published_at, attachments=attachments)
