def get_data_by_intent(intent):
    database = {
        "jadwal_krs": {
            "mulai": "11 Agustus 2025",
            "selesai": "22 Agustus 2025",
            "semester": "Ganjil 2025/2026",
            "link_siakad": "sim.unipma.ac.id"
        },
        "syarat_krs": {
            "batas_bayar": "10 Agustus 2025",
            "link_siakad": "sim.unipma.ac.id",
            "semester": "Ganjil 2025/2026",
            "min_bayar": "50%"
        },
        "jadwal_kuliah": {
            "tanggal_masuk": "1 September 2025",
            "semester": "Ganjil 2025/2026",
            "link": "sim.unipma.ac.id",
            "tgl_masuk": "1 September 2025",
            "menu_siakad": "Jadwal Kuliah"
        },
        "cek_nilai": {
            "link_siakad": "sim.unipma.ac.id",
            "semester": "Ganjil 2025/2026",
            "tgl_rilis": "10 Januari 2026",
            "batas_revisi": "15 Januari 2026",
            "menu_nilai": "Kartu Hasil Studi"
        },
        "jadwal_ujian": {
            "mulai": "5 Januari 2026",
            "selesai": "17 Januari 2026",
            "tanggal_susulan": "19 - 21 Januari 2026",
            "semester": "Ganjil 2025/2026",
            "tgl_uts": "20 Oktober 2025",
            "tgl_uas": "5 Januari 2026",
            "batas_lapor": "3"
        },
        "syarat_ujian": {
            "persen_hadir": "75%",
            "cetak_kartu": "20 Desember 2025",
            "mulai": "5 Januari 2026",
            "semester": "Ganjil 2025/2026",
            "min_hadir": "75",
            "seragam": "Almamater",
            "link": "sim.unipma.ac.id"
        },
        "info_kalender": {
            "semester": "Ganjil 2025/2026",
            "link_kalender": "unipma.ac.id/kalender",
            "tahun": "2025",
            "tgl_libur": "15 - 30 Juni 2025",
            "tgl_libur_mulai": "20 Januari 2026",
            "tgl_libur_selesai": "28 Februari 2026",
            "next_holiday": "17 Agustus",
            "ket_holiday": "Hari Kemerdekaan",
            "tahun_ajar": "2025/2026",
            "minggu_tenang": "29 Desember 2025",
            "tgl_raya": "31 Maret 2025",
            "tgl_masuk": "1 September 2025"
        },
        "cuti_kuliah": {
            "batas_cuti": "15 September 2025",
            "durasi": "2",
            "semester": "Ganjil",
            "biaya_cuti": "Rp 250.000",
            "max_cuti": "4",
            "lokasi_baa": "Gedung A Lantai 1",
            "link": "sim.unipma.ac.id"
        },
        "aktif_kuliah": {
            "link_surat": "sim.unipma.ac.id",
            "hari": "2",
            "menu_surat": "Surat Keterangan",
            "keperluan": "Tunjangan Gaji / Beasiswa",
            "gedung_baa": "Gedung A",
            "link": "sim.unipma.ac.id",
            "waktu_proses": "1-2",
            "jam_layanan": "08.00 - 15.00"
        },
        "pindah_prodi": {
            "semester": "Ganjil",
            "sks": "40",
            "batas_pindah": "30 Agustus 2025",
            "batas_semester": "4",
            "min_smt": "2",
            "min_ipk": "3.00",
            "biaya_konversi": "Rp 500.000",
            "durasi_proses": "2"
        },
        "syarat_skripsi": {
            "sks": "110",
            "batas_nilai_d": "2",
            "skor_toefl": "400",
            "semester": "7",
            "min_sks": "110",
            "min_ipk": "2.75",
            "min_smt": "7"
        },
        "pengajuan_judul": {
            "link_sita": "sita.unipma.ac.id",
            "batas_judul": "30 September 2025",
            "waktu_validasi": "1 Minggu",
            "max_judul": "3"
        },
        "dosen_pembimbing": {
            "link_sita": "sita.unipma.ac.id",
            "kali": "8",
            "tgl_sk": "10 Oktober 2025",
            "batas_ganti": "1 Bulan setelah SK",
            "min_bimbingan": "8"
        },
        "kerja_praktik": {
            "semester": "6",
            "durasi": "2",
            "link_kp": "sim.unipma.ac.id",
            "sks": "4",
            "min_smt_kp": "6",
            "min_sks_kp": "100",
            "lokasi_tu": "Tata Usaha Fakultas",
            "durasi_kp": "2",
            "min_ipk": "2.50",
            "batas_kp": "Setiap Awal Semester"
        },
        "syarat_wisuda": {
            "skor": "425",
            "ipk": "2.75",
            "link_wisuda": "wisuda.unipma.ac.id",
            "min_toefl": "425",
            "batas_yudisium": "10 Oktober 2025",
            "batas_berkas": "15 Oktober 2025"
        },
        "jadwal_wisuda": {
            "periode": "Gelombang I 2025",
            "tanggal": "25 Oktober 2025",
            "tempat": "Graha Cendekia UNIPMA",
            "bulan": "Oktober",
            "jam": "07.00 WIB",
            "link_wisuda": "wisuda.unipma.ac.id",
            "periode_wisuda": "I Tahun 2025",
            "tgl_wisuda": "25 Oktober 2025",
            "tempat_wisuda": "Graha Cendekia",
            "tgl_tutup": "30 September 2025",
            "tgl_gladi": "24 Oktober 2025",
            "jam_gladi": "14.00 WIB",
            "bln_1": "April",
            "bln_2": "Oktober"
        },
        "biaya_wisuda": {
            "biaya": "2.250.000",
            "batas_bayar": "30 September 2025",
            "bank": "Bank Jatim",
            "biaya_s1": "2.250.000",
            "biaya_s2": "2.500.000",
            "nama_rek": "Bendahara UNIPMA",
            "biaya_wisuda": "Rp 2.250.000",
            "bank_wisuda": "Bank Jatim",
            "batas_bayar_wisuda": "30 September 2025"
        },
        "legalisir_ijazah": {
            "biaya_per_lembar": "5.000",
            "maks": "10",
            "link_legalisir": "sim.unipma.ac.id",
            "hari": "3",
            "jam_buka": "08.00",
            "jam_tutup": "15.00",
            "biaya_legalisir": "Rp 5.000",
            "max_lembar": "10",
            "jam_layanan": "08.00 - 15.00"
        },
        "sertifikat_toefl": {
            "skor_s1": "425",
            "link_toefl": "lab-bahasa.unipma.ac.id",
            "biaya_tes": "150.000",
            "tgl_tes": "Selasa & Rabu",
            "min_skor_toefl": "425",
            "hari_tes": "Selasa dan Rabu",
            "masa_berlaku": "2",
            "next_toefl": "Setiap Minggu",
            "lokasi_lab": "Gedung C Lantai 2"
        },
        "bebas_pustaka": {
            "link_perpus": "perpus.unipma.ac.id",
            "jam": "08.00 - 15.30",
            "lokasi_perpus": "Gedung Perpustakaan",
            "min_buku": "2",
            "link_repo": "repository.unipma.ac.id"
        },
        "biaya_ukt": {
            "min": "2.100.000",
            "max": "4.500.000",
            "teknik": "Rp 3.800.000",
            "ekonomi": "Rp 3.200.000",
            "pendidikan": "Rp 2.900.000",
            "hukum": "Rp 3.100.000",
            "kesehatan": "Rp 4.000.000",
            "prodi_teknik": "Rp 3.800.000",
            "prodi_ekonomi": "Rp 3.200.000",
            "prodi_pendidikan": "Rp 2.900.000",
            "prodi_hukum": "Rp 3.100.000",
            "prodi_kesehatan": "Rp 4.000.000",
            "ukt_teknik": "Rp 3.800.000",
            "ukt_ekonomi": "Rp 3.200.000",
            "ukt_fkip": "Rp 2.900.000",
            "link_siakad": "sim.unipma.ac.id",
            "tgl": "20 Agustus 2025",
            "nominal_ukt": "Sesuai Prodi",
            "bank_ukt": "Bank Jatim / BNI",
            "batas_bayar_ukt": "20 Agustus 2025"
        },
        "cara_bayar_ukt": {
            "bank": "Bank Jatim & BNI",
            "kode_univ": "041",
            "bank_ukt": "Bank Jatim",
            "kode_va": "88041 + NIM",
            "kode_institusi": "041"
        },
        "dispensasi_bayar": {
            "tgl": "15 Agustus 2025",
            "kali": "2",
            "batas_dispen": "15 Agustus 2025",
            "max_cicilan": "3",
            "lokasi_keuangan": "Gedung A Lantai 1"
        },
        "denda_ukt": {
            "denda": "50.000",
            "tgl": "20 Agustus 2025",
            "nominal": "50.000",
            "nominal_denda": "Rp 50.000",
            "batas_bayar_ukt": "20 Agustus 2025"
        },
        "potongan_ukt": {
            "persen": "10",
            "link_beasiswa": "kemahasiswaan.unipma.ac.id",
            "diskon_saudara": "10"
        },
        "lupa_password": {
            "nomer": "0812-3456-7890 (LPTIK)",
            "format": "DDMMYYYY",
            "link_siakad": "sim.unipma.ac.id",
            "kontak_lptik": "0812-3456-7890",
            "gedung_tik": "Gedung Lab Komputer",
            "format_password": "Tanggal Lahir (DDMMYYYY)"
        },
        "ganti_data": {
            "link_siakad": "sim.unipma.ac.id",
            "gedung_baa": "Gedung A",
            "loket_data": "3",
            "periode_lapor": "Awal Semester"
        },
        "siakad_error": {
            "link": "sim.unipma.ac.id",
            "email_it": "lptik@unipma.ac.id",
            "link_alt": "10.10.10.1 (Lokal)",
            "ig_kampus": "@unipma_official",
            "email_helpdesk": "helpdesk@unipma.ac.id"
        },
        "lokasi_gedung": {
            "graha": "Jl. Setia Budi",
            "rektorat": "Gedung A Kampus 1",
            "lab_terpadu": "Gedung C Lantai 3",
            "perpus": "Gedung Perpustakaan (Utara Masjid)",
            "fakultas": "Fakultas masing-masing",
            "gedung": "A/B/C",
            "lantai": "1",
            "prodi": "Informatika",
            "prodi_teknik": "Gedung C Lantai 2",
            "prodi_ekonomi": "Gedung A Lantai 2",
            "prodi_pendidikan": "Gedung B Lantai 1",
            "prodi_hukum": "Gedung D",
            "prodi_kesehatan": "Gedung E (Laboratorium)",
            "lokasi_graha": "Jl. Setia Budi No. 85",
            "lokasi_rektorat": "Gedung A",
            "lokasi_lab": "Gedung Laboratorium Terpadu",
            "lokasi_perpus": "Sebelah Masjid Ulul Albab",
            "gedung_teknik": "C",
            "lantai_tu": "1",
            "landmark_pasca": "Lapangan Tenis",
            "gedung_baa": "A"
        },
        "info_wifi": {
            "ssid": "UNIPMA_Smart",
            "password": "NIM & Password SIM",
            "link_login": "1.1.1.1",
            "lokasi": "Seluruh Kampus",
            "ssid_wifi": "UNIPMA_Smart",
            "gedung_tik": "Gedung Lab Komputer",
            "lokasi_wifi_kencang": "Perpustakaan & Gedung A",
            "pass_perpus": "baca_buku"
        },
        "jam_perpus": {
            "buka": "08.00",
            "tutup": "16.00",
            "istirahat_mulai": "11.30",
            "istirahat_selesai": "13.00",
            "tutup_sabtu": "12.00",
            "jam_buka": "08.00",
            "jam_tutup": "16.00",
            "jam_istirahat": "12.00 - 13.00",
            "jam_layanan_admin": "09.00 - 14.00"
        },
        "lokasi_masjid": {
            "lokasi_masjid": "Kampus 1",
            "gedung": "A-C",
            "lantai": "1",
            "nama_masjid": "Ulul Albab",
            "jam_jumat": "11.45 WIB",
            "lokasi": "Area Kampus",
            "lokasi_masjid_utama": "Tengah Kampus (Sebelah Perpus)",
            "lantai_mushola_a": "2",
            "landmark_masjid": "Gedung C",
            "lantai_mushola_teknik": "3"
        },
        "lokasi_kantin": {
            "gedung": "Fasilitas Umum",
            "lokasi": "Belakang Gedung C",
            "nama_kantin": "Kantin Pusat",
            "tanda": "Parkiran",
            "buka": "07.00",
            "tutup": "16.00",
            "gedung_kantin": "C",
            "lokasi_kantin_jujur": "Lobby Gedung A",
            "lokasi_kantin_pusat": "Area Parkir Belakang",
            "jam_buka_kantin": "07.00",
            "area_pujasera": "Utara Masjid"
        },
        "info_beasiswa": {
            "link_mhs": "kemahasiswaan.unipma.ac.id",
            "nama_beasiswa": "KIP-K",
            "link_daftar": "kip-kuliah.kemdikbud.go.id",
            "bulan": "Agustus",
            "link_tele": "@infobeasiswa",
            "bln_kipk": "Juli - Agustus",
            "link_beasiswa": "kemahasiswaan.unipma.ac.id",
            "min_ipk_ppa": "3.25",
            "smt_ppa": "3",
            "ig_kemahasiswaan": "@kemahasiswaan_unipma",
            "min_ipk_umum": "3.00",
            "gedung_kemahasiswaan": "A Lantai 1"
        },
        "info_kkn": {
            "periode": "Januari 2026",
            "bulan": "Januari",
            "sks": "110",
            "mulai": "1 Desember 2025",
            "selesai": "15 Desember 2025",
            "wilayah": "Madiun & Magetan",
            "desa": "Binaan",
            "tgl_pembekalan": "20 Desember 2025",
            "tanggal": "2 Januari 2026",
            "periode_kkn": "Genap 2025/2026",
            "lokasi_kkn": "Kabupaten Madiun & Ngawi",
            "min_sks_kkn": "100",
            "tgl_daftar_kkn": "November 2025",
            "smt_kkn": "7",
            "biaya_kkn": "Rp 750.000",
            "link_lppm": "lppm.unipma.ac.id"
        },
        "organisasi_kampus": {
            "lokasi": "Kampus 1",
            "ig_organisasi": "bemunipma",
            "masa_orientasi": "PKKMB (September)",
            "gedung_ukm": "Student Center",
            "ig_bem": "@bem_unipma"
        },
        "klinik_kesehatan": {
            "lokasi": "Kampus 1 Lantai 1",
            "gedung": "Layanan Umum",
            "jam": "08.00 - 15.00",
            "nomor": "0351-462986",
            "nomer_darurat": "119",
            "gedung_klinik": "Poliklinik (Dekat Gerbang 2)",
            "jam_klinik": "08.00 - 14.00",
            "lokasi_uks": "Setiap Fakultas"
        },
        "sapaan": {
            "nama_bot": "Alisa"
        },
        "identitas_bot": {
            "nama_bot": "Alisa"
        },
        "pamit": {
            "nama_bot": "Alisa"
        }
    }

    return database.get(intent, None)