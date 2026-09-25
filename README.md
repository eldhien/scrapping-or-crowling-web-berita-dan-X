# Scraper Berita Bencana

Web sederhana (Streamlit) untuk mengumpulkan data penelitian bencana dari **detik.com**, **kompas.com**, dan **BMKG**.

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
| sumber | detik.com / kompas.com / bmkg (nama feed) |
| judul | Judul berita |
| isi_teks | Isi artikel yang sudah dibersihkan dari "Baca juga", iklan, dll. |
| lokasi | Lokasi kejadian (otomatis), contoh `Kabupaten Asahan, Sumatera Utara` |
| jenis_bencana | `gempa` / `banjir` / `longsor` / `-` |
| label | `bencana` / `bukan_bencana` |
| tingkat_keparahan | `tinggi` / `sedang` / `rendah` / `-` |
| keyword | Keyword yang cocok |
| url | Tautan artikel (untuk sitasi dan cek ulang) |

## Cara kerja

- **Detik & Kompas**: menelusuri **halaman indeks harian**. Pencarian Detik mengabaikan filter tanggal
  dan pencarian Kompas dirender dengan JavaScript, jadi indeks per tanggal lebih andal.
  Artikel yang judulnya cocok dengan keyword kemudian dibuka untuk mengambil isi lengkapnya.
- **BMKG**: memakai open data resmi (`data.bmkg.go.id/DataMKG/TEWS/*.json`).
  Feed ini **hanya memuat ±15 gempa terbaru**. Data historis harus diminta di https://dataonline.bmkg.go.id.

## Aturan pelabelan otomatis (`scraper/labeling.py`)

Label dibuat berbasis aturan (*weak labeling*), **bukan ground truth**:

- **jenis_bencana**: skor kata kunci (kemunculan di judul bobot 3, di isi bobot 1), diambil skor tertinggi.
- **label**: `bencana` jika ada ≥3 kata konteks kejadian (korban, BPBD, pengungsi, ketinggian air,
  magnitudo, dll.) dan tidak ada pemakaian kiasan ("banjir pesanan", "longsor suara", "gempa politik").
- **tingkat_keparahan**:
  - `tinggi`: ada korban tewas/hilang/tertimbun, atau magnitudo ≥ 6,5
  - `sedang`: ada pengungsi, kerusakan, luka, atau rumah terendam, atau magnitudo ≥ 5,5
  - `rendah`: selain itu

  Kalimat bernegasi ("tidak ada korban jiwa") diabaikan. Untuk BMKG, keparahan dihitung dari magnitudo dan skala MMI.
- **lokasi**: urutan prioritas: pola kejadian di judul ("Banjir Rendam Bekasi"), lalu "Kabupaten/Kota X" di isi,
  lalu desa/kecamatan, lalu dateline. Provinsi ditambahkan jika disebut.

> Untuk metodologi penelitian: validasi label secara manual pada sampel acak (misalnya 10–20%),
> laporkan akurasi atau Cohen's kappa, lalu koreksi label sebelum data dipakai untuk training.

## Tweet X (tab "Tweet X")

Memakai [tweet-harvest](https://github.com/helmisatria/tweet-harvest) v2.7.1. Butuh Node.js.

- **Ambil langsung**: isi *Auth token X*, yaitu nilai cookie `auth_token` dari x.com
  (F12 → Application → Cookies). Token hanya diteruskan ke proses tweet-harvest dan tidak disimpan ke file.
  Web dikunci ke `localhost` (lihat `.streamlit/config.toml`) supaya token tidak bisa dimasukkan dari perangkat lain.
- **Upload CSV**: untuk CSV yang dibuat dengan menjalankan tweet-harvest sendiri di terminal.
- Data mentah disimpan di `hasil/raw_tweets/tweets-data/`, data olahan di `hasil/<nama_file>`.
- Kolom `judul` berisi `@username`. Retweet dibuang, dan slang ("bjir", "rmh", "ngungsi") dinormalisasi hanya untuk pelabelan.
  Label tweet cukup butuh 1 kata konteks, karena tweet jauh lebih pendek dari artikel berita.
- Pakai **akun cadangan**. Scraping X melanggar ToS X dan akun bisa dibatasi.

### Token di file `.env` & pengambilan rutin

- Isi `X_AUTH_TOKEN=...` di file `.env`. Web akan memakainya kalau kolom token dikosongkan.
  File `.env` sudah masuk `.gitignore`.
- Tanpa web: `python ambil_tweet.py --keyword "gempa, banjir, longsor" --hari 3 --limit 500 --nama data_tweet`
  mengambil tweet terbaru dan menggabungkannya ke `hasil/data_tweet.csv` (duplikat dibuang).
- `jalankan_harian.bat` memanggil skrip tersebut dan mencatat output ke `hasil/jadwal.log`.
  File ini bisa didaftarkan ke Windows Task Scheduler supaya berjalan otomatis setiap hari.

## Etika scraping

- Ada jeda antar request (default 1 detik, bisa diatur) dan User-Agent yang jelas.
- Gunakan hanya untuk penelitian, cantumkan sumber, dan jangan menyebarkan ulang teks berita secara utuh.
- Rentang waktu panjang (lebih dari 1 bulan) sebaiknya dijalankan per bulan.
  Satu hari Kompas bisa berisi lebih dari 30 halaman indeks.
