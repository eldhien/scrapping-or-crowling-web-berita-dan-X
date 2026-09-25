"""Scraper kompas.com lewat halaman indeks harian (`indeks.kompas.com/?site=all&date=YYYY-MM-DD&page=N`).

Pencarian kompas dirender dengan JavaScript, jadi indeks per tanggal lebih andal.
"""
from datetime import datetime

from .common import add_query, extract_paragraphs

INDEX_URL = "https://indeks.kompas.com/"
SKIP_URL_PARTS = ("video.kompas.com", "/foto/", "/image/", "/infografik/")


def iter_listing(fetcher, day, max_pages):
    """Yield dict {url, judul, ringkasan} dari indeks kompas pada satu hari."""
    seen = set()
    for page in range(1, max_pages + 1):
        soup = fetcher.soup(f"{INDEX_URL}?site=all&date={day:%Y-%m-%d}&page={page}")
        if soup is None:
            break
        new_items = 0
        for item in soup.select(".articleItem"):
            link = item.select_one("a.article-link[href]")
            title = item.select_one(".articleTitle")
            if link is None or title is None:
                continue
            url = link["href"]
            if url in seen or any(p in url for p in SKIP_URL_PARTS):
                continue
            seen.add(url)
            new_items += 1
            yield {"url": url, "judul": title.get_text(" ", strip=True), "ringkasan": ""}
        if new_items == 0:
            break


def parse_article(fetcher, url):
    # page=all menampilkan artikel multi-halaman dalam satu halaman
    soup = fetcher.soup(add_query(url, "page=all"))
    if soup is None:
        return None
    title = soup.select_one("h1.read__title")
    body = soup.select_one(".read__content")
    if title is None or body is None:
        return None
    for junk in body.select("script, style, .inner-link-baca-juga, .ads-on-body, .video-wrap, "
                            ".kompasidRec, .read__bottom, .ga--readmore"):
        junk.decompose()

    tanggal = ""
    meta = soup.find("meta", attrs={"name": "content_PublishedDate"})
    if meta and meta.get("content"):
        try:
            tanggal = datetime.strptime(meta["content"], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            tanggal = meta["content"]

    return {
        "tanggal": tanggal,
        "sumber": "kompas.com",
        "judul": title.get_text(strip=True),
        "isi_teks": extract_paragraphs(body),
        "url": url,
    }
