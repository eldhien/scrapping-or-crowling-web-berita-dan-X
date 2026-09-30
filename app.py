"""Web scraping data berita (Detik, Kompas, BMKG) dan tweet X untuk data penelitian.

Jalankan:  streamlit run app.py
"""
import json
import math
from collections import deque
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from kumpul_per_kejadian import PROGRESS_FILE, count_rows, load_progress, months_back, out_path, run_once
from scraper import detik, twitter
from scraper.runner import COLUMNS, run
from scraper.storage import OUTPUT_DIR, RAW_TWEET_DIR, env_token, load_existing, merge_and_save, safe_filename, save


def valid_range(rentang):
    if not isinstance(rentang, (tuple, list)) or len(rentang) != 2:
        st.error("Pilih tanggal mulai dan tanggal akhir.")
        return None
    return rentang


def show_result(records, out_path, fmt, key, append=False):
    if not records:
        st.warning("Tidak ada data yang cocok. Coba perluas rentang waktu atau ubah keyword.")
        return
    df, n_new = merge_and_save(records, out_path, fmt, append)
    st.dataframe(df, width="stretch")
    if append:
        st.success(f"{n_new} data baru digabung, total {len(df)} data di: {out_path}")
    else:
        st.success(f"{len(df)} data tersimpan di: {out_path}")

    s1, s2 = st.columns(2)
    s1.write("**Per sumber**")
    s1.dataframe(df["sumber"].value_counts())
    s2.write("**Per keyword**")
    s2.dataframe(df["keyword"].value_counts())
    st.download_button("Unduh file", out_path.read_bytes(), file_name=out_path.name, key=key)


# ============================================================================ tab berita
def tab_berita():
    with st.form("form_berita"):
        c1, c2 = st.columns(2)
        with c1:
            sources = st.multiselect("1. Sumber", ["Detik", "Kompas", "BMKG"], default=["Detik", "Kompas"])
            detik_channels = st.multiselect("Kanal Detik", list(detik.CHANNELS), default=["news"],
                                            help="news = detikNews nasional; lainnya kanal regional.")
            today = date.today()
            rentang = st.date_input("2. Rentang waktu", value=(today - timedelta(days=3), today),
                                    max_value=today, format="DD/MM/YYYY")
        with c2:
            keywords = st.text_input("3. Keyword (pisahkan dengan koma)", value="", placeholder="contoh: pemilu, pilpres",
                                     help="Dicocokkan ke judul (dan ringkasan Detik). Kosongkan untuk mengambil semua.")
            nama_file = st.text_input("4. Nama file", value="data_berita")
            fmt = st.selectbox("Format file", ["csv", "xlsx", "json"])

        with st.expander("Pengaturan lanjutan"):
            a1, a2, a3 = st.columns(3)
            max_pages = a1.number_input("Maks. halaman indeks per hari", 1, 100, 50)
            delay = a2.number_input("Jeda antar request (detik)", 0.5, 10.0, 1.0, step=0.5)
            max_articles = a3.number_input("Maks. jumlah artikel (0 = tanpa batas)", 0, 100000, 0)

        submitted = st.form_submit_button("Mulai scraping", type="primary")

    if not submitted:
        return
    rentang = valid_range(rentang)
    if rentang is None:
        return
    if not sources:
        st.error("Pilih minimal satu sumber.")
        return
    if "Detik" in sources and not detik_channels:
        st.error("Pilih minimal satu kanal Detik.")
        return

    start, end = rentang
    n_days = (end - start).days + 1
    if n_days > 31:
        st.warning(f"Rentang {n_days} hari akan memakan waktu lama. Pertimbangkan membaginya per bulan.")
    if "BMKG" in sources:
        st.info("BMKG khusus data gempa; feed publiknya hanya berisi ±15 gempa terbaru per feed. "
                "Data historis diminta lewat dataonline.bmkg.go.id.")

    out_path = OUTPUT_DIR / f"{safe_filename(nama_file)}.{fmt}"
    bar = st.progress(0.0)
    status = st.empty()
    table = st.empty()
    records = []

    for event in run(sources, start, end, keywords.split(","), detik_channels=detik_channels,
                     max_pages=int(max_pages), delay=float(delay), max_articles=int(max_articles)):
        if event[0] == "progress":
            _, frac, msg = event
            bar.progress(min(frac, 1.0))
            status.text(msg)
        else:
            records.append(event[1])
            df = pd.DataFrame(records, columns=COLUMNS)
            table.dataframe(df.drop(columns=["isi_teks"]).tail(10), width="stretch")
            if len(records) % 20 == 0:  # checkpoint supaya data aman kalau proses dihentikan
                save(df, out_path, fmt)

    table.empty()
    show_result(records, out_path, fmt, key="dl_berita")


