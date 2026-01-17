import json
import os

INPUT_FILE = 'data/raw_data.txt'
OUTPUT_FILE = 'data/intents.json'

DEFAULT_RESPONSES = {
    # --- KATEGORI A: AKADEMIK ---
    "jadwal_krs": ["Jadwal pengisian KRS biasanya dilakukan 2 minggu sebelum awal semester. Silakan cek Kalender Akademik di Siakad untuk tanggal pastinya."],
    "syarat_krs": ["Syarat utama mengambil KRS adalah status mahasiswa Aktif dan telah melunasi tagihan keuangan semester sebelumnya."],
    "jadwal_kuliah": ["Jadwal perkuliahan dan pembagian kelas dapat dilihat pada menu 'Jadwal Kuliah' di akun Siakad Anda."],
    "cek_nilai": ["Nilai KHS (Kartu Hasil Studi) dan Transkrip Sementara bisa dilihat dan diunduh melalui menu 'Hasil Studi' di Siakad."],
    "jadwal_ujian": ["Jadwal UTS dan UAS akan tercantum di Kartu Ujian. Biasanya dirilis 1 minggu sebelum masa ujian dimulai."],
    "syarat_ujian": ["Syarat mengikuti ujian adalah lunas biaya semester berjalan dan wajib membawa Kartu Ujian yang sudah dicetak dari Siakad."],
    "info_kalender": ["Kalender Akademik terbaru dapat diunduh di website Biro Administrasi Akademik (BAA) UNIPMA atau dashboard Siakad."],
    "cuti_kuliah": ["Prosedur cuti akademik diajukan ke BAA dengan surat permohonan yang disetujui Dosen Wali dan Kaprodi."],
    "aktif_kuliah": ["Surat Keterangan Aktif Kuliah bisa diurus di Tata Usaha (TU) Fakultas atau diajukan secara online di portal mahasiswa."],
    "pindah_prodi": ["Mutasi prodi memerlukan persetujuan Kaprodi asal dan tujuan, serta memenuhi batas minimal SKS dan IPK tertentu."],

    # --- KATEGORI B: TUGAS AKHIR & KELULUSAN ---
    "syarat_skripsi": ["Syarat skripsi: menempuh minimal 110-120 SKS, IPK minimal 2.75, dan tidak ada nilai D/E pada mata kuliah prasyarat."],
    "pengajuan_judul": ["Pengajuan judul skripsi dilakukan melalui sistem SITA (Sistem Informasi Tugas Akhir) dengan mengunggah outline penelitian."],
    "dosen_pembimbing": ["Dosen Pembimbing ditentukan melalui SK Dekan. Anda bisa melihat nama pembimbing di akun SITA Anda."],
    "kerja_praktik": ["Kerja Praktik (KP/Magang) biasanya diambil pada Semester 6 atau 7. Pendaftaran dilakukan melalui admin prodi masing-masing."],
    "syarat_wisuda": ["Syarat wisuda meliputi: Lulus Sidang TA, Validasi Keuangan, Bebas Pustaka, dan memenuhi skor minimal TOEFL."],
    "jadwal_wisuda": ["Jadwal wisuda biasanya dilaksanakan dalam beberapa gelombang setiap tahunnya. Cek pengumuman di web BAA atau official IG UNIPMA."],
    "biaya_wisuda": ["Rincian biaya wisuda mencakup biaya prosesi, toga, dan ijazah. Nominal pastinya diatur dalam SK Rektor terbaru."],
    "legalisir_ijazah": ["Legalisir ijazah dapat dilakukan di bagian BAA dengan membawa fotokopi ijazah asli dan menunjukkan ijazah asli."],
    "sertifikat_toefl": ["Mahasiswa wajib memiliki skor ELPT/TOEFL minimal tertentu (sesuai standar prodi) sebagai syarat ujian skripsi atau wisuda."],
    "bebas_pustaka": ["Surat Bebas Pustaka diperoleh jika mahasiswa tidak memiliki pinjaman buku dan telah menyerahkan salinan skripsi ke perpustakaan."],

    # --- KATEGORI C: KEUANGAN & ADMINISTRASI ---
    "biaya_ukt": ["Besaran UKT ditentukan berdasarkan kelompok ekonomi saat awal masuk. Rincian tagihan bisa dilihat di menu Keuangan Siakad."],
    "cara_bayar_ukt": ["Pembayaran UKT dilakukan melalui Virtual Account (VA) Bank Jatim atau BNI sesuai nomor yang tertera di Siakad."],
    "dispensasi_bayar": ["Pengajuan dispensasi atau penundaan pembayaran bisa dikonsultasikan ke bagian Keuangan/BAA dengan membawa surat alasan yang kuat."],
    "denda_ukt": ["Keterlambatan pembayaran UKT dapat berakibat pada penonaktifan sementara akun Siakad atau denda sesuai kebijakan universitas."],
    "potongan_ukt": ["Informasi potongan UKT (KIP-K, Beasiswa, atau Saudara Kandung) dapat ditanyakan langsung ke bagian Kemahasiswaan."],
    "lupa_password": ["Jika lupa password Siakad, silakan hubungi admin LPTIK atau gunakan fitur 'Reset Password' jika email aktif."],
    "ganti_data": ["Perubahan data identitas (nama, tgl lahir) wajib melampirkan fotokopi KTP/KK/Ijazah terakhir ke bagian BAA."],
    "siakad_error": ["Jika Siakad error/down, silakan tunggu beberapa saat atau lapor ke Helpdesk LPTIK jika kendala berlanjut."],

    # --- KATEGORI D: FASILITAS & KEMAHASISWAAN ---
    "lokasi_gedung": ["Kampus UNIPMA memiliki beberapa gedung utama (Gedung A, B, C, dst). Silakan cek peta kampus di area pintu masuk."],
    "info_wifi": ["Akses WiFi kampus menggunakan ID mahasiswa. Password default biasanya diberikan saat masa orientasi atau tanya admin lab."],
    "jam_perpus": ["Perpustakaan pusat UNIPMA biasanya buka setiap Senin-Jumat pukul 08.00 - 15.30 WIB."],
    "lokasi_masjid": ["Tempat ibadah/Masjid tersedia di dalam lingkungan kampus untuk kenyamanan beribadah mahasiswa dan staf."],
    "lokasi_kantin": ["Kantin mahasiswa terletak di area belakang atau sekitar gedung perkuliahan yang menyediakan berbagai makanan."],
    "info_beasiswa": ["Info beasiswa (KIP-K, PPA, Djarum, dll) selalu diupdate melalui mading kemahasiswaan atau website resmi UNIPMA."],
    "info_kkn": ["KKN dilaksanakan di semester tertentu. Pendaftaran dan persyaratan wilayah akan diumumkan oleh bagian LPPM."],
    "organisasi_kampus": ["Gabunglah dengan BEM, DPM, atau UKM di tingkat Universitas maupun Fakultas saat periode Open Recruitment."],
    "klinik_kesehatan": ["Kampus menyediakan fasilitas kesehatan terbatas (UKS/Poliklinik) untuk penanganan pertama bagi mahasiswa."],

    # --- KATEGORI E: CHIT-CHAT ---
    "sapaan": ["Halo! Saya asisten virtual akademik UNIPMA. Ada yang bisa saya bantu terkait info perkuliahan?"],
    "identitas_bot": ["Saya adalah bot asisten akademik yang dikembangkan menggunakan teknologi ICNN (Bi-LSTM) untuk membantu mahasiswa."],
    "pamit": ["Sama-sama! Semoga sukses studinya. Jangan ragu bertanya lagi jika ada kendala."],
    "default": ["Maaf, saya belum memahami maksud Anda. Silakan ketik kata kunci yang lebih spesifik seperti 'jadwal krs' atau 'syarat wisuda'."]
}

