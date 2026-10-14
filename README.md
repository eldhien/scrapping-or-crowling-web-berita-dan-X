# Scraper Berita & Tweet X

Web sederhana (Streamlit) untuk mengumpulkan data penelitian untuk topik apa saja dari **detik.com**, **kompas.com**, **tweet X**, dan (opsional) **BMKG**.

## Cara menjalankan

```bash
pip install -r requirements.txt
streamlit run app.py
```

Browser akan terbuka di http://localhost:8501.

## Input

1. **Sumber**: Detik (bisa pilih kanal regional), Kompas, BMKG
2. **Rentang waktu**: tanggal mulai sampai tanggal akhir
3. **Keyword**: dipisah koma, dicocokkan ke judul (dan ringkasan Detik)
4. **Nama file**: hasil disimpan di folder `hasil/` sebagai CSV, XLSX, atau JSON

## Kolom output

| Kolom | Isi |
|---|---|
| tanggal | Waktu terbit (WIB), `YYYY-MM-DD HH:MM:SS` |
| sumber | detik.com / kompas.com / x.com / bmkg (nama feed) |
| judul | Judul berita (untuk tweet: `@username`) |
| isi_teks | Isi artikel yang sudah dibersihkan dari "Baca juga", iklan, dll. |
| lokasi | Lokasi yang terdeteksi otomatis, contoh `Kabupaten Asahan, Sumatera Utara` (bisa kosong) |
| keyword | Keyword yang cocok |
| url | Tautan artikel (untuk sitasi dan cek ulang) |

## Cara kerja

- **Detik & Kompas**: menelusuri **halaman indeks harian**. Pencarian Detik mengabaikan filter tanggal
  dan pencarian Kompas dirender dengan JavaScript, jadi indeks per tanggal lebih andal.
  Artikel yang judulnya cocok dengan keyword kemudian dibuka untuk mengambil isi lengkapnya.
- **BMKG** (opsional, khusus gempa): memakai open data resmi (`data.bmkg.go.id/DataMKG/TEWS/*.json`).
  Feed ini **hanya memuat ±15 gempa terbaru**. Data historis harus diminta di https://dataonline.bmkg.go.id.
- **lokasi**: deteksi berbasis aturan ("Kabupaten/Kota X" di judul/isi, lalu desa/kecamatan, lalu dateline;
  provinsi ditambahkan jika disebut). Ini tebakan awal, validasi manual tetap diperlukan.

## Tweet X (tab "Tweet X")

Memakai [tweet-harvest](https://github.com/helmisatria/tweet-harvest) v2.7.1. Butuh Node.js.

- **Ambil langsung**: isi *Auth token X*, yaitu nilai cookie `auth_token` dari x.com
  (F12 → Application → Cookies). Token hanya diteruskan ke proses tweet-harvest dan tidak disimpan ke file.
  Web dikunci ke `localhost` (lihat `.streamlit/config.toml`) supaya token tidak bisa dimasukkan dari perangkat lain.
- **Upload CSV**: untuk CSV yang dibuat dengan menjalankan tweet-harvest sendiri di terminal.
- Data mentah disimpan di `hasil/raw_tweets/tweets-data/`, data olahan di `hasil/<nama_file>`.
- Kolom `judul` berisi `@username`. Retweet dibuang, dan slang umum ("yg", "gak", "udh") dinormalisasi hanya untuk deteksi lokasi.
- **Tab "Pengaturan Scraping"**: isi X Auth Token, kata kunci, jumlah tweet, nama file, tanggal mulai/akhir (opsional), dan format. Hasil disimpan ke `hasil/<nama_file>.<format>` dengan kolom umum: `tanggal, username, isi_teks, keyword, suka, retweet, balasan, url`.
- Via terminal: `python kumpul_per_kejadian.py --keyword "jakarta" --jumlah 1000 --nama jakarta --mulai 2025-10-08`.
- Pakai **akun cadangan**. Scraping X melanggar ToS X dan akun bisa dibatasi.

### Token di file `.env` & pengambilan rutin

- Isi `X_AUTH_TOKEN=...` di file `.env`. Web akan memakainya kalau kolom token dikosongkan.
  File `.env` sudah masuk `.gitignore`.
- Tanpa web: `python ambil_tweet.py --keyword "pemilu, pilpres" --hari 3 --limit 500 --nama data_tweet`
  mengambil tweet terbaru dan menggabungkannya ke `hasil/data_tweet.csv` (duplikat dibuang).
- `jalankan_harian.bat` memanggil skrip tersebut (ganti `GANTI_KEYWORD_ANDA` dengan keyword Anda) dan mencatat output ke `hasil/jadwal.log`.
  File ini bisa didaftarkan ke Windows Task Scheduler supaya berjalan otomatis setiap hari.

## Etika scraping

- Ada jeda antar request (default 1 detik, bisa diatur) dan User-Agent yang jelas.
- Gunakan hanya untuk penelitian, cantumkan sumber, dan jangan menyebarkan ulang teks berita secara utuh.
- Rentang waktu panjang (lebih dari 1 bulan) sebaiknya dijalankan per bulan.
  Satu hari Kompas bisa berisi lebih dari 30 halaman indeks.