# ============================================================================ tab tweet
def tab_tweet():
    mode = st.radio("Cara mengambil tweet", ["Ambil langsung (tweet-harvest)", "Upload CSV hasil tweet-harvest"],
                    horizontal=True)
    langsung = mode.startswith("Ambil")

    with st.form("form_tweet"):
        c1, c2 = st.columns(2)
        with c1:
            if langsung:
                saved_token = env_token()
                token = st.text_input(
                    "Auth token X" + (" (kosongkan untuk memakai token dari .env)" if saved_token else ""),
                    type="password",
                    help="Cookie `auth_token` dari x.com (F12 → Application → Cookies). "
                         "Bisa juga disimpan di file .env sebagai X_AUTH_TOKEN=...")
                if saved_token:
                    st.caption("✅ Token dari file .env terdeteksi.")
                today = date.today()
                rentang = st.date_input("Rentang waktu", value=(today - timedelta(days=7), today),
                                        max_value=today, format="DD/MM/YYYY", key="rentang_tweet")
            else:
                uploaded = st.file_uploader("File CSV dari tweet-harvest", type=["csv"])
            keywords = st.text_input("Keyword (pisahkan dengan koma)", value="", placeholder="contoh: pemilu, pilpres",
                                     key="kw_tweet",
                                     help="Mode langsung: dipakai sebagai query pencarian X (digabung OR). "
                                          "Mode upload: dipakai untuk menyaring tweet.")
        with c2:
            nama_file = st.text_input("Nama file", value="data_tweet", key="nama_tweet")
            fmt = st.selectbox("Format file", ["csv", "xlsx", "json"], key="fmt_tweet")
            if langsung:
                a1, a2 = st.columns(2)
                limit = a1.number_input("Maks. jumlah tweet", 10, 5000, 500, step=50)
                tab = a2.selectbox("Tab pencarian", ["LATEST", "TOP"])
                lang = a1.selectbox("Bahasa", ["id", "semua"])
                exclude_rt = a2.checkbox("Tanpa retweet", value=True)
                date_mode = st.selectbox(
                    "Metode filter tanggal", list(twitter.DATE_MODES),
                    help="Kalau hasil 0, coba metode lain. Sebagian akun X diblokir memakai filter tanggal; "
                         "pakai 'Tanpa filter tanggal' lalu jalankan rutin tiap hari.")
        append = st.checkbox("Gabungkan ke file yang sudah ada (duplikat dibuang)", value=False,
                             help="Berguna untuk mengumpulkan tweet sedikit demi sedikit, misalnya dijalankan tiap hari.")

        if langsung:
            with st.expander("Query lanjutan (opsional)"):
                custom_query = st.text_input(
                    "Query X manual (menimpa keyword di atas)",
                    placeholder='contoh: banjir (bekasi OR jakarta) lang:id -filter:retweets')
        submitted = st.form_submit_button("Mulai", type="primary")

    if not submitted:
        return
    out_name = safe_filename(nama_file, "data_tweet")
    out_path = OUTPUT_DIR / f"{out_name}.{fmt}"
    kw_list = [k.strip() for k in keywords.split(",") if k.strip()]

    if not langsung:
        if uploaded is None:
            st.error("Upload file CSV terlebih dahulu.")
            return
        try:
            records = twitter.process_csv(uploaded, kw_list)
        except ValueError as e:
            st.error(str(e))
            return
        show_result(records, out_path, fmt, key="dl_tweet", append=append)
        return

    token = token.strip() or saved_token
    if not token:
        st.error("Masukkan auth token X, atau isi X_AUTH_TOKEN di file .env.")
        return
    rentang = valid_range(rentang)
    if rentang is None:
        return
    query = custom_query.strip() or twitter.build_query(kw_list, "" if lang == "semua" else lang)
    if not query:
        st.error("Isi keyword atau query manual.")
        return
    start, end = rentang
    mode_code = twitter.DATE_MODES[date_mode]
    full_query = f"{query} {twitter.date_operators(start, end, mode_code)}".strip()
    if mode_code == "none":
        st.info("Tanpa filter tanggal, X hanya memberikan tweet TERBARU (biasanya beberapa hari ke belakang). "
                "Tweet di luar rentang tanggal akan dibuang. Untuk data jangka panjang, jalankan tiap hari "
                "dengan opsi 'Gabungkan ke file yang sudah ada'.")
    st.write(f"**Query:** `{full_query}`  ·  {start:%d-%m-%Y} s.d. {end:%d-%m-%Y}")
    st.caption("Tips: salin query di atas ke kotak pencarian x.com untuk mengecek apakah X menampilkan hasil.")
    st.caption("Run pertama akan mengunduh tweet-harvest dan Chromium (bisa beberapa menit). "
               "Jangan tutup tab ini selama proses berjalan.")

    raw_name = f"{out_name}_raw"
    log_box = st.empty()
    log = deque(maxlen=15)
    with st.spinner("tweet-harvest sedang berjalan..."):
        try:
            for line in twitter.harvest(token, query, start, end, int(limit), raw_name,
                                        RAW_TWEET_DIR, tab=tab, date_mode=mode_code):
                log.append(line)
                log_box.code("\n".join(log))
        except RuntimeError as e:
            st.error(str(e))
            return

    raw_path = twitter.find_output(RAW_TWEET_DIR, raw_name)
    if raw_path is None:
        log_path = RAW_TWEET_DIR / f"{raw_name}.log"
        full_log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        if "Invalid twitter auth token" in full_log:
            st.error("Auth token tidak valid atau kedaluwarsa. Login ulang di x.com lalu salin auth_token yang baru.")
        elif "rate limit" in full_log.lower():
            st.error("Kena rate limit X. Tunggu 15 menit atau lebih, lalu coba lagi dengan limit tweet yang lebih kecil.")
        elif "allOfTheseWords" in full_log:
            st.error("tweet-harvest gagal membuka form Advanced Search X. Kemungkinan token tidak valid, "
                     "atau tampilan X sudah berubah sehingga tweet-harvest perlu diperbarui.")
        else:
            st.error("tweet-harvest selesai tanpa tweet (0 data). Coba rentang waktu lebih panjang atau keyword lain.")
        with st.expander("Log lengkap tweet-harvest"):
            st.code(full_log or "(log kosong)")
        st.caption(f"Log tersimpan di: {log_path}")
        return
    st.caption(f"Data mentah: {raw_path}")
    # query X sudah menyaring keyword; saring ulang hanya kalau keyword bukan dari query manual
    try:
        records = twitter.process_csv(raw_path, [] if custom_query.strip() else kw_list, exclude_rt,
                                      start=start, end=end)
    except ValueError as e:
        st.error(str(e))
        return
    show_result(records, out_path, fmt, key="dl_tweet", append=append)


