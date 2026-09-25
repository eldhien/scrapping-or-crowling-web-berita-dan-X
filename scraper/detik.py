"""Scraper detik.com lewat halaman indeks harian.

Halaman pencarian detik mengabaikan filter tanggal, jadi kita telusuri indeks per hari
(`/indeks?page=N&date=MM/DD/YYYY`) lalu saring judul + ringkasan dengan keyword.
"""
from datetime import datetime

from .common import add_query, extract_paragraphs

CHANNELS = {
    "news": "https://news.detik.com/indeks",
    "jatim": "https://www.detik.com/jatim/indeks",
    "jabar": "https://www.detik.com/jabar/indeks",
    "jateng": "https://www.detik.com/jateng/indeks",
    "jogja": "https://www.detik.com/jogja/indeks",
    "bali": "https://www.detik.com/bali/indeks",
    "sumut": "https://www.detik.com/sumut/indeks",
    "sulsel": "https://www.detik.com/sulsel/indeks",
    "sumbagsel": "https://www.detik.com/sumbagsel/indeks",
    "kalimantan": "https://www.detik.com/kalimantan/indeks",
}

SKIP_URL_PARTS = ("20.detik.com", "/foto-", "/video", "/infografis")


def iter_listing(fetcher, channel, day, max_pages):
    """Yield dict {url, judul, ringkasan} dari indeks satu kanal pada satu hari."""
    base = CHANNELS[channel]
    date_param = day.strftime("%m/%d/%Y")
    seen = set()
    for page in range(1, max_pages + 1):
        soup = fetcher.soup(f"{base}?page={page}&date={date_param}")
        if soup is None:
            break
        new_items = 0
        for art in soup.select("article"):
            link = art.select_one(".media__title a[href]")
            if link is None:
                continue
            url = link["href"]
            if url in seen or any(p in url for p in SKIP_URL_PARTS):
                continue
            seen.add(url)
            new_items += 1
            desc = art.select_one(".media__desc")
            yield {
                "url": url,
                "judul": link.get_text(strip=True),
                "ringkasan": desc.get_text(" ", strip=True) if desc else "",
            }
        if new_items == 0 or not soup.select_one(f'.pagination a[href*="page={page + 1}&"]'):
            break


def parse_article(fetcher, url):
    # single=1 menampilkan artikel multi-halaman dalam satu halaman
    soup = fetcher.soup(add_query(url, "single=1"))
    if soup is None:
        return None
    title = soup.select_one("h1.detail__title")
    body = soup.select_one(".detail__body-text")
    if title is None or body is None:
        return None
    for junk in body.select("script, style, table.linksisip, .linksisip, .parallaxindetail, "
                            ".staticdetail_container, .detail__body-tag, .noncontent, .sisip_embed_sosmed"):
        junk.decompose()

    tanggal = ""
    meta = soup.find("meta", attrs={"name": "publishdate"})
    if meta and meta.get("content"):
        try:
            tanggal = datetime.strptime(meta["content"], "%Y/%m/%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            tanggal = meta["content"]

    return {
        "tanggal": tanggal,
        "sumber": "detik.com",
        "judul": title.get_text(strip=True),
        "isi_teks": extract_paragraphs(body),
        "url": url,
    }
