# Scraper Berita & Tweet X

Web sederhana (Streamlit) untuk mengumpulkan data penelitian untuk **topik apa saja** dari
**detik.com**, **kompas.com**, **tweet X**, dan (opsional) **BMKG**. Hasil disimpan ke folder `hasil/`
sesuai nama file/topik yang Anda isi.

## 1. Persiapan (sekali saja)

| Kebutuhan | Cek / pasang |
|---|---|
| Python 3.10+ | `python --version` |
| Node.js (untuk tweet X) | `node --version` dan `npx --version`. Unduh di https://nodejs.org jika belum ada |
| Dependensi Python | `pip install -r requirements.txt` (jalankan di folder proyek) |

Run pertama untuk tweet akan mengunduh `tweet-harvest` dan Chromium otomatis (bisa beberapa menit).

## 2. Menjalankan web

Buka terminal di folder proyek, lalu:

```bash
streamlit run app.py
```

Buka http://localhost:8501 di browser (jika tidak terbuka otomatis). Web hanya bisa diakses dari
laptop ini (lihat `.streamlit/config.toml`) agar token tidak bisa dimasukkan dari perangkat lain.
Hentikan dengan `Ctrl + C` di terminal.

## 3. Mendapatkan Auth Token X

Token dibutuhkan untuk semua fitur tweet. Token adalah nilai cookie `auth_token` dari akun X yang sedang login.

1. Buka https://x.com di Chrome/Edge dan **login** (disarankan akun cadangan, bukan akun utama).
2. Tekan **F12** untuk membuka DevTools.
3. Buka tab **Application** (di Firefox: **Storage**). Jika tab tidak terlihat, klik `»` di sisi kanan.
4. Di panel kiri pilih **Cookies** → `https://x.com`.
5. Cari baris bernama **`auth_token`**, lalu salin isi kolom **Value** (±40 karakter hex).
6. Pakai token dengan salah satu cara:
   - **Ketik di web**: tempel ke kolom *Auth token X* pada tab tweet. Hanya berlaku untuk sesi itu.
   - **Simpan di `.env`** (disarankan): salin `.env.example` menjadi `.env`, lalu isi
     ```
     X_AUTH_TOKEN=isi_token_anda_di_sini
     ```
     Web otomatis memakainya jika kolom token dikosongkan, dan CLI selalu memakainya.
     File `.env` sudah masuk `.gitignore`, jangan dibagikan atau di-commit.

Catatan token:
- Token **kedaluwarsa** jika Anda logout, ganti password, atau X mereset sesi. Jika muncul
  "Invalid twitter auth token", ulangi langkah di atas.
- Jangan bagikan token: siapa pun yang memegangnya bisa masuk ke akun Anda.
- Scraping X melanggar ToS X dan akun bisa dibatasi. Pakai **akun cadangan**.

## 4. Memakai web

Web punya tiga tab.

### Tab "Berita (Detik, Kompas, BMKG)" (tanpa token)

1. Pilih **Sumber** (Detik, Kompas, BMKG) dan kanal Detik.
2. Pilih **Rentang waktu**.
3. Isi **Keyword** dipisah koma (dicocokkan ke judul dan ringkasan). Kosongkan untuk mengambil semua.
4. Isi **Nama file** dan pilih format (csv / xlsx / json), lalu klik **Mulai scraping**.

### Tab "Tweet X"

1. Pilih cara: **Ambil langsung** (butuh token) atau **Upload CSV** hasil tweet-harvest.
2. Isi token (atau kosongkan jika sudah ada di `.env`), **keyword** dipisah koma, dan **nama file**.
3. Atur rentang waktu, jumlah maksimal tweet, bahasa, dan metode filter tanggal.
4. Klik **Mulai**. Hasil tersimpan ke `hasil/<nama_file>.<format>` dan data mentah ke `hasil/raw_tweets/`.

Opsi "Gabungkan ke file yang sudah ada" menambah data ke file lama dan membuang duplikat.
Opsi "Query lanjutan" memungkinkan query X manual, contoh: `banjir (bekasi OR jakarta) lang:id`.

### Tab "Tweet per Topik"

Mengumpulkan tweet ke file per topik: isi **Nama topik** (misal `Pemilu`) dan keyword, hasil masuk
ke `hasil/data_tweetPemilu.csv`. Menjalankan ulang dengan nama sama akan menambah data.

