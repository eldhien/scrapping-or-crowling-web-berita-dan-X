"""Kumpulkan tweet X berdasarkan keyword, jumlah, dan rentang tanggal ke satu file.

Contoh:
  python kumpul_per_kejadian.py --keyword "jakarta" --jumlah 1000 --nama jakarta --mulai 2025-10-08
Dipakai bersama oleh CLI dan tab "Pengaturan Scraping" di app.py.
"""
import argparse
import math
import sys
from datetime import date, datetime

from scraper import twitter
from scraper.storage import OUTPUT_DIR, RAW_TWEET_DIR, env_token, merge_and_save, safe_filename

BUFFER = 1.3  # ambil lebih banyak dari target karena retweet/duplikat dibuang


def out_path(nama, fmt):
    return OUTPUT_DIR / f"{safe_filename(nama, 'data_tweet')}.{fmt}"


def run_once(token, keywords, lang, jumlah, start, end, date_mode, nama, fmt, exclude_rt=True):
    """Generator dipakai bersama oleh CLI dan web.
    yield ("log", baris) selama tweet-harvest berjalan, lalu di akhir yield ("result", n_new, df, path)."""
    query = twitter.build_query(keywords, lang)
    raw_name = f"{safe_filename(nama, 'data_tweet')}_raw"
    limit = math.ceil(jumlah * BUFFER)
    for line in twitter.harvest(token, query, start, end, limit, raw_name, RAW_TWEET_DIR,
                                tab="LATEST", date_mode=date_mode):
        yield ("log", line)
    raw = twitter.find_output(RAW_TWEET_DIR, raw_name)
    if raw is None:
        yield ("result", 0, None, None)
        return
    records = twitter.process_csv_umum(raw, keywords, exclude_rt,
                                       start=None if date_mode == "none" else start,
                                       end=None if date_mode == "none" else end)
    records = records[:jumlah]
    path = out_path(nama, fmt)
    df, n_new = merge_and_save(records, path, fmt, append=True,
                               columns=twitter.TWEET_COLUMNS, dedupe=("url",))
    yield ("result", n_new, df, path)


def _tanggal(text):
    return datetime.strptime(text, "%Y-%m-%d").date()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keyword", required=True, help="kata kunci, dipisah koma (digabung OR)")
    ap.add_argument("--jumlah", type=int, default=1000, help="jumlah tweet yang diambil")
    ap.add_argument("--nama", default="data_tweet", help="nama file hasil (tanpa ekstensi)")
    ap.add_argument("--mulai", type=_tanggal, default=None, help="tanggal mulai YYYY-MM-DD (kosong = tanpa filter)")
    ap.add_argument("--akhir", type=_tanggal, default=None, help="tanggal akhir YYYY-MM-DD (kosong = hari ini)")
    ap.add_argument("--metode-tanggal", default="date", choices=["date", "time", "id"],
                    help="date=since/until, time=since_time/until_time, id=since_id/max_id")
    ap.add_argument("--bahasa", default="id", help="kode bahasa, kosongkan untuk semua bahasa")
    ap.add_argument("--format", default="csv", choices=["csv", "xlsx", "json"])
    args = ap.parse_args()

    token = env_token()
    if not token:
        sys.exit("X_AUTH_TOKEN kosong. Isi token di file .env terlebih dahulu.")
    keywords = [k.strip() for k in args.keyword.split(",") if k.strip()]
    end = args.akhir or date.today()
    start = args.mulai or end
    date_mode = "none" if args.mulai is None else args.metode_tanggal

    n_new, path = 0, None
    for item in run_once(token, keywords, args.bahasa, args.jumlah, start, end, date_mode, args.nama, args.format):
        if item[0] == "log":
            print("   ", item[1], flush=True)
        else:
            _, n_new, df, path = item
    if path is None:
        sys.exit(f"Tidak ada tweet. Cek log di {RAW_TWEET_DIR}")
    print(f"{n_new} tweet baru tersimpan di {path}")


if __name__ == "__main__":
    main()
