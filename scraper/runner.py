"""Orkestrasi scraping: menelusuri tiap sumber per tanggal dan menghasilkan event progres + record."""
from . import bmkg, detik, kompas
from .common import Fetcher, date_range, match_keywords
from .labeling import detect_lokasi

COLUMNS = ["tanggal", "sumber", "judul", "isi_teks", "lokasi", "keyword", "url"]


def run(sources, start, end, keywords, detik_channels=("news",), max_pages=50, delay=1.0, max_articles=0):
    """Generator yang menghasilkan tuple:
        ("progress", fraksi_0_sampai_1, pesan)
        ("record", dict)
    """
    fetcher = Fetcher(delay=delay)
    keywords = [k.strip().lower() for k in keywords if k.strip()]
    days = list(date_range(start, end))

    # satu "tugas" = satu sumber/kanal pada satu hari
    tasks = []
    if "Detik" in sources:
        tasks += [("detik", ch, d) for d in days for ch in detik_channels]
    if "Kompas" in sources:
        tasks += [("kompas", None, d) for d in days]
    total = len(tasks) + (1 if "BMKG" in sources else 0)
    done, count, seen = 0, 0, set()

    def limit_reached():
        return max_articles and count >= max_articles

    if "BMKG" in sources:
        yield ("progress", 0.0, "BMKG: mengambil data gempa (open data JSON)...")
        for rec in bmkg.fetch(fetcher, start, end):
            hit = match_keywords(f"{rec['judul']} {rec['isi_teks']}", keywords)
            if hit and not limit_reached():
                rec["keyword"] = ", ".join(hit)
                count += 1
                yield ("record", rec)
        done += 1

    for source, channel, day in tasks:
        if limit_reached():
            break
        name = f"detik/{channel}" if source == "detik" else "kompas"
        yield ("progress", done / total, f"{name} {day:%d-%m-%Y}: membaca indeks...")

        listing = (detik.iter_listing(fetcher, channel, day, max_pages) if source == "detik"
                   else kompas.iter_listing(fetcher, day, max_pages))
        parser = detik.parse_article if source == "detik" else kompas.parse_article

        for item in listing:
            if item["url"] in seen:
                continue
            hit = match_keywords(f"{item['judul']} {item['ringkasan']}", keywords)
            if not hit:
                continue
            seen.add(item["url"])
            yield ("progress", done / total, f"{name} {day:%d-%m-%Y}: {item['judul'][:70]}")
            rec = parser(fetcher, item["url"])
            if rec is None:
                continue
            rec["keyword"] = ", ".join(hit)
            count += 1
            rec["lokasi"] = detect_lokasi(rec["judul"], rec["isi_teks"])
            yield ("record", rec)
            if limit_reached():
                break
        done += 1

    yield ("progress", 1.0, f"Selesai. {count} data terkumpul.")