> **Penting: batas rentang tanggal.** Pada pengujian, pencarian X dengan akun yang dipakai hanya
> mengembalikan tweet dari beberapa hari terakhir. Rentang yang berakhir di masa lalu (misal
> `until` seminggu lalu) menghasilkan **0 tweet** walau query-nya valid, sedangkan rentang yang
> berakhir **hari ini** berhasil. Karena itu:
> - set tanggal akhir ke **hari ini**, atau pilih "Tanpa filter tanggal";
> - untuk data jangka panjang, jalankan rutin tiap hari dengan opsi "Gabungkan ke file yang sudah ada";
> - mode "bulanan" kemungkinan besar kosong untuk akun seperti ini.

## 5. Memakai lewat terminal (tanpa web)

Semua perintah memakai token dari `.env`.

```bash
# satu topik, ambil tweet terbaru lalu gabung ke hasil/data_tweet.csv
python ambil_tweet.py --keyword "pemilu, pilpres" --hari 3 --limit 500 --nama data_tweet

# kumpulkan sampai target per topik -> hasil/data_tweetPemilu.csv
python kumpul_per_kejadian.py --topik Pemilu --keyword "pemilu, pilpres" --target 2000
```

`jalankan_harian.bat` memanggil `ambil_tweet.py` dan mencatat output ke `hasil/jadwal.log`.
Ganti `GANTI_KEYWORD_ANDA` di dalamnya, lalu daftarkan ke Windows Task Scheduler agar jalan tiap hari.

## Kolom output

| Kolom | Isi |
|---|---|
| tanggal | Waktu terbit (WIB), `YYYY-MM-DD HH:MM:SS` |
| sumber | detik.com / kompas.com / x.com / bmkg (nama feed) |
| judul | Judul berita (untuk tweet: `@username`) |
| isi_teks | Isi artikel yang sudah dibersihkan dari "Baca juga", iklan, dll. |
| lokasi | Lokasi yang terdeteksi otomatis, contoh `Kabupaten Asahan, Sumatera Utara` (bisa kosong) |
| keyword | Keyword yang cocok |
| url | Tautan artikel/tweet (untuk sitasi dan cek ulang) |

## Cara kerja

- **Detik & Kompas**: menelusuri halaman indeks harian (pencarian Detik mengabaikan filter tanggal dan
  pencarian Kompas dirender dengan JavaScript). Artikel yang judulnya cocok dengan keyword dibuka untuk
  mengambil isi lengkapnya.
- **Tweet X**: memakai [tweet-harvest](https://github.com/helmisatria/tweet-harvest) v2.7.1. Retweet dibuang,
  dan slang umum ("yg", "gak", "udh") dinormalisasi hanya untuk deteksi lokasi.
- **BMKG** (opsional, khusus gempa): open data resmi `data.bmkg.go.id/DataMKG/TEWS/*.json`. Feed hanya
  memuat ±15 gempa terbaru; data historis diminta di https://dataonline.bmkg.go.id.
- **lokasi**: deteksi berbasis aturan ("Kabupaten/Kota X" di judul/isi, lalu desa/kecamatan, lalu dateline;
  provinsi ditambahkan jika disebut). Ini tebakan awal, validasi manual tetap diperlukan.

## Pemecahan masalah

| Gejala | Penyebab / solusi |
|---|---|
| `npx tidak ditemukan` | Pasang Node.js lalu buka terminal baru |
| "Auth token tidak valid" | Token kedaluwarsa. Ambil token baru (bagian 3) |
| Hasil 0 tweet | Cek tanggal akhir (lihat catatan penting di atas), coba "Tanpa filter tanggal", atau cek query yang sama di kotak pencarian x.com |
| Kena rate limit | Tunggu ≥15 menit, kecilkan jumlah tweet |
| Log lengkap | `hasil/raw_tweets/<nama>_raw.log` |

## Etika scraping

- Ada jeda antar request (default 1 detik, bisa diatur) dan User-Agent yang jelas.
- Gunakan hanya untuk penelitian, cantumkan sumber, dan jangan menyebarkan ulang teks berita secara utuh.
- Rentang waktu panjang (lebih dari 1 bulan) sebaiknya dijalankan per bulan.
  Satu hari Kompas bisa berisi lebih dari 30 halaman indeks.
