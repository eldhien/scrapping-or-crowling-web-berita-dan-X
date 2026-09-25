"""Utilitas bersama: HTTP fetcher yang sopan (ada jeda & retry), rentang tanggal, dan pembersih teks."""
import time
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 (research-scraper)"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}

# Paragraf yang bukan bagian isi berita (iklan, tautan sisipan, ajakan unduh aplikasi, dll.)
NOISE_PREFIXES = (
    "baca juga",
    "scroll to continue",
    "simak video",
    "simak juga",
    "tonton juga",
    "advertisement",
    "dapatkan update",
    "baca berita tanpa iklan",
    "download aplikasi",
    "gabung kompas.com+",
    "copyright",
    "[gambas",
    "disclaimer",
)


class Fetcher:
    """Wrapper requests.Session dengan jeda minimum antar request dan retry sederhana."""

    def __init__(self, delay=1.0, timeout=20):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.delay = delay
        self.timeout = timeout
        self._last = 0.0

    def get(self, url, retries=3):
        for attempt in range(retries):
            wait = self.delay - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            try:
                resp = self.session.get(url, timeout=self.timeout)
                self._last = time.time()
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return resp
            except requests.RequestException:
                self._last = time.time()
                if attempt == retries - 1:
                    return None
                time.sleep(2 * (attempt + 1))
        return None

    def soup(self, url):
        resp = self.get(url)
        return BeautifulSoup(resp.text, "lxml") if resp is not None else None

    def json(self, url):
        resp = self.get(url)
        return resp.json() if resp is not None else None


def date_range(start: date, end: date):
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def match_keywords(text, keywords):
    """Kembalikan keyword yang muncul di text (case-insensitive). Tanpa keyword = semua lolos."""
    if not keywords:
        return ["(semua)"]
    low = text.lower()
    return [k for k in keywords if k in low]


def extract_paragraphs(container):
    """Ambil teks per paragraf <p> dan buang paragraf noise. Fallback ke seluruh teks container."""
    paragraphs = []
    for p in container.find_all("p"):
        text = p.get_text(" ", strip=True)
        if not text or text.lower().startswith(NOISE_PREFIXES):
            continue
        paragraphs.append(text)
    if not paragraphs:
        return container.get_text(" ", strip=True)
    return "\n".join(paragraphs)


def add_query(url, param):
    return f"{url}{'&' if '?' in url else '?'}{param}"
