import os
import io
import torch
import soundfile as sf
import logging
import gc

# Matikan log spam
logging.getLogger("TTS").setLevel(logging.ERROR)

from TTS.api import TTS

# Konfigurasi Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Kita simpan wav target di folder models
MODEL_DIR = os.path.join(BASE_DIR, "models") 
SPEAKER_WAV = os.path.join(MODEL_DIR, "target_voice.wav")

class XTTSVoiceEngine:
    def __init__(self):
        print("\n" + "="*50)
        print("[XTTS] Inisialisasi Engine Bahasa Indonesia Native...")
        
        # Cek GPU & Set FP16
        if torch.cuda.is_available():
            self.device = "cuda"
            self.use_half = True # Optimasi 4GB VRAM
            print(f"[XTTS] GPU Terdeteksi: {torch.cuda.get_device_name(0)}")
            print("[XTTS] Mode Hemat VRAM (FP16) Aktif.")
        else:
            self.device = "cpu"
            self.use_half = False
            print("[XTTS] WARNING: Berjalan di CPU (Lambat).")

        # Cek File Suara Target
        if not os.path.exists(SPEAKER_WAV):
            print(f"[XTTS] WARNING: '{SPEAKER_WAV}' tidak ditemukan!")
            print("[XTTS] Sistem akan menggunakan suara default (mungkin tidak anime).")
            # Create dummy file to prevent crash during init if missing
            self._create_dummy_wav()

        # Load Model
        try:
            print("[XTTS] Loading Model (Mungkin memakan waktu download di run pertama)...")
            self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(self.device)
            
            # Konversi ke FP16 untuk hemat memori
            if self.use_half:
                self.tts.tts.half() 
            
            print("[XTTS] Model Siap Digunakan.")
        except Exception as e:
            print(f"[XTTS] CRITICAL ERROR: {e}")
            self.tts = None
        
        print("="*50 + "\n")

    def _create_dummy_wav(self):
        import numpy as np
        sr = 22050
        x = np.zeros(sr * 3, dtype=np.float32)
        sf.write(SPEAKER_WAV, x, sr)

    def synthesize(self, text, emotion="neutral"):
        """
        Return: audio_bytes, mime_type
        """
        if not self.tts:
            return None, "error_model_not_loaded"
        
        if not text or not text.strip():
            return None, "error_empty_text"

        try:
            # Pre-processing text simple
            clean_text = self._naturalize_text(text)

            # Generate (Hati-hati VRAM)
            wav = self.tts.tts(
                text=clean_text, 
                speaker_wav=SPEAKER_WAV, 
                language="id"
            )

            # Bersihkan cache VRAM setelah generate (Penting buat 4GB VRAM)
            if self.device == "cuda":
                torch.cuda.empty_cache()

            # Convert ke bytes
            out_buf = io.BytesIO()
            sf.write(out_buf, wav, 24000, format='WAV')
            return out_buf.getvalue(), "audio/wav"

        except Exception as e:
            print(f"[XTTS] Error Generasi: {e}")
            if "memory" in str(e).lower():
                torch.cuda.empty_cache()
                gc.collect()
            return None, str(e)

    def _naturalize_text(self, text):
        # Mapping sederhana biar ga kaku
        replacements = {
            "saya": "aku",
            "anda": "kamu",
            "apakah": "apa",
            "tidak": "enggak",
        }
        text_lower = text.lower()
        for k, v in replacements.items():
            text_lower = text_lower.replace(f" {k} ", f" {v} ")
        return text_lower

# Singleton
_engine = None
def get_xtts_engine():
    global _engine
    if _engine is None:
        _engine = XTTSVoiceEngine()
    return _engine