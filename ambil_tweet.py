import argparse
import sys
from datetime import date, datetime, timedelta

from scraper import twitter
from scraper.storage import RAW_TWEET_DIR, OUTPUT_DIR, env_token, merge_and_save, safe_filename


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keyword", default="", help="dipisah koma (digabung OR)")
    ap.add_argument("--hari", type=int, default=30, help="simpan tweet dari N hari terakhir (default 3)")
    ap.add_argument("--limit", type=int, default=10, help="maks. tweet per run")
    ap.add_argument("--nama", default="data_gibran", help="nama file hasil (tanpa ekstensi)")
    ap.add_argument("--format", default="csv", choices=["csv", "xlsx", "json"])
    ap.add_argument("--bahasa", default="id", help="kode bahasa, kosongkan untuk semua bahasa")
    args = ap.parse_args()

    token = env_token()
    if not token:
        sys.exit("X_AUTH_TOKEN kosong. Isi token di file .env terlebih dahulu.")

    keywords = [k.strip() for k in args.keyword.split(",") if k.strip()]
    end = date.today()
    start = end - timedelta(days=args.hari - 1)
    query = twitter.build_query(keywords, args.bahasa)
    out_name = safe_filename(args.nama, "data_tweet")
    raw_name = f"{out_name}_raw"
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] query: {query} | simpan {start} s.d. {end}")

    for line in twitter.harvest(token, query, start, end, args.limit, raw_name, RAW_TWEET_DIR,
                                tab="LATEST", date_mode="none"):
        print(line, flush=True)

    raw_path = twitter.find_output(RAW_TWEET_DIR, raw_name)
    if raw_path is None:
        sys.exit(f"Tidak ada tweet. Cek log: {RAW_TWEET_DIR / (raw_name + '.log')}")

    records = twitter.process_csv(raw_path, keywords, start=start, end=end)
    out_path = OUTPUT_DIR / f"{out_name}.{args.format}"
    df, n_new = merge_and_save(records, out_path, args.format, append=True)
    print(f"{n_new} tweet baru, total {len(df)} di {out_path}")


if __name__ == "__main__":
    main()
