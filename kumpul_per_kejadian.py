import argparse
import json
import math
import sys
from datetime import date, timedelta

from scraper import twitter
from scraper.storage import OUTPUT_DIR, RAW_TWEET_DIR, env_token, load_existing, merge_and_save, safe_filename

# topik bawaan CLI: nama -> keyword pencarian (digabung OR). Topik lain lewat --kejadian NAMA --keyword ...
EVENTS = {
    "Gempa": ["gempa"],
    "Banjir": ["banjir"],
    "Longsor": ["longsor", "tanah longsor"],
}
PROGRESS_FILE = OUTPUT_DIR / "progress_kumpul.json"
BUFFER = 1.3  # ambil lebih banyak dari target karena retweet/duplikat dibuang


def out_path(event, fmt):
    return OUTPUT_DIR / f"data_tweet{safe_filename(event, 'topik')}.{fmt}"


def count_rows(event, fmt):
    return len(load_existing(out_path(event, fmt), fmt))


def months_back(years):
    today = date.today()
    first = date(today.year, today.month, 1)
    result = []
    for _ in range(years * 12):
        nxt = date(first.year + (first.month == 12), first.month % 12 + 1, 1)
        result.append((first, min(nxt - timedelta(days=1), today)))
        first = date(first.year - (first.month == 1), (first.month - 2) % 12 + 1, 1)
    return result


def run_once(token, event, keywords, lang, limit, start, end, date_mode, raw_name, fmt):
    """Generator dipakai bersama oleh CLI dan web.
    yield ("log", baris) selama tweet-harvest berjalan, lalu di akhir yield ("result", n_new, raw_path)."""
    query = twitter.build_query(keywords, lang)
    for line in twitter.harvest(token, query, start, end, limit, raw_name, RAW_TWEET_DIR,
                                tab="LATEST", date_mode=date_mode):
        yield ("log", line)
    raw = twitter.find_output(RAW_TWEET_DIR, raw_name)
    if raw is None:
        yield ("result", 0, None)
        return
    records = twitter.process_csv(raw, keywords,
                                  start=None if date_mode == "none" else start,
                                  end=None if date_mode == "none" else end)
    _, n_new = merge_and_save(records, out_path(event, fmt), fmt, append=True)
    yield ("result", n_new, raw)


def run_once_cli(*args, **kwargs):
    """Bungkus run_once untuk CLI: cetak log penting ke stdout, kembalikan n_new."""
    n_new = 0
    for item in run_once(*args, **kwargs):
        if item[0] == "log":
            line = item[1]
            if "Total tweets saved" in line or "No tweets found" in line or "rate limit" in line.lower() \
                    or "Invalid" in line or "Error" in line:
                print("   ", line, flush=True)
        else:
            n_new = item[1]
    return n_new


def load_progress():
    try:
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["terbaru", "bulanan"], default="terbaru")
    ap.add_argument("--kejadian", default=",".join(EVENTS),
                    help=f"nama topik (bawaan: {', '.join(EVENTS)}); nama lain = topik baru, keyword dari --keyword")
    ap.add_argument("--keyword", default="", help="keyword (dipisah koma) untuk topik di luar bawaan")
    ap.add_argument("--target", type=int, default=2000, help="target jumlah data per kejadian")
    ap.add_argument("--tahun", type=int, default=5, help="mode bulanan: berapa tahun ke belakang")
    ap.add_argument("--metode-tanggal", default="date", choices=["date", "time", "id"],
                    help="mode bulanan: date=since/until, time=since_time/until_time, id=since_id/max_id")
    ap.add_argument("--bahasa", default="id")
    ap.add_argument("--format", default="csv", choices=["csv", "xlsx", "json"])
    args = ap.parse_args()

    token = env_token()
    if not token:
        sys.exit("X_AUTH_TOKEN kosong. Isi token di file .env terlebih dahulu.")
    events = [e.strip() for e in args.kejadian.split(",") if e.strip()]
    extra_kw = [k.strip() for k in args.keyword.split(",") if k.strip()]
    for e in events:
        EVENTS.setdefault(e, EVENTS.get(e.capitalize()) or extra_kw or [e])

    if args.mode == "terbaru":
        for event in events:
            have = count_rows(event, args.format)
            if have >= args.target:
                print(f"[{event}] sudah {have} data (target {args.target}), dilewati.")
                continue
            limit = math.ceil((args.target - have) * BUFFER)
            print(f"[{event}] punya {have}, mengambil ±{limit} tweet terbaru...", flush=True)
            n_new = run_once_cli(token, event, EVENTS[event], args.bahasa, limit, date.today(), date.today(),
                             "none", f"raw_{event}_terbaru", args.format)
            total = count_rows(event, args.format)
            print(f"[{event}] +{n_new} baru, total {total} → {out_path(event, args.format)}")
            if total < args.target:
                print(f"[{event}] belum mencapai target. X hanya memberi tweet terbaru; jalankan lagi "
                      f"besok (data baru akan digabung) atau pakai mode bulanan.")
        return

    # ---- mode bulanan
    months = months_back(args.tahun)
    per_month = math.ceil(args.target * BUFFER / len(months))
    progress = load_progress()
    print(f"{len(months)} bulan x {len(events)} kejadian, ±{per_month} tweet per bulan. "
          f"Metode tanggal: {args.metode_tanggal}")
    empty_streak = 0
    for event in events:
        done = set(progress.get(event, []))
        for start, end in months:
            key = f"{start:%Y-%m}"
            if key in done:
                continue
            print(f"[{event} {key}] mengambil ±{per_month} tweet...", flush=True)
            n_new = run_once_cli(token, event, EVENTS[event], args.bahasa, per_month, start, end,
                             args.metode_tanggal, f"raw_{event}_{start:%Y%m}", args.format)
            print(f"[{event} {key}] +{n_new} baru, total {count_rows(event, args.format)}")
            empty_streak = empty_streak + 1 if n_new == 0 else 0
            if empty_streak >= 3:
                sys.exit("3 bulan berturut-turut 0 tweet. Kemungkinan filter tanggal diblokir untuk akun ini "
                         "atau kena rate limit. Cek log di hasil/raw_tweets/, lalu jalankan lagi nanti "
                         "(bulan yang sudah selesai tidak diulang).")
            if n_new > 0:  # bulan kosong tidak dicatat, supaya dicoba ulang di run berikutnya
                done.add(key)
                progress[event] = sorted(done)
                PROGRESS_FILE.write_text(json.dumps(progress, indent=2), encoding="utf-8")
        print(f"[{event}] selesai: {count_rows(event, args.format)} data → {out_path(event, args.format)}")


if __name__ == "__main__":
    main()
