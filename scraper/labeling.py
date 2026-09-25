"""Pelabelan otomatis berbasis aturan (rule-based / weak labeling).

Hasilnya adalah LABEL AWAL, bukan ground truth. Untuk data penelitian, label wajib
divalidasi manual (misalnya cek sampel acak lalu hitung akurasi/Cohen's kappa).
"""
import re

# --------------------------------------------------------------------------- jenis bencana
JENIS = {
    "gempa": ["gempa", "gempa bumi", "lindu", "magnitudo", "guncangan gempa", "episentrum"],
    "banjir": ["banjir", "banjir bandang", "banjir rob", "rob", "terendam", "genangan air", "luapan", "meluap"],
    "longsor": ["longsor", "tanah longsor", "tanah bergerak", "pergerakan tanah", "longsoran", "tertimbun"],
}
_JENIS_RE = {
    jenis: re.compile(r"\b(?:" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) + r")\b", re.I)
    for jenis, words in JENIS.items()
}

# Pemakaian kiasan: "banjir pesanan", "gempa politik", "longsor suara", dst.
KIASAN = {
    "banjir": ["pesanan", "order", "orderan", "diskon", "promo", "kritik", "hujatan", "pujian", "komentar",
               "dukungan", "penonton", "pengunjung", "air mata", "rezeki", "hadiah", "bonus", "gol", "tawaran",
               "peminat", "pembeli", "investor", "sponsor", "ucapan", "doa", "apresiasi", "medali", "cuan",
               "like", "job", "bintang", "penumpang", "wisatawan", "pelamar", "sanjungan"],
    "gempa": ["politik", "bursa", "pasar", "transfer", "susunan", "kabinet"],
    "longsor": ["suara", "harga", "saham", "rupiah", "elektabilitas", "ihsg", "popularitas", "nilai tukar",
                "penjualan", "kemenangan"],
}
_KIASAN_RE = re.compile(
    "|".join(
        rf"\b{jenis}\s+(?:\w+\s+)?(?:{'|'.join(re.escape(k) for k in kata)})\b"
        for jenis, kata in KIASAN.items()
    ),
    re.I,
)

# Kata konteks yang menandakan kejadian bencana nyata
KONTEKS = ["korban", "warga", "pengungsi", "mengungsi", "evakuasi", "bpbd", "bnpb", "basarnas", "tim sar",
           "bmkg", "rumah", "ketinggian air", "hujan deras", "intensitas hujan", "kedalaman", "pusat gempa",
           "rusak", "kerusakan", "tewas", "meninggal", "hilang", "tertimbun", "luka", "jembatan", "tanggul",
           "sungai", "desa", "kecamatan", "kelurahan", "terdampak", "posko", "bantuan", "tanggap darurat",
           "lintang", "bujur", "skala", "longsoran", "material", "lumpur", "surut"]
_KONTEKS_RE = re.compile(r"\b(?:" + "|".join(re.escape(k) for k in KONTEKS) + r")\b", re.I)

# --------------------------------------------------------------------------- keparahan
_TINGGI_RE = re.compile(
    r"\b(?:tewas|meninggal(?: dunia)?|korban jiwa|hilang|tertimbun|jenazah|korban meninggal|"
    r"status tanggap darurat|ribuan (?:warga|rumah|jiwa)|berpotensi tsunami)\b", re.I)
_SEDANG_RE = re.compile(
    r"\b(?:mengungsi|pengungsi|rusak|kerusakan|luka|terluka|terendam|ambruk|roboh|ambles|terputus|putus|"
    r"lumpuh|terisolasi|hanyut|jebol|puluhan rumah|ratusan rumah)\b", re.I)
_NEGASI_RE = re.compile(r"\b(?:tidak|tak|belum|nihil|tanpa|bukan)\b", re.I)
_MAGNITUDO_RE = re.compile(r"(?:magnitudo|\bM)\s*(?:\(M\)\s*)?(\d+(?:[.,]\d+)?)", re.I)