# ============================================================================ tab per topik
def tab_kejadian():
    st.caption("Mengumpulkan tweet ke file terpisah per topik. Nama topik yang Anda isi menjadi nama file: "
               "`data_tweet<NamaTopik>.csv`. Menjalankan ulang dengan nama yang sama akan menambah data ke file itu.")

    existing = sorted(OUTPUT_DIR.glob("data_tweet*.csv"))
    if existing:
        st.write("**File topik yang sudah ada:**")
        st.dataframe(pd.DataFrame({"file": [p.name for p in existing],
                                   "jumlah_data": [len(load_existing(p, "csv")) for p in existing]}),
                     width="stretch", hide_index=True)

    # Radio mode ditaruh DI LUAR form: form baru render ulang saat submit, jadi kalau radio ini
    # ada di dalam form, field "tahun"/"metode tanggal" (khusus mode bulanan) tidak akan sempat
    # terlihat sebelum form disubmit.
    mode = st.radio("Mode pengambilan", ["terbaru", "bulanan"], horizontal=True, key="mode_kejadian",
                    help="terbaru: tweet TERBARU tanpa filter tanggal (untuk semua akun). "
                         "bulanan: sebar per bulan selama N tahun, BUTUH akun yang bisa memakai "
                         "filter tanggal since:/until: di X.")

    with st.form("form_kejadian"):
        c1, c2 = st.columns(2)
        with c1:
            saved_token = env_token()
            token = st.text_input(
                "Auth token X" + (" (kosongkan untuk memakai token dari .env)" if saved_token else ""),
                type="password", key="token_kejadian",
                help="Cookie `auth_token` dari x.com. Bisa juga disimpan di file .env sebagai X_AUTH_TOKEN=...")
            if saved_token:
                st.caption("✅ Token dari file .env terdeteksi.")
            topik = st.text_input("Nama topik / file", placeholder="contoh: Pemilu, Banjir, Harga_BBM",
                                  help="Menjadi nama file hasil: data_tweet<NamaTopik>.csv")
            keywords = st.text_input("Keyword (pisahkan dengan koma)", key="kw_kejadian",
                                     placeholder="contoh: pemilu, pilpres",
                                     help="Digabung dengan OR di pencarian X. Kosong = pakai nama topik.")
            target = st.number_input("Target jumlah data", 100, 50000, 2000, step=100)
        with c2:
            if mode == "bulanan":
                tahun = st.number_input("Berapa tahun ke belakang", 1, 10, 5)
                date_mode_label = st.selectbox(
                    "Metode filter tanggal", list(twitter.DATE_MODES.keys())[1:],  # tanpa opsi "none"
                    help="Kalau hasil 0, coba metode lain.")
            lang = st.selectbox("Bahasa", ["id", "semua"], key="lang_kejadian")

        submitted = st.form_submit_button("Mulai kumpulkan", type="primary")

    if not submitted:
        return
    token = token.strip() or saved_token
    if not token:
        st.error("Masukkan auth token X, atau isi X_AUTH_TOKEN di file .env.")
        return
    if not topik.strip():
        st.error("Isi nama topik.")
        return
    event = safe_filename(topik, "topik")
    kw_list = [k.strip() for k in keywords.split(",") if k.strip()] or [topik.strip()]
    lang_code = "" if lang == "semua" else lang
    fmt = "csv"
    st.write(f"**Topik:** {event} · **Keyword:** {', '.join(kw_list)} · **File:** `{out_path(event, fmt).name}`")

    if mode == "bulanan":
        st.info("Sebelum lanjut: cek dulu di kotak pencarian x.com apakah query dengan filter tanggal "
                "menampilkan hasil untuk akun ini. Kalau tidak, pilih mode 'terbaru' saja.")
        months = months_back(int(tahun))
        per_run = math.ceil(target * 1.3 / len(months))
        date_mode = twitter.DATE_MODES[date_mode_label]
        progress = load_progress()

    overall = st.progress(0.0)
    status = st.empty()
    log_box = st.empty()
    summary = st.container()

    if mode == "terbaru":
        have = count_rows(event, fmt)
        if have >= target:
            status.text(f"[{event}] sudah {have} data (target {target}), dilewati.")
        else:
            limit = math.ceil((target - have) * 1.3)
            log = deque(maxlen=12)
            n_new = 0
            for item in run_once(token, event, kw_list, lang_code, limit, date.today(), date.today(),
                                 "none", f"raw_{event}_terbaru", fmt):
                if item[0] == "log":
                    log.append(item[1])
                    log_box.code("\n".join(log))
                else:
                    n_new = item[1]
            status.text(f"[{event}] +{n_new} baru, total {count_rows(event, fmt)}")
        overall.progress(1.0)

    else:  # bulanan
        done = set(progress.get(event, []))
        empty_streak = 0
        for step, (start, end) in enumerate(months, 1):
            key = f"{start:%Y-%m}"
            if key in done:
                overall.progress(step / len(months))
                continue
            status.text(f"[{event} {key}] mengambil ±{per_run} tweet...")
            raw_name = f"raw_{event}_{start:%Y%m}"
            log = deque(maxlen=12)
            n_new = 0
            for item in run_once(token, event, kw_list, lang_code, per_run, start, end,
                                 date_mode, raw_name, fmt):
                if item[0] == "log":
                    log.append(item[1])
                    log_box.code("\n".join(log))
                else:
                    n_new = item[1]
            overall.progress(step / len(months))
            empty_streak = empty_streak + 1 if n_new == 0 else 0
            if n_new > 0:
                done.add(key)
                progress[event] = sorted(done)
                PROGRESS_FILE.write_text(json.dumps(progress, indent=2), encoding="utf-8")
            if empty_streak >= 3:
                st.error("3 bulan berturut-turut 0 tweet. Kemungkinan filter tanggal diblokir untuk akun "
                         "ini atau kena rate limit. Bulan yang sudah selesai tidak akan diulang; "
                         "jalankan lagi nanti untuk melanjutkan.")
                break

    log_box.empty()
    status.empty()
    with summary:
        p = out_path(event, fmt)
        st.success(f"Proses selesai: {count_rows(event, fmt)} data di {p.name}")
        if p.exists():
            st.dataframe(load_existing(p, fmt).drop(columns=["isi_teks"]).tail(20), width="stretch")
            st.download_button(f"Unduh {p.name}", p.read_bytes(), file_name=p.name, key=f"dl_{event}")


# ============================================================================ halaman
st.set_page_config(page_title="Scraper Data", page_icon="🔎", layout="wide")
st.title("Scraper Data Berita & Tweet X")
st.caption("Kolom lokasi diisi otomatis berbasis aturan, jadi validasi manual tetap diperlukan.")

tab1, tab2, tab3 = st.tabs(["📰 Berita (Detik, Kompas, BMKG)", "🐦 Tweet X", "📦 Tweet per Topik"])
with tab1:
    tab_berita()
with tab2:
    tab_tweet()
with tab3:
    tab_kejadian()
