# server/voice.py
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import asyncio
import io
import pygame
import re
import speech_recognition as sr
import numpy as np
import soundfile as sf
import requests
import urllib.parse
import random

from faster_whisper import WhisperModel
from scipy import signal
from deep_translator import GoogleTranslator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STYLE_BERT_API_URL = "http://127.0.0.1:5001/voice"
STYLE_BERT_MODEL_ID = 0

ENABLE_NATURAL_BREATH = True
ENABLE_VOICE_WARMTH = True
ENABLE_HUMBLE_TONE = True
ENABLE_SMOOTH_TRANSITIONS = True
ENABLE_NATURAL_FILLERS = True
ENABLE_SMART_PAUSES = True
ENABLE_FEMININE_VOICE = True

DEVICE_STT = "cpu"

class AnimeVoiceAssistant:
    def __init__(self):
        self.stt_model = None
        self.recognizer = None
        self.rvc_device = None
        self.translator = GoogleTranslator(source="id", target="ja")
        
        self.thinking_fillers = [
            "...",
            "えっと...",
            "ええ...",
            "あの...",
            "んー...",
            "そうですね...",
            "まあ...",
            "えーっと...",
            "うーん...",
        ]
        
        self.breath_pauses = [
            "...",
            "、",
        ]

    def _translate_id_to_jp(self, text):
        try:
            return self.translator.translate(text)
        except:
            return text

    def _add_sentence_breaks(self, text):
        if not ENABLE_NATURAL_FILLERS:
            return text
        
        sentences = re.split(r'([。！？])', text)
        result = []
        
        for i in range(0, len(sentences), 2):
            if i >= len(sentences):
                break
                
            sentence = sentences[i]
            punctuation = sentences[i + 1] if i + 1 < len(sentences) else ""
            
            if not sentence.strip():
                continue
            
            result.append(sentence)
            result.append(punctuation)
            
            if punctuation and i + 2 < len(sentences):
                filler = random.choice(self.thinking_fillers)
                result.append(filler)
        
        return ''.join(result)

    def _add_clause_breaks(self, text):
        if not ENABLE_SMART_PAUSES:
            return text
        
        parts = text.split('、')
        result = []
        
        for i, part in enumerate(parts):
            if not part.strip():
                continue
            
            result.append(part)
            
            if i < len(parts) - 1:
                if random.random() < 0.6:
                    pause = random.choice(self.breath_pauses)
                    result.append(pause)
                else:
                    result.append('、')
        
        return ''.join(result)

    def _add_long_sentence_breaks(self, text):
        words = []
        current = ""
        char_count = 0
        
        for char in text:
            current += char
            
            if char in '。！？、':
                words.append(current)
                current = ""
                char_count = 0
            else:
                char_count += 1
                if char_count >= 10 and char not in 'ャュョッァィゥェォ':
                    if random.random() < 0.5:
                        filler = random.choice(["...", "、"])
                        words.append(current + filler)
                    else:
                        words.append(current + '、')
                    current = ""
                    char_count = 0
        
        if current:
            words.append(current)
        
        return ''.join(words)

    def _process_japanese_text(self, text):
        text = self._add_long_sentence_breaks(text)
        text = self._add_clause_breaks(text)
        text = self._add_sentence_breaks(text)
        
        text = re.sub(r'\.{4,}', '...', text)
        text = re.sub(r'、{2,}', '、', text)
        text = re.sub(r'。{2,}', '。', text)
        
        return text

    def _apply_feminine_pitch(self, audio_data, sample_rate=44100):
        if not ENABLE_FEMININE_VOICE:
            return audio_data
        
        audio = np.asarray(audio_data, dtype=np.float32)
        
        try:
            from scipy.signal import resample
            pitch_shift_factor = 1.30
            
            new_length = int(len(audio) / pitch_shift_factor)
            audio_shifted = resample(audio, new_length)
            
            audio = resample(audio_shifted, len(audio))
            
        except:
            pass
        
        return audio

    def _apply_feminine_formant(self, audio_data, sample_rate=44100):
        if not ENABLE_FEMININE_VOICE:
            return audio_data
        
        audio = np.asarray(audio_data, dtype=np.float32)
        
        try:
            sos_high = signal.butter(2, 3500, 'high', fs=sample_rate, output='sos')
            high_freq = signal.sosfilt(sos_high, audio)
            
            sos_mid = signal.butter(2, [800, 3500], btype='band', fs=sample_rate, output='sos')
            mid_freq = signal.sosfilt(sos_mid, audio)
            
            sos_low = signal.butter(2, 400, 'low', fs=sample_rate, output='sos')
            low_freq = signal.sosfilt(sos_low, audio)
            
            audio = low_freq * 0.5 + mid_freq * 0.65 + high_freq * 1.2
            
            audio = audio / (np.max(np.abs(audio)) + 1e-8) * 0.95
            
        except:
            pass
        
        return audio

    def _apply_feminine_breathiness(self, audio_data, sample_rate=44100):
        if not ENABLE_FEMININE_VOICE:
            return audio_data
        
        audio = np.asarray(audio_data, dtype=np.float32)
        
        try:
            breath_noise = np.random.normal(0, 0.008, len(audio)).astype(np.float32)
            
            sos = signal.butter(4, [2000, 8000], btype='band', fs=sample_rate, output='sos')
            breath_filtered = signal.sosfilt(sos, breath_noise)
            
            audio = audio * 0.92 + breath_filtered * 0.08
            
        except:
            pass
        
        return audio

    def _add_natural_breath(self, audio_data, sample_rate=44100):
        if not ENABLE_NATURAL_BREATH:
            return audio_data
        audio = np.asarray(audio_data, dtype=np.float32)
        breath_duration = int(sample_rate * 0.12)
        breath = np.random.normal(0, 0.002, breath_duration).astype(np.float32)
        breath *= np.hanning(breath_duration)
        breath *= 0.15
        return np.concatenate([breath, audio, breath])

    def _apply_voice_warmth(self, audio_data, sample_rate=44100):
        if not ENABLE_VOICE_WARMTH:
            return audio_data
        audio = np.asarray(audio_data, dtype=np.float32)
        try:
            sos_low = signal.butter(2, 200, 'high', fs=sample_rate, output='sos')
            audio = signal.sosfilt(sos_low, audio)
            sos_warmth = signal.butter(1, [300, 5000], btype='band', fs=sample_rate, output='sos')
            warm_signal = signal.sosfilt(sos_warmth, audio)
            audio = audio * 0.7 + warm_signal * 0.3
            audio = np.tanh(audio * 1.02) * 0.94
        except:
            pass
        return audio

    def _smooth_audio_transitions(self, audio_data, sample_rate=44100):
        if not ENABLE_SMOOTH_TRANSITIONS:
            return audio_data
        audio = np.asarray(audio_data, dtype=np.float32)
        try:
            sos = signal.butter(3, 8000, 'low', fs=sample_rate, output='sos')
            audio = signal.sosfilt(sos, audio)
        except:
            pass
        fade_duration = int(sample_rate * 0.012)
        if fade_duration > 0 and len(audio) > fade_duration * 2:
            fade_in = np.linspace(0, 1, fade_duration) ** 1.5
            fade_out = np.linspace(1, 0, fade_duration) ** 1.5
            audio[:fade_duration] *= fade_in
            audio[-fade_duration:] *= fade_out
        return audio

    def _apply_humble_characteristics(self, audio_data, sample_rate=44100):
        if not ENABLE_HUMBLE_TONE:
            return audio_data
        audio = np.asarray(audio_data, dtype=np.float32)
        audio = audio * 0.88
        try:
            b, a = signal.butter(2, [250, 4500], btype='band', fs=sample_rate)
            audio = signal.filtfilt(b, a, audio)
        except:
            pass
        return audio

    def _normalize_tts_text(self, text):
        s = (text or "").strip()
        s = " ".join(s.split())
        if not s:
            return ""
        return s

    def _silence_wav_bytes(self, duration_s=0.25, sample_rate=44100):
        sr = int(sample_rate)
        n = max(1, int(sr * float(duration_s)))
        x = np.zeros(n, dtype=np.float32)
        buf = io.BytesIO()
        sf.write(buf, x, sr, format="WAV", subtype="PCM_16")
        return buf.getvalue()

    def _ensure_stt(self):
        if self.stt_model is not None and self.recognizer is not None:
            return
        self.stt_model = WhisperModel("base", device=DEVICE_STT, compute_type="int8")
        self.recognizer = sr.Recognizer()

    def listen(self):
        self._ensure_stt()
        with sr.Microphone() as source:
            print("\n[LISTENING]...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                with open("temp_input.wav", "wb") as f:
                    f.write(audio.get_wav_data())
                segments, _ = self.stt_model.transcribe("temp_input.wav", language="id")
                text = "".join([s.text for s in segments]).strip()
                if text:
                    print(f"[USER]: {text}")
                    return text
                return None
            except Exception:
                return None

    def _map_emotion_to_style(self, emotion):
        emo = (emotion or "").lower()
        if "happy" in emo or "senang" in emo:
            return "Happy"
        if "sad" in emo or "sedih" in emo:
            return "Sad"
        if "angry" in emo or "marah" in emo:
            return "Angry"
        if "surprised" in emo or "kaget" in emo:
            return "Surprised"
        if "whisper" in emo:
            return "Whisper"
        return "Neutral"

    def _generate_style_bert_audio(self, text, emotion, output_path):
        try:
            style = self._map_emotion_to_style(emotion)
            params = {
                "text": text,
                "model_id": STYLE_BERT_MODEL_ID,
                "style": style,
                "style_weight": 0.5,
                "language": "JP",
                "sdp_ratio": 0.3,
                "noise": 0.6,
                "noisew": 0.8,
                "length": 1.35
            }
            encoded = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
            url = f"{STYLE_BERT_API_URL}?{encoded}"
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return True
            else:
                return False
        except:
            return False

    async def speak_anime(self, text):
        print(f"[AI]: {text}")
        jp_text = self._translate_id_to_jp(text)
        jp_text_enhanced = self._process_japanese_text(jp_text)
        print(f"[JP]: {jp_text_enhanced}")
        
        output_wav = os.path.join(BASE_DIR, "output_anime.wav")
        norm_text = self._normalize_tts_text(jp_text_enhanced)
        success = self._generate_style_bert_audio(norm_text, "Neutral", output_wav)
        if success:
            try:
                audio_data, sr = sf.read(output_wav, dtype='float32')
                audio_data = self._smooth_audio_transitions(audio_data, sr)
                audio_data = self._apply_humble_characteristics(audio_data, sr)
                audio_data = self._apply_feminine_pitch(audio_data, sr)
                audio_data = self._apply_feminine_formant(audio_data, sr)
                audio_data = self._apply_feminine_breathiness(audio_data, sr)
                audio_data = self._apply_voice_warmth(audio_data, sr)
                audio_data = self._add_natural_breath(audio_data, sr)
                sf.write(output_wav, audio_data, sr)
            except:
                pass
            self.play_audio(output_wav)

    def synthesize_bytes(self, text, voice=None, pitch=None, emotion=None, f0method=None):
        output_wav = os.path.join(BASE_DIR, "output_tts_bytes.wav")
        jp_text = self._translate_id_to_jp(text)
        jp_text_enhanced = self._process_japanese_text(jp_text)
        norm_text = self._normalize_tts_text(jp_text_enhanced)
        success = self._generate_style_bert_audio(norm_text, emotion, output_wav)
        if success:
            try:
                audio_data, sr = sf.read(output_wav, dtype='float32')
                audio_data = self._apply_feminine_pitch(audio_data, sr)
                audio_data = self._apply_feminine_formant(audio_data, sr)
                audio_data = self._apply_feminine_breathiness(audio_data, sr)
                audio_data = self._apply_voice_warmth(audio_data, sr)
                sf.write(output_wav, audio_data, sr)
            except:
                pass
            with open(output_wav, "rb") as f:
                audio_bytes = f.read()
            if os.path.exists(output_wav):
                os.remove(output_wav)
            return audio_bytes, "audio/wav"
        else:
            return self._silence_wav_bytes(), "audio/wav"

    def play_audio(self, file_path):
        pygame.mixer.init()
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
        except:
            pass
        finally:
            pygame.mixer.quit()
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass

    def warmup_rvc(self):
        try:
            requests.get(STYLE_BERT_API_URL.replace("/voice", ""), timeout=1)
            return True
        except:
            return False

    def transcribe_file(self, audio_path):
        self._ensure_stt()
        segments, _ = self.stt_model.transcribe(audio_path, language="id")
        return "".join([s.text for s in segments]).strip()

if __name__ == "__main__":
    bot = AnimeVoiceAssistant()
    try:
        while True:
            user_input = bot.listen()
            if user_input:
                asyncio.run(bot.speak_anime(user_input))
    except KeyboardInterrupt:
        pass