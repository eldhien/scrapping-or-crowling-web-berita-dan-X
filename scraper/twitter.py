"""Tweet X lewat tweet-harvest (https://github.com/helmisatria/tweet-harvest).

tweet-harvest menjalankan Chromium dengan cookie `auth_token` akun X. Token hanya diteruskan
ke proses tweet-harvest dan tidak pernah ditulis ke disk oleh modul ini.
"""
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .labeling import detect_lokasi

TWEET_HARVEST = "tweet-harvest@2.7.1"
WIB = timezone(timedelta(hours=7))
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# Normalisasi bahasa informal umum khusus untuk deteksi lokasi/keyword (isi_teks asli tidak diubah)
SLANG = {
    "yg": "yang", "dg": "dengan", "dgn": "dengan", "gak": "tidak", "ga": "tidak", "nggak": "tidak",
    "enggak": "tidak", "gk": "tidak", "tdk": "tidak", "blm": "belum", "udh": "sudah", "udah": "sudah",
    "bgt": "banget", "krn": "karena", "utk": "untuk", "sy": "saya",
}
_SLANG_RE = re.compile(r"(" + "|".join(map(re.escape, SLANG)) + r")", re.I)
_URL_RE = re.compile(r"https?://\S+")
_MENTION_RE = re.compile(r"@\w+")


def normalize_text(text):
    text = _URL_RE.sub(" ", text)
    text = _MENTION_RE.sub(" ", text)
    text = text.replace("#", " ")
    return _SLANG_RE.sub(lambda m: SLANG[m.group(1).lower()], text)


def build_query(keywords, lang="id"):
    # Retweet tidak disaring lewat query (-filter:retweets bisa membuat hasil kosong saat diketik
    # ke form Advanced Search), melainkan dibuang di process_csv.
    kws = [k.strip() for k in keywords if k.strip()]
    query = "(" + " OR ".join(f'"{k}"' if " " in k else k for k in kws) + ")" if len(kws) > 1 else "".join(kws)
    if lang:
        query += f" lang:{lang}"
    return query.strip()


# Cara memfilter tanggal di pencarian X. since:/until: kadang diblokir untuk sebagian akun,
# jadi disediakan alternatif berbasis unix time dan ID tweet (snowflake).
DATE_MODES = {
    "Tanpa filter tanggal (tweet terbaru, disaring setelahnya)": "none",
    "since_time / until_time (unix)": "time",
    "since_id / max_id (ID tweet)": "id",
    "since / until (tanggal)": "date",
}
TWITTER_EPOCH_MS = 1288834974657


def _midnight_wib(day):
    return datetime(day.year, day.month, day.day, tzinfo=WIB)


def date_operators(start, end, mode):
    """Operator rentang tanggal [start, end] (inklusif, WIB) untuk query X."""
    if mode == "none":
        return ""
    t0, t1 = _midnight_wib(start), _midnight_wib(end + timedelta(days=1))
    if mode == "time":
        return f"since_time:{int(t0.timestamp())} until_time:{int(t1.timestamp())}"
    if mode == "id":
        to_id = lambda t: (int(t.timestamp() * 1000) - TWITTER_EPOCH_MS) << 22
        return f"since_id:{to_id(t0)} max_id:{to_id(t1)}"
    return f"since:{start:%Y-%m-%d} until:{end + timedelta(days=1):%Y-%m-%d}"


def harvest(token, query, start, end, limit, out_name, workdir, tab="LATEST", delay=3, date_mode="time"):
    """Jalankan tweet-harvest dan yield baris log-nya (token disamarkan).
    Hasil CSV ada di <workdir>/tweets-data/<out_name>.csv"""
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if npx is None:
        raise RuntimeError("npx tidak ditemukan. Install Node.js dulu: https://nodejs.org")
    Path(workdir).mkdir(parents=True, exist_ok=True)
    # Operator tanggal ditulis sendiri ke query (tidak memakai -f/--to tweet-harvest yang selalu since:/until:)
    query = f"{query} {date_operators(start, end, date_mode)}".strip()
    cmd = [
        npx, "-y", TWEET_HARVEST,
        "-o", f"{out_name}.csv",
        "-s", query,
        "--tab", tab,
        "-l", str(limit),
        "-d", str(delay),
        "-t", token,
    ]
    proc = subprocess.Popen(cmd, cwd=workdir, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    # log (token disamarkan) disimpan supaya kegagalan bisa dianalisis
    with open(Path(workdir) / f"{out_name}.log", "w", encoding="utf-8") as log:
        log.write(f"query: {query} | {start} s.d. {end} | limit {limit} | tab {tab}\n")
        for line in proc.stdout:
            line = _ANSI_RE.sub("", line).rstrip().replace(token, "***")
            if line:
                log.write(line + "\n")
                yield line
        proc.wait()
        if proc.returncode != 0:
            msg = f"[tweet-harvest selesai dengan kode {proc.returncode}]"
            log.write(msg + "\n")
            yield msg


def find_output(workdir, out_name):
    """Path CSV hasil tweet-harvest, atau None kalau tidak ada / kosong (0 tweet)."""
    candidates = [Path(workdir) / "tweets-data" / f"{out_name}.csv", Path(workdir) / f"{out_name}.csv"]
    return next((p for p in candidates if p.exists() and p.stat().st_size > 10), None)


def _parse_date(value):
    for fmt in ("%a %b %d %H:%M:%S %z %Y", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(str(value), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(WIB).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return str(value)


def _col(df, *names):
    return next((n for n in names if n in df.columns), None)


def process_csv(source, keywords=(), exclude_retweets=True, start=None, end=None):
    """Ubah CSV tweet-harvest (path atau file upload) menjadi record berkolom sama dengan data berita.
    start/end (date, opsional): hanya ambil tweet yang tanggalnya (WIB) di rentang itu."""
    try:
        df = pd.read_csv(source, dtype=str).fillna("")
    except pd.errors.EmptyDataError:
        raise ValueError("File CSV kosong (0 tweet).")
    text_col = _col(df, "full_text", "text", "tweet", "content")
    if text_col is None:
        raise ValueError(f"Kolom teks tweet tidak ditemukan. Kolom yang ada: {list(df.columns)}")
    date_col = _col(df, "created_at", "date", "tanggal")
    user_col = _col(df, "username", "user_screen_name", "screen_name")
    url_col = _col(df, "tweet_url", "url")
    id_col = _col(df, "id_str", "id", "tweet_id")

    if id_col:
        df = df.drop_duplicates(subset=[id_col])
    if exclude_retweets:
        df = df[~df[text_col].str.startswith("RT @")]
    keywords = [k.strip().lower() for k in keywords if k.strip()]

    records = []
    for _, row in df.iterrows():
        text = row[text_col].strip()
        norm = normalize_text(text)
        hit = [k for k in keywords if k in norm.lower()] if keywords else ["(semua)"]
        if not hit:
            continue
        tanggal = _parse_date(row[date_col]) if date_col else ""
        if start and end and tanggal[:10] and not (f"{start}" <= tanggal[:10] <= f"{end}"):
            continue
        url = row[url_col] if url_col else ""
        if not url and user_col and id_col:
            url = f"https://x.com/{row[user_col]}/status/{row[id_col]}"
        records.append({
            "tanggal": tanggal,
            "sumber": "x.com",
            "judul": f"@{row[user_col]}" if user_col else "",
            "isi_teks": text,
            "lokasi": detect_lokasi("", norm),
            "keyword": ", ".join(hit),
            "url": url,
        })
    return records