# --------------------------------------------------------------------------- lokasi
PROVINSI = [
    "Aceh", "Sumatera Utara", "Sumatera Barat", "Riau", "Kepulauan Riau", "Jambi", "Bengkulu", "Sumatera Selatan",
    "Kepulauan Bangka Belitung", "Lampung", "Banten", "DKI Jakarta", "Jawa Barat", "Jawa Tengah", "DI Yogyakarta",
    "Jawa Timur", "Bali", "Nusa Tenggara Barat", "Nusa Tenggara Timur", "Kalimantan Barat", "Kalimantan Tengah",
    "Kalimantan Selatan", "Kalimantan Timur", "Kalimantan Utara", "Sulawesi Utara", "Gorontalo", "Sulawesi Tengah",
    "Sulawesi Barat", "Sulawesi Selatan", "Sulawesi Tenggara", "Maluku", "Maluku Utara", "Papua", "Papua Barat",
    "Papua Barat Daya", "Papua Tengah", "Papua Pegunungan", "Papua Selatan",
]
ALIAS_PROVINSI = {
    "Jatim": "Jawa Timur", "Jabar": "Jawa Barat", "Jateng": "Jawa Tengah", "DIY": "DI Yogyakarta",
    "Yogyakarta": "DI Yogyakarta", "Jogja": "DI Yogyakarta", "Jakarta": "DKI Jakarta", "NTB": "Nusa Tenggara Barat",
    "NTT": "Nusa Tenggara Timur", "Sumut": "Sumatera Utara", "Sumbar": "Sumatera Barat",
    "Sumsel": "Sumatera Selatan", "Kalbar": "Kalimantan Barat", "Kalteng": "Kalimantan Tengah",
    "Kalsel": "Kalimantan Selatan", "Kaltim": "Kalimantan Timur", "Kaltara": "Kalimantan Utara",
    "Sulut": "Sulawesi Utara", "Sulteng": "Sulawesi Tengah", "Sulsel": "Sulawesi Selatan",
    "Sultra": "Sulawesi Tenggara", "Sulbar": "Sulawesi Barat", "Malut": "Maluku Utara", "Kepri": "Kepulauan Riau",
    "Babel": "Kepulauan Bangka Belitung", "Bangka Belitung": "Kepulauan Bangka Belitung",
}
_PROV_NAMES = {p: p for p in PROVINSI} | ALIAS_PROVINSI
_PROV_RE = re.compile(r"\b(" + "|".join(re.escape(n) for n in sorted(_PROV_NAMES, key=len, reverse=True)) + r")\b")

_WORD = r"[A-Z][\w'\-]+"
_WILAYAH_RE = re.compile(rf"\b(Kabupaten|Kab\.|Kota)\s+({_WORD}(?:\s+{_WORD}){{0,2}})")
_DESA_RE = re.compile(rf"\b(Kecamatan|Kec\.|Desa|Kelurahan|Dusun)\s+({_WORD}(?:\s+{_WORD}){{0,2}})")
_KEJADIAN_RE = re.compile(
    r"(?i:\b(?:gempa|banjir|longsor|rob)\b)[^.\n]{0,80}?"
    r"\b(?i:di|guncang|mengguncang|landa|melanda|terjang|menerjang|rendam|merendam|hantam|menghantam|"
    r"timbun|menimbun|kepung|mengepung|terjadi di)\s+"
    rf"((?:Kabupaten|Kab\.|Kota)\s+)?({_WORD}(?:\s+{_WORD}){{0,2}})"
)
_DATELINE_RE = re.compile(r"^\s*([A-Z][A-Za-z .]{2,30}?)\s*(?:,\s*KOMPAS\.com|\s+-\s)")

# Kata ber-huruf kapital yang bukan nama tempat (sering muncul di judul Title Case)
STOP = {
    "Warga", "Rumah", "Ratusan", "Puluhan", "Ribuan", "Hari", "Ini", "Itu", "Jalan", "Dan", "Akibat", "Sejak",
    "Pagi", "Siang", "Sore", "Malam", "Dini", "BPBD", "BNPB", "BMKG", "Tim", "SAR", "Korban", "Orang", "Tewas",
    "Meninggal", "Hilang", "Mengungsi", "Terendam", "Rusak", "Lagi", "Kembali", "Hingga", "Sampai", "Usai", "Saat",
    "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu", "Januari", "Februari", "Maret", "April",
    "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember", "Magnitudo", "Berikut",
    "Begini", "Ada", "Tak", "Tidak", "Terkini", "Waspada", "Potensi", "Status", "Jiwa", "Kepala", "Pemkab",
    "Pemkot", "Pemprov", "Sekolah", "Kantor", "Kampus", "Lokasi", "Sekitar", "Tempat", "Area", "Gempa", "Banjir", "Longsor", "Wilayah", "Daerah", "Kawasan", "Sejumlah", "Beberapa",
}


