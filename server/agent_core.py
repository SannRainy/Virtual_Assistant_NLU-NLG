import numpy as np
from tensorflow.keras.preprocessing.sequence import pad_sequences
from utils.text_preprocessing import text_normalize
from utils.response_generator import generate_hybrid_response
from utils.session_manager import SessionManager
from utils.clarification_data import CLARIFICATION_MAP

class AgentOrchestrator:
    def __init__(self, model, tokenizer, lbl_encoder, intent_map, stemmer, max_len=30):
        self.model = model
        self.tokenizer = tokenizer
        self.lbl_encoder = lbl_encoder
        self.intent_map = intent_map
        self.stemmer = stemmer
        self.max_len = max_len
        
        self.CONFIDENCE_THRESHOLD = 0.45
        self.CLARIFICATION_THRESHOLD = 0.20
        
        self.sessions = {}

        self.tools = {
            'cek_nilai': self.tool_check_grades,
            'jadwal_kuliah': self.tool_get_schedule,
            'biaya_ukt': self.tool_check_tuition,
            'denda_ukt': self.tool_check_penalty,
            'jadwal_ujian': self.tool_exam_schedule,
            'dosen_pembimbing': self.tool_check_supervisor,
            'lokasi_gedung': self.tool_find_location,
            'siakad_error': self.tool_system_status
        }

    def get_session(self, session_id):
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionManager()
        return self.sessions[session_id]

    def reset_session(self, session_id):
        if session_id in self.sessions:
            self.sessions[session_id].reset_session()

    def process_query(self, user_input, session_id):
        session = self.get_session(session_id)
        session.update_history("user", user_input)
        session.extract_entities(user_input) 

        processed_inp = self.stemmer.stem(text_normalize(user_input))
        seq = self.tokenizer.texts_to_sequences([processed_inp])
        padded = pad_sequences(seq, truncating='post', maxlen=self.max_len)

        result = self.model.predict(padded, verbose=0)
        max_prob = np.max(result)
        tag_index = np.argmax(result)
        tag = self.lbl_encoder.inverse_transform([tag_index])[0]

        response_text = ""
        emotion = "neutral"

        if max_prob >= self.CONFIDENCE_THRESHOLD:
            session.set_context(tag)
            
            if tag in self.tools:
                response_text = self.tools[tag](session, tag)
                emotion = "neutral"
                if tag == 'siakad_error': emotion = "sad"
            
            elif tag in ['syarat_krs', 'syarat_ujian', 'syarat_skripsi', 'syarat_wisuda', 'info_beasiswa']:
                response_text = self.execute_rag(user_input, tag)
                emotion = "neutral"

            else:
                static_responses = self.intent_map.get(tag, ["Maaf, data respon tidak ditemukan."])
                response_text = generate_hybrid_response(tag, static_responses, session.memory_slots)
                
                if tag in ['sapaan', 'terimakasih']:
                    emotion = "happy"
                elif tag in ['pamit']:
                    emotion = "neutral"

        elif max_prob >= self.CLARIFICATION_THRESHOLD:
            clarification = CLARIFICATION_MAP.get(tag)
            if clarification:
                response_text = clarification
            else:
                response_text = f"Saya mendeteksi ini terkait '{tag.replace('_', ' ')}', tapi saya kurang yakin. Bisa diperjelas?"
            emotion = "confused"

        else:
            response_text = "Maaf, saya belum memahami maksud Anda. Bisa gunakan kata kunci lain seperti 'Jadwal', 'Nilai', atau 'UKT'?"
            emotion = "confused"

        session.update_history("ai", response_text)

        return {
            "reply": response_text,
            "emotion": emotion,
            "intent": tag,
            "confidence": float(max_prob),
            "debug": session.debug_memory()
        }

    def tool_check_grades(self, session, tag):
        nim = session.memory_slots.get('nim')
        semester = session.memory_slots.get('semester', 'Semester ini')
        
        if not nim:
            return "Untuk mengecek nilai, silakan login atau sebutkan NIM Anda terlebih dahulu."
        
        return f"[AKSES DATABASE] Menampilkan Kartu Hasil Studi (KHS) untuk NIM {nim} pada {semester}. IPK Sementara: 3.50."

    def tool_get_schedule(self, session, tag):
        prodi = session.memory_slots.get('prodi')
        if not prodi:
            return "Anda ingin melihat jadwal kuliah untuk Program Studi apa?"
        return f"[AKSES DATABASE] Berikut adalah jadwal perkuliahan terbaru untuk Prodi {prodi}."

    def tool_check_tuition(self, session, tag):
        static_responses = self.intent_map.get(tag, [
            "Besaran UKT dapat dilihat pada menu Keuangan di Siakad Anda."
        ])
        return generate_hybrid_response(tag, static_responses, session.memory_slots)

    def tool_check_penalty(self, session, tag):
        return "[AKSES KEUANGAN] Tidak ada denda keterlambatan yang tercatat pada akun Anda saat ini."

    def tool_exam_schedule(self, session, tag):
        return "Jadwal UTS/UAS dapat dilihat pada Kartu Ujian yang dicetak melalui Siakad H-1 minggu sebelum pelaksanaan."

    def tool_check_supervisor(self, session, tag):
        return "[AKSES SITA] Dosen Pembimbing Skripsi Anda tercatat di sistem SITA. Silakan login ke portal tugas akhir untuk detail kontak."

    def tool_find_location(self, session, tag):
        gedung = session.memory_slots.get('gedung') or session.memory_slots.get('lokasi')
        if gedung:
            return f"Lokasi {gedung} berada di area kampus utama. Anda bisa melihat peta digital di website universitas."
        return "Gedung atau lokasi mana yang ingin Anda cari?"

    def tool_system_status(self, session, tag):
        return "[SYSTEM CHECK] Server Siakad terpantau stabil. Jika mengalami error 502/504, silakan clear cache browser atau coba lagi dalam 15 menit."

    def execute_rag(self, query, tag):
        context_docs = "[RAG RETRIEVAL] Mengambil dokumen panduan akademik terkait..."
        return f"{context_docs} Berdasarkan panduan resmi: Penjelasan detail mengenai {tag.replace('_', ' ')} tersedia di Buku Pedoman Akademik halaman 20-25."
