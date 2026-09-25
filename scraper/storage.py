"""Simpan/baca file hasil, nama file aman, dan pembaca file .env (tanpa dependensi tambahan)."""
import os
import re
from pathlib import Path

import pandas as pd
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

from .runner import COLUMNS

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "hasil"
RAW_TWEET_DIR = OUTPUT_DIR / "raw_tweets"
ENV_FILE = ROOT / ".env"
EXCEL_CELL_LIMIT = 32767


def load_env(path=ENV_FILE):
    """Baca KEY=VALUE dari .env ke os.environ (nilai yang sudah ada di environment tidak ditimpa)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env_token():
    load_env()
    return os.environ.get("X_AUTH_TOKEN", "").strip()


def safe_filename(name, default="data_bencana"):
    name = re.sub(r"[^\w\-]+", "_", name.strip()).strip("_")
    return name or default


def save(df, path, fmt):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "csv":
        df.to_csv(path, index=False, encoding="utf-8-sig")
    elif fmt == "xlsx":
        clean = df.map(lambda v: ILLEGAL_CHARACTERS_RE.sub("", v)[:EXCEL_CELL_LIMIT] if isinstance(v, str) else v)
        clean.to_excel(path, index=False)
    else:
        df.to_json(path, orient="records", force_ascii=False, indent=2)


def load_existing(path, fmt):
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    if fmt == "csv":
        return pd.read_csv(path, dtype=str).fillna("")
    if fmt == "xlsx":
        return pd.read_excel(path, dtype=str).fillna("")
    return pd.read_json(path, dtype=False).fillna("")


def merge_and_save(records, path, fmt, append=False):
    """Gabungkan record (dan isi file lama jika append), buang duplikat, simpan.
    Return (DataFrame akhir, jumlah data baru)."""
    df = pd.DataFrame(records, columns=COLUMNS)
    n_before = 0
    if append:
        old = load_existing(path, fmt)
        n_before = len(old)
        df = pd.concat([old, df], ignore_index=True)
    df = df.drop_duplicates(subset=["url", "isi_teks"]).sort_values("tanggal").reset_index(drop=True)
    save(df, path, fmt)
    return df, len(df) - n_before