def _trim_place(name):
    words = []
    for w in name.split():
        if w in STOP:
            break
        words.append(w)
    return " ".join(words)


def _first_place(regex, text):
    """Tempat pertama yang cocok: group(1) = awalan (Kabupaten/Kota/Desa..., boleh kosong), group(2) = nama."""
    for m in regex.finditer(text):
        place = _trim_place(m.group(2))
        if place:
            place = _PROV_NAMES.get(place, place)  # "Jateng" -> "Jawa Tengah"
            return " ".join(f"{m.group(1) or ''} {place}".replace("Kab. ", "Kabupaten ").split())
    return ""


def _detect_provinsi(text, place):
    """Provinsi yang disebut tepat setelah nama tempat ("Kabupaten Asahan, Sumatera Utara"),
    jika tidak ada pakai provinsi yang paling sering disebut."""
    name = place.split()[-1] if place else ""
    if name:
        for m in re.finditer(re.escape(name), text):
            near = _PROV_RE.search(text, m.end(), m.end() + 60)
            if near:
                return _PROV_NAMES[near.group(1)]
    counts = {}
    for m in _PROV_RE.finditer(text):
        prov = _PROV_NAMES[m.group(1)]
        counts[prov] = counts.get(prov, 0) + 1
    return max(counts, key=counts.get) if counts else ""  # dict terurut -> seri dimenangkan yang muncul duluan


def detect_lokasi(judul, isi):
    text = f"{judul}\n{isi}"
    # Urutan prioritas: pola kejadian di judul > Kabupaten/Kota di isi > pola kejadian di isi > desa/kecamatan
    place = (
        _first_place(_KEJADIAN_RE, judul)
        or _first_place(_WILAYAH_RE, isi)
        or _first_place(_KEJADIAN_RE, isi)
        or _first_place(_DESA_RE, isi)
    )
    provinsi = _detect_provinsi(text, place)

    if not place:
        dl = _DATELINE_RE.match(isi)
        if dl:
            place = dl.group(1).strip().title()
    if not place:
        return provinsi
    if provinsi and provinsi.lower() not in place.lower():
        return f"{place}, {provinsi}"
    return place


# --------------------------------------------------------------------------- klasifikasi
def detect_jenis(judul, isi):
    scores = {j: 3 * len(r.findall(judul)) + len(r.findall(isi)) for j, r in _JENIS_RE.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "-"


def detect_label(judul, isi, jenis, min_konteks=3):
    """min_konteks = jumlah minimal kata konteks kejadian (3 untuk berita, 1 untuk tweet yang pendek)."""
    if jenis == "-":
        return "bukan_bencana"
    kiasan_judul = bool(_KIASAN_RE.search(judul))
    kiasan_isi = len(_KIASAN_RE.findall(isi))
    konteks = len(set(m.lower() for m in _KONTEKS_RE.findall(f"{judul} {isi}")))
    if kiasan_judul or (kiasan_isi and konteks < min_konteks + 1):
        return "bukan_bencana"
    return "bencana" if konteks >= min_konteks else "bukan_bencana"


def detect_keparahan(judul, isi, label):
    if label != "bencana":
        return "-"
    # kalimat bernegasi ("tidak ada korban jiwa") diabaikan
    kalimat = [k for k in re.split(r"(?<=[.!?])\s+|\n", f"{judul}.\n{isi}") if not _NEGASI_RE.search(k)]
    teks = " ".join(kalimat)
    mags = []
    for m in _MAGNITUDO_RE.findall(f"{judul} {isi}"):
        try:
            v = float(m.replace(",", "."))
            if 1 <= v <= 10:
                mags.append(v)
        except ValueError:
            pass
    mag = max(mags, default=0)
    if _TINGGI_RE.search(teks) or mag >= 6.5:
        return "tinggi"
    if _SEDANG_RE.search(teks) or mag >= 5.5:
        return "sedang"
    return "rendah"


def enrich(record):
    """Tambahkan kolom lokasi, jenis_bencana, label, tingkat_keparahan ke record artikel berita."""
    judul, isi = record["judul"], record["isi_teks"]
    jenis = detect_jenis(judul, isi)
    label = detect_label(judul, isi, jenis)
    record["lokasi"] = detect_lokasi(judul, isi)
    record["jenis_bencana"] = jenis
    record["label"] = label
    record["tingkat_keparahan"] = detect_keparahan(judul, isi, label)
    return record