def generate_json():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ File {INPUT_FILE} tidak ditemukan! Pastikan file raw_data.txt sudah ada di folder data/.")
        return

    intents_list = []
    current_tag = None
    current_patterns = []

    print("⏳ Sedang memproses 40 Intent...")
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line: continue

        if line.startswith("==="):
            if current_tag:
                response = DEFAULT_RESPONSES.get(current_tag, DEFAULT_RESPONSES["default"])
                intents_list.append({
                    "tag": current_tag,
                    "patterns": current_patterns,
                    "responses": response
                })
            
            current_tag = line.replace("===", "").strip()
            current_patterns = []
        else:
            current_patterns.append(line)

    if current_tag:
        response = DEFAULT_RESPONSES.get(current_tag, DEFAULT_RESPONSES["default"])
        intents_list.append({
            "tag": current_tag,
            "patterns": current_patterns,
            "responses": response
        })

    final_data = {"intents": intents_list}

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)

    print(f"\n🎉 SUKSES! {len(intents_list)} Tag telah digenerate ke {OUTPUT_FILE}")
    
    missing_tags = set(DEFAULT_RESPONSES.keys()) - set([i['tag'] for i in intents_list]) - {"default"}
    if missing_tags:
        print(f"⚠️ PERINGATAN: Tag berikut ada di kamus respon tapi TIDAK ADA di raw_data.txt: {list(missing_tags)}")

if __name__ == "__main__":
    generate_json()