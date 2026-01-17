import re

normalizad_word_dict = {
    "sim": "sim", "siakad": "sim", "sikd": "sim", "siakd": "sim","siakad": "siakad", "sikd": "siakad", "portal": "siakad", "sim": "siakad", 
    "sita": "sita", "elma": "elma", "lptik": "lptik", "unipma": "unipma", 
    "unima": "unipma", "kampus": "kampus", "universitas": "kampus",
    "graha": "graha", "cendekia": "cendekia", "ulul": "ulul", "albab": "albab", 
    "rektorat": "rektorat",

    "krs": "krs", "krsan": "krs", "sks": "sks", "matkul": "mata kuliah", 
    "mk": "mata kuliah", "mtkul": "mata kuliah", "mtul": "mata kuliah",
    "kuliah": "kuliah", "kuliya": "kuliah", "kuliyah": "kuliah", "kulaih": "kuliah", 
    "prkuliahan": "kuliah", "jadwal": "jadwal", "jdwl": "jadwal", "jadual": "jadwal", 
    "jdwal": "jadwal", "jawal": "jadwal", "ujian": "ujian", "ujina": "ujian", 
    "uijan": "ujian", "ujisn": "ujian", "ujin": "ujian", "tes": "ujian",
    "uts": "uts", "uas": "uas", "semester": "semester", "smt": "semester", 
    "smster": "semester", "smester": "semester", "smstr": "semester",
    "ganjil": "ganjil", "genap": "genap", "maba": "mahasiswa baru", 
    "kating": "kakak tingkat",

    "skripsi": "skripsi", "skrpsi": "skripsi", "skrispi": "skripsi", 
    "ta": "skripsi", "judul": "judul", "jdul": "judul", "outline": "outline", 
    "outlene": "outline", "outlen": "outline", "dospem": "dosen pembimbing", 
    "pembimbing": "dosen pembimbing", "dosbing": "dosen pembimbing", "dsen": "dosen",
    "sempro": "seminar proposal", "sidang": "sidang", "pendadaran": "sidang",
    "wisuda": "wisuda", "yudisium": "wisuda", "yidisium": "wisuda", "toga": "toga",
    "ijazah": "ijazah", "ijasah": "ijazah", "legalisir": "legalisir", 
    "lgalisir": "legalisir", "kp": "kerja praktik", "magang": "kerja praktik", 
    "pkl": "kerja praktik", "praktek": "kerja praktik", "toefl": "toefl", 
    "elpt": "toefl", "tofel": "toefl", "skor": "skor", "scor": "skor",

    "bayar": "bayar", "byar": "bayar", "pembayaran": "bayar", "pmbyaran": "bayar", 
    "tf": "bayar", "transfer": "bayar", "biaya": "biaya", "biya": "biaya", 
    "tarif": "biaya", "harga": "biaya", "nominal": "biaya", "ukt": "ukt", 
    "spp": "ukt", "tagihan": "tagihan", "tgihan": "tagihan", "tunggakan": "tunggakan", 
    "nunggak": "tunggakan", "lunas": "lunas", "lnas": "lunas", "dispensasi": "dispensasi", 
    "dispen": "dispensasi", "keringanan": "dispensasi", "beasiswa": "beasiswa", 
    "besiswa": "beasiswa", "kipk": "kip-k", "kip-k": "kip-k", "pndaftaran": "daftar",
    "potongan": "potongan", "ptongan": "potongan", "diskon": "potongan", 
    "cashback": "potongan",

    "surat": "surat", "srat": "surat", "aktif": "aktif", "akrif": "aktif",
    "cuti": "cuti", "cti": "cuti", "off": "cuti", "berhenti": "cuti", 
    "brenti": "cuti", "stop": "cuti", "pindah": "pindah", "pndah": "pindah", 
    "mutasi": "pindah", "ganti": "ganti", "revisi": "ganti", "ubah": "ganti",
    "prodi": "prodi", "jurusan": "prodi", "prdi": "prodi", "fakultas": "fakultas",
    "baak": "baa", "baa": "baa", "tu": "tu", "tata usaha": "tu",
    "wifi": "wifi", "wfi": "wifi", "internet": "wifi", "hotspot": "hotspot", 
    "hospot": "hotspot", "password": "password", "pasword": "password", 
    "pw": "password", "sandi": "password", "reset": "reset",
    "perpus": "perpustakaan", "perpstakaan": "perpustakaan", "pustaka": "perpustakaan", 
    "buku": "buku", "masjid": "masjid", "msjid": "masjid", "mushola": "mushola", 
    "mshola": "mushola", "sholat": "sholat", "kantin": "kantin", "makan": "makan", 
    "laper": "makan", "foodcourt": "kantin",

    "kapan": "kapan", "kpn": "kapan", "kpan": "kapan", "tgl": "tanggal", 
    "tanggal": "tanggal", "mana": "mana", "dmn": "dimana", "dimana": "dimana", 
    "dmna": "dimana", "bagaimana": "bagaimana", "gmn": "bagaimana", 
    "gmna": "bagaimana", "gimana": "bagaimana", "apa": "apa", "ap": "apa", 
    "apakah": "apa", "apkh": "apa", "berapa": "berapa", "brp": "berapa", 
    "brpa": "berapa", "brapa": "berapa", "siapa": "siapa", "sapa": "siapa", 
    "syapa": "siapa", "syarat": "syarat", "syrat": "syarat", "sarat": "syarat", 
    "persyaratan": "syarat", "dokumen": "dokumen", "berkas": "dokumen", 
    "dkumen": "dokumen", "file": "dokumen", "info": "info", "inpo": "info", 
    "informasi": "info", "spill": "info", "eror": "error", "error": "error", 
    "down": "error", "lemot": "error", "bug": "error", "bantu": "tolong", 
    "tolong": "tolong", "tlong": "tolong", "help": "tolong"
}

def text_normalize(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'(ku|mu|nya|lah|kah|pun)\b', '', text)
    words = text.split()
    normalized_words = []
    for word in words:
        if word in normalizad_word_dict:
            normalized_words.append(normalizad_word_dict[word])
        else:
            normalized_words.append(word)
    result = " ".join(normalized_words)
    return re.sub(r'\s+', ' ', result).strip()