"""Data gempa dari open data resmi BMKG (JSON), bukan scraping HTML.

Catatan: feed publik BMKG hanya memuat kejadian TERBARU (±15 gempa per feed).
Data historis harus diminta lewat https://dataonline.bmkg.go.id (perlu registrasi).
"""
import re
from datetime import datetime, timedelta, timezone

FEEDS = {
    "autogempa": "https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json",
    "gempaterkini": "https://data.bmkg.go.id/DataMKG/TEWS/gempaterkini.json",
    "gempadirasakan": "https://data.bmkg.go.id/DataMKG/TEWS/gempadirasakan.json",
}
WIB = timezone(timedelta(hours=7))


def _lokasi(wilayah):
    # "Pusat gempa berada di laut 57 km timur Kota Bima" -> "Kota Bima"
    # "127 km BaratLaut TAHUNA-KEP.SANGIHE-SULUT"        -> "Tahuna, Kep.Sangihe, Sulut"
    m = re.search(r"\d+\s*km\s+\S+\s+(.+)$", wilayah)
    place = m.group(1) if m else wilayah
    if place.isupper():
        place = ", ".join(p.strip().title() for p in place.split("-") if p.strip())
    return place.strip()


def fetch(fetcher, start, end):
    """Ambil gempa dari semua feed BMKG yang tanggalnya (WIB) berada di [start, end]."""
    records, seen = [], set()
    for feed, url in FEEDS.items():
        data = fetcher.json(url)
        if not data:
            continue
        gempa = data.get("Infogempa", {}).get("gempa", [])
        if isinstance(gempa, dict):
            gempa = [gempa]
        for g in gempa:
            try:
                waktu = datetime.fromisoformat(g["DateTime"]).astimezone(WIB)
            except (KeyError, ValueError):
                continue
            key = (g.get("DateTime"), g.get("Coordinates"))
            if key in seen or not (start <= waktu.date() <= end):
                continue
            seen.add(key)

            wilayah = g.get("Wilayah", "")
            dirasakan = g.get("Dirasakan", "")
            isi = (
                f"Gempa bumi bermagnitudo {g.get('Magnitude')} terjadi pada {g.get('Tanggal')} pukul {g.get('Jam')}. "
                f"Episentrum di {g.get('Lintang')}, {g.get('Bujur')} dengan kedalaman {g.get('Kedalaman')}. "
                f"{wilayah}."
            )
            if dirasakan:
                isi += f" Dirasakan (skala MMI): {dirasakan}."
            if g.get("Potensi"):
                isi += f" {g['Potensi']}."

            records.append({
                "tanggal": waktu.strftime("%Y-%m-%d %H:%M:%S"),
                "sumber": f"bmkg ({feed})",
                "judul": f"Gempa M {g.get('Magnitude')} - {wilayah}",
                "isi_teks": isi,
                "lokasi": _lokasi(wilayah),
                "url": url,
            })
    return records
