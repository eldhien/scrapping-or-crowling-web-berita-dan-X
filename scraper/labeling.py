"""Deteksi lokasi otomatis berbasis aturan (umum, tidak terikat topik).

Hasilnya adalah tebakan awal, bukan ground truth: validasi manual tetap diperlukan.
"""
import re

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
_DATELINE_RE = re.compile(r"^\s*([A-Z][A-Za-z .]{2,30}?)\s*(?:,\s*KOMPAS\.com|\s+-\s)")

# Kata ber-huruf kapital yang bukan nama tempat (sering muncul di judul Title Case)
STOP = {
    "Warga", "Rumah", "Ratusan", "Puluhan", "Ribuan", "Hari", "Ini", "Itu", "Jalan", "Dan", "Akibat", "Sejak",
    "Pagi", "Siang", "Sore", "Malam", "Dini", "BPBD", "BNPB", "BMKG", "Tim", "SAR", "Korban", "Orang", "Tewas",
    "Meninggal", "Hilang", "Mengungsi", "Terendam", "Rusak", "Lagi", "Kembali", "Hingga", "Sampai", "Usai", "Saat",
    "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu", "Januari", "Februari", "Maret", "April",
    "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember", "Magnitudo", "Berikut",
    "Begini", "Ada", "Tak", "Tidak", "Terkini", "Waspada", "Potensi", "Status", "Jiwa", "Kepala", "Pemkab",
    "Pemkot", "Pemprov", "Sekolah", "Kantor", "Kampus", "Lokasi", "Sekitar", "Tempat", "Area", "Wilayah", "Daerah", "Kawasan", "Sejumlah", "Beberapa",
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
    # Urutan prioritas: Kabupaten/Kota di judul > di isi > desa/kecamatan > dateline
    place = (
        _first_place(_WILAYAH_RE, judul)
        or _first_place(_WILAYAH_RE, isi)
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


