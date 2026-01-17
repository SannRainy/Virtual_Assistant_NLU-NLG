import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import asyncio
import contextlib
import edge_tts
import html
import io
import pygame
import re
import speech_recognition as sr
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
from scipy import signal
from scipy.interpolate import CubicSpline
from scipy.ndimage import gaussian_filter1d

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RVC_MODEL_PATH = os.path.join(BASE_DIR, "models", "ayaka-jp_e101.pth")
RVC_INDEX_PATH = os.path.join(BASE_DIR, "models", "added_IVF4031_Flat_nprobe_1_ayaka-jp_v2.index")
if not os.path.exists(RVC_INDEX_PATH):
    RVC_INDEX_PATH = ""

TTS_VOICE = "id-ID-GadisNeural"
PITCH_SHIFT = -2
RVC_INDEX_RATE = 0.78
RVC_RMS_MIX_RATE = 0.21
RVC_PROTECT = 0.45
RVC_FILTER_RADIUS = 3
RVC_F0_METHOD = "rmvpe"
RVC_F0_AUTOTUNE = True
QUIET_RVC_LOGS = True
ENABLE_CASUAL_F0 = True
ENABLE_SMOOTH_TRANSITIONS = True
ENABLE_HUMBLE_TONE = True
ENABLE_NATURAL_BREATH = True
ENABLE_VOICE_WARMTH = True
CASUAL_REF_AUDIO_PATH = os.path.join(BASE_DIR, "models", "ref_casual.wav")

DEVICE_STT = "cpu"
DEVICE_RVC = None
RVC_CUDA_DEVICE = "cuda:0"
RVC_CPU_DEVICE = "cpu:0"

class AnimeVoiceAssistant:
    def __init__(self):
        self.stt_model = None
        self.recognizer = None
        self.rvc = None
        self.rvc_device = None
        import threading
        self.rvc_lock = threading.Lock()
        self.devnull = open(os.devnull, "w")

        try:
            from rvc_python.infer import RVCInference
            print("[INIT] Memuat Pita Suara Anime (RVC)...")
            import torch
            if DEVICE_RVC is not None:
                device_rvc = DEVICE_RVC
            else:
                device_rvc = RVC_CUDA_DEVICE if torch.cuda.is_available() else RVC_CPU_DEVICE
            with self._maybe_quiet_rvc():
                rvc = RVCInference(device=device_rvc)
                self.rvc_device = device_rvc

            if os.path.exists(RVC_MODEL_PATH):
                with self._maybe_quiet_rvc():
                    rvc.load_model(RVC_MODEL_PATH, index_path=RVC_INDEX_PATH if RVC_INDEX_PATH else "")
                self.rvc = rvc
                print(f"[SUCCESS] Model {RVC_MODEL_PATH} dimuat!")
            else:
                print(f"[WARN] File model tidak ditemukan di {RVC_MODEL_PATH}")
            if RVC_INDEX_PATH:
                print(f"[INIT] Index RVC terdeteksi di {RVC_INDEX_PATH}, akan digunakan.")
            else:
                print("[WARN] Index RVC tidak ditemukan, konversi akan berjalan tanpa index.")
        except ModuleNotFoundError as e:
            if getattr(e, "name", "") == "rvc_python" or "rvc_python" in str(e):
                print("[WARN] RVC nonaktif (modul rvc_python belum terpasang). TTS akan berjalan tanpa konversi suara.")
            else:
                raise
        except Exception as e:
            print(f"[WARN] Inisialisasi RVC gagal: {e}")

    @contextlib.contextmanager
    def _maybe_quiet_rvc(self):
        if not QUIET_RVC_LOGS:
            yield
            return
        
        with self.rvc_lock:
            with open(os.devnull, "w") as devnull:
                with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                    yield

    def _add_natural_breath(self, audio_data, sample_rate=44100):
        if not ENABLE_NATURAL_BREATH:
            return audio_data
        
        audio = np.asarray(audio_data, dtype=np.float32)
        breath_duration = int(sample_rate * 0.08)
        breath = np.random.normal(0, 0.002, breath_duration).astype(np.float32)
        breath *= np.hanning(breath_duration)
        breath *= 0.15
        
        audio = np.concatenate([breath, audio, breath])
        return audio

    def _apply_voice_warmth(self, audio_data, sample_rate=44100):
        if not ENABLE_VOICE_WARMTH:
            return audio_data
        
        audio = np.asarray(audio_data, dtype=np.float32)
        
        try:
            sos_low = signal.butter(2, 180, 'high', fs=sample_rate, output='sos')
            audio = signal.sosfilt(sos_low, audio)
            
            sos_warmth = signal.butter(1, [250, 4500], btype='band', fs=sample_rate, output='sos')
            warm_signal = signal.sosfilt(sos_warmth, audio)
            audio = audio * 0.75 + warm_signal * 0.25
            
            audio = np.tanh(audio * 1.05) * 0.92
        except:
            pass
        
        return audio

    def _smooth_audio_transitions(self, audio_data, sample_rate=44100):
        if not ENABLE_SMOOTH_TRANSITIONS:
            return audio_data
        
        audio = np.asarray(audio_data, dtype=np.float32)
        
        try:
            sos = signal.butter(3, 7200, 'low', fs=sample_rate, output='sos')
            audio = signal.sosfilt(sos, audio)
        except:
            pass
        
        fade_duration = int(sample_rate * 0.008)
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
        audio = audio * 0.93
        
        try:
            b, a = signal.butter(2, [200, 4200], btype='band', fs=sample_rate)
            audio = signal.filtfilt(b, a, audio)
        except:
            pass
        
        return audio

    def _get_pitch_stats(self, audio_path):
        try:
            import parselmouth
        except Exception:
            return None

        snd = parselmouth.Sound(audio_path)
        pitch = snd.to_pitch(time_step=0.008, pitch_floor=120, pitch_ceiling=380)
        freqs = pitch.selected_array["frequency"]
        freqs = freqs[freqs > 0]
        if freqs.size == 0:
            return {
                "median": 185.0,
                "p10": 165.0,
                "p90": 215.0,
                "floor": 120.0,
                "ceiling": 380.0,
                "duration": float(snd.get_total_duration()),
            }
        return {
            "median": float(np.median(freqs)),
            "p10": float(np.percentile(freqs, 10)),
            "p90": float(np.percentile(freqs, 90)),
            "mean": float(np.mean(freqs)),
            "std": float(np.std(freqs)),
            "floor": 120.0,
            "ceiling": 380.0,
            "duration": float(snd.get_total_duration()),
        }

    def _detect_indonesian_patterns(self, text):
        patterns = {
            'humble_words': ['mohon', 'maaf', 'permisi', 'silakan', 'terima kasih', 'baik', 'tolong'],
            'polite_particles': [' ya', ' kok', ' sih', ' dong', ' deh', ' lho', ' nih'],
            'questions': ['apa', 'bagaimana', 'kenapa', 'mengapa', 'siapa', 'kapan', 'dimana', 'berapa'],
            'emphasis': ['sangat', 'sekali', 'banget', 'benar', 'pasti'],
        }
        
        text_lower = text.lower()
        detected = {
            'is_humble': any(word in text_lower for word in patterns['humble_words']),
            'has_particle': any(particle in text_lower for particle in patterns['polite_particles']),
            'is_question': any(q in text_lower for q in patterns['questions']) or '?' in text,
            'is_statement': '.' in text and '?' not in text,
            'has_emphasis': any(emp in text_lower for emp in patterns['emphasis']),
        }
        
        return detected

    def _apply_casual_f0_file(self, input_wav_path, output_wav_path, text, emotion, ref_audio_path=None):
        if not ENABLE_CASUAL_F0:
            return False
        try:
            import parselmouth
            from parselmouth.praat import call
        except Exception:
            return False

        ref_path = ref_audio_path
        if not ref_path and os.path.exists(CASUAL_REF_AUDIO_PATH):
            ref_path = CASUAL_REF_AUDIO_PATH

        src_stats = self._get_pitch_stats(input_wav_path) or {}
        ref_stats = self._get_pitch_stats(ref_path) if ref_path and os.path.exists(ref_path) else None

        base_median = float((ref_stats or src_stats).get("median", 185.0))
        base_p10 = float((ref_stats or src_stats).get("p10", base_median * 0.89))
        base_p90 = float((ref_stats or src_stats).get("p90", base_median * 1.16))
        base_range = max(15.0, base_p90 - base_p10)
        duration = float(src_stats.get("duration", 0))
        if duration <= 0:
            return False

        patterns = self._detect_indonesian_patterns(text or "")

        snd = parselmouth.Sound(input_wav_path)
        time_step = 0.008
        floor = 120.0
        ceiling = 380.0
        manipulation = call(snd, "To Manipulation", time_step, floor, ceiling)
        pitch_tier = call(manipulation, "Extract pitch tier")
        call(pitch_tier, "Remove points between", 0, duration)

        rng = np.random.default_rng()
        phase1 = float(rng.uniform(0, 2 * np.pi))
        phase2 = float(rng.uniform(0, 2 * np.pi))
        phase3 = float(rng.uniform(0, 2 * np.pi))
        wobble_hz = float(rng.uniform(0.55, 0.85))
        wobble2_hz = wobble_hz * float(rng.uniform(0.30, 0.50))
        micro_wobble_hz = float(rng.uniform(4.5, 6.5))

        em = (emotion or "").strip().lower()
        emo_bias = 0.0
        emo_amp = 1.0
        emo_micro = 0.008
        
        if patterns['is_humble']:
            emo_bias = -0.022
            emo_amp = 0.88
            emo_micro = 0.005
        elif em == "happy":
            emo_bias = 0.012
            emo_amp = 1.10
            emo_micro = 0.012
        elif em == "sad":
            emo_bias = -0.028
            emo_amp = 0.85
            emo_micro = 0.004
        elif em == "surprised":
            emo_bias = 0.025
            emo_amp = 1.15
            emo_micro = 0.015
        elif em == "oh":
            emo_bias = -0.012
            emo_amp = 0.92
            emo_micro = 0.006

        is_question = patterns['is_question']
        is_statement = patterns['is_statement']
        has_particle = patterns['has_particle']
        has_emphasis = patterns['has_emphasis']

        amp = min(0.048, max(0.015, (base_range / max(140.0, base_median)) * 0.058)) * emo_amp
        
        if has_particle:
            amp *= 0.94
        if has_emphasis:
            amp *= 1.08
        
        dt = 0.018
        t = 0.0
        time_points = []
        freq_points = []
        
        while t <= duration:
            mult = 1.0 + emo_bias
            mult += amp * np.sin(2 * np.pi * wobble_hz * t + phase1)
            mult += (amp * 0.40) * np.sin(2 * np.pi * wobble2_hz * t + phase2)
            mult += emo_micro * np.sin(2 * np.pi * micro_wobble_hz * t + phase3)
            
            if not is_question and not is_statement:
                mult += 0.010 * np.sin(2 * np.pi * 0.25 * t)
            
            if is_question and t > max(0, duration - 0.65):
                progress = (t - (duration - 0.65)) / 0.65
                mult += 0.058 * (progress ** 0.8)
            
            if is_statement and t > max(0, duration - 0.50):
                progress = (t - (duration - 0.50)) / 0.50
                mult -= 0.038 * (progress ** 1.2)
            
            if has_particle and t > max(0, duration - 0.35):
                progress = (t - (duration - 0.35)) / 0.35
                mult -= 0.018 * progress
            
            if has_emphasis and 0.15 < t < min(duration * 0.6, duration - 0.2):
                mult += 0.015 * np.sin(2 * np.pi * 1.2 * t)
            
            freq = base_median * mult
            freq = max(floor, min(ceiling, freq))
            
            time_points.append(t)
            freq_points.append(freq)
            t += dt
        
        if len(time_points) > 5:
            time_arr = np.array(time_points)
            freq_arr = np.array(freq_points)
            
            freq_smooth = gaussian_filter1d(freq_arr, sigma=1.2)
            
            cs = CubicSpline(time_arr, freq_smooth)
            
            smooth_times = np.linspace(0, duration, int(duration / 0.015))
            smooth_freqs = cs(smooth_times)
            
            smooth_freqs = np.clip(smooth_freqs, floor, ceiling)
            
            for t_val, f_val in zip(smooth_times, smooth_freqs):
                call(pitch_tier, "Add point", float(t_val), float(f_val))
        else:
            for t_val, f_val in zip(time_points, freq_points):
                call(pitch_tier, "Add point", float(t_val), float(f_val))

        call([manipulation, pitch_tier], "Replace pitch tier")
        resynth = call(manipulation, "Get resynthesis (overlap-add)")
        resynth.save(output_wav_path, "WAV")
        return True

    def _normalize_tts_text(self, text):
        s = (text or "").strip()
        s = re.sub(r'[^\w\s\.,!\?;:\-\'\"]', '', s)
        s = " ".join(s.split())
        if not s:
            return ""
        s = s.replace("…", "...")
        s = s.replace("--", ",")
        if s[-1] not in ".!?":
            s += "."
        return s

    def _silence_wav_bytes(self, duration_s=0.25, sample_rate=44100):
        sr = int(sample_rate)
        n = max(1, int(sr * float(duration_s)))
        x = np.zeros(n, dtype=np.float32)
        buf = io.BytesIO()
        sf.write(buf, x, sr, format="WAV", subtype="PCM_16")
        return buf.getvalue()

    def _tts_prosody(self, emotion, text=""):
        patterns = self._detect_indonesian_patterns(text)
        
        if patterns['is_humble']:
            return "-2%", "-1%", "-4Hz"
        
        em = (emotion or "").strip().lower()
        if em == "happy":
            return "+6%", "+1%", "+5Hz"
        if em == "sad":
            return "-7%", "-3%", "-5Hz"
        if em == "surprised":
            return "+9%", "+1%", "+11Hz"
        if em == "oh":
            return "-3%", "-1%", "-2Hz"
        return "+0%", "+0%", "+0Hz"

    def _parse_signed_int(self, s, suffix):
        if s is None:
            return 0
        v = str(s).strip()
        if not v.endswith(suffix):
            return 0
        v = v[: -len(suffix)].strip()
        if not v:
            return 0
        try:
            return int(v)
        except Exception:
            return 0

    def _format_signed_int(self, value, suffix):
        try:
            iv = int(value)
        except Exception:
            iv = 0
        sign = "+" if iv >= 0 else ""
        return f"{sign}{iv}{suffix}"

    def _split_tts_segments(self, text):
        s = (text or "").strip()
        if not s:
            return []
        parts = re.findall(r"[^.!?;,:\n]+[.!?;,:\n]?", s, flags=re.UNICODE)
        out = []
        for p in parts:
            seg = p.strip()
            if not seg:
                continue
            last = seg[-1]
            if last in ".!?":
                pause_ms = 260 if last == "." else 300
            elif last in ",;:":
                pause_ms = 140
            elif last == "\n":
                pause_ms = 220
                seg = seg.rstrip("\n").strip()
            else:
                pause_ms = 90
            if seg:
                out.append((seg, pause_ms))
        return out

    def _build_ssml(self, text, voice, emotion):
        rate, volume, pitch_hz = self._tts_prosody(emotion, text)
        base_rate = self._parse_signed_int(rate, "%")
        base_pitch = self._parse_signed_int(pitch_hz, "Hz")

        segments = self._split_tts_segments(text)
        if not segments:
            segments = [(text, 200)]

        body_parts = []
        for seg_text, pause_ms in segments:
            cleaned = " ".join(seg_text.split())
            if not cleaned:
                continue
            esc = html.escape(cleaned)
            seg_rate = base_rate
            if len(cleaned) > 120:
                seg_rate -= 5
            elif len(cleaned) > 80:
                seg_rate -= 2
            elif len(cleaned) < 30:
                seg_rate += 1

            seg_pitch = base_pitch
            if cleaned.endswith("!"):
                seg_pitch += 4
            elif cleaned.endswith("?"):
                seg_pitch += 6

            rate_attr = self._format_signed_int(seg_rate, "%")
            pitch_attr = self._format_signed_int(seg_pitch, "Hz")
            pause = max(80, min(int(pause_ms), 800))
            body_parts.append(
                f'<prosody rate="{rate_attr}" pitch="{pitch_attr}" volume="{volume}">{esc}</prosody><break time="{pause}ms"/>'
            )

        body = "".join(body_parts)
        ssml = (
            '<speak version="1.0" '
            'xmlns="http://www.w3.org/2001/10/synthesis" '
            'xml:lang="id-ID">'
            f'<voice name="{html.escape(voice)}">{body}</voice>'
            "</speak>"
        )
        return ssml

    def _edge_tts_save(self, text, voice, emotion, out_path):
        rate, volume, pitch_hz = self._tts_prosody(emotion, text)
        segments = self._split_tts_segments(text)
        if segments:
            parts = []
            for seg_text, pause_ms in segments:
                cleaned = " ".join((seg_text or "").split())
                if not cleaned:
                    continue
                parts.append(cleaned)
                if pause_ms >= 260:
                    parts.append("...")
                elif pause_ms >= 140:
                    parts.append(",")
            speak_text = " ".join(parts)
            speak_text = re.sub(r"\s+,", ",", speak_text)
            speak_text = re.sub(r"\s+\.\.\.", "...", speak_text)
            speak_text = re.sub(r"\s+", " ", speak_text).strip()
        else:
            speak_text = text
        asyncio.run(edge_tts.Communicate(speak_text, voice, rate=rate, volume=volume, pitch=pitch_hz).save(out_path))
        return False

    def _ensure_stt(self):
        if self.stt_model is not None and self.recognizer is not None:
            return
        print("[INIT] Memuat Telinga (Whisper)...")
        self.stt_model = WhisperModel("base", device=DEVICE_STT, compute_type="int8")
        self.recognizer = sr.Recognizer()

    def warmup_rvc(self):
        if self.rvc is None:
            return False
        input_wav = os.path.join(BASE_DIR, "rvc_warmup_in.wav")
        output_wav = os.path.join(BASE_DIR, "rvc_warmup_out.wav")
        try:
            sr_out = 44100
            x = np.zeros(int(sr_out * 0.25), dtype=np.float32)
            sf.write(input_wav, x, sr_out)
            with self._maybe_quiet_rvc():
                self.rvc.set_params(
                    f0method=RVC_F0_METHOD,
                    f0up_key=PITCH_SHIFT,
                    index_rate=RVC_INDEX_RATE if RVC_INDEX_PATH else 0,
                    filter_radius=RVC_FILTER_RADIUS,
                    rms_mix_rate=RVC_RMS_MIX_RATE,
                    protect=RVC_PROTECT,
                )
                self.rvc.infer_file(input_wav, output_wav)
            return True
        finally:
            for p in (input_wav, output_wav):
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass

    def listen(self):
        self._ensure_stt()
        with sr.Microphone() as source:
            print("\n[LISTENING] Silakan bicara...")
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

    async def speak_anime(self, text):
        print(f"[AI]: {text}")
        
        temp_tts = "temp_tts.mp3"
        temp_tts_wav = "temp_tts.wav"
        temp_tts_casual_wav = "temp_tts_casual.wav"
        norm_text = self._normalize_tts_text(text)
        self._edge_tts_save(norm_text, TTS_VOICE, None, temp_tts)
        
        output_rvc = "output_anime.wav"

        if self.rvc is None:
            self.play_audio(temp_tts)
            return

        try:
            import ffmpeg
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            (
                ffmpeg
                .input(temp_tts)
                .output(temp_tts_wav, ac=1, ar=44100, format="wav", loglevel="error")
                .overwrite_output()
                .run(cmd=ffmpeg_exe)
            )
            input_for_rvc = temp_tts_wav
            if self._apply_casual_f0_file(temp_tts_wav, temp_tts_casual_wav, norm_text, None):
                input_for_rvc = temp_tts_casual_wav
            with self._maybe_quiet_rvc():
                self.rvc.set_params(
                    f0up_key=PITCH_SHIFT,
                    f0method=RVC_F0_METHOD,
                    index_rate=RVC_INDEX_RATE if RVC_INDEX_PATH else 0,
                    filter_radius=RVC_FILTER_RADIUS,
                    rms_mix_rate=RVC_RMS_MIX_RATE,
                    protect=RVC_PROTECT,
                    f0autotune=RVC_F0_AUTOTUNE,
                )
                self.rvc.infer_file(input_for_rvc, output_rvc)

            audio_data, sr = sf.read(output_rvc, dtype='float32')
            audio_data = self._smooth_audio_transitions(audio_data, sr)
            audio_data = self._apply_humble_characteristics(audio_data, sr)
            audio_data = self._apply_voice_warmth(audio_data, sr)
            audio_data = self._add_natural_breath(audio_data, sr)
            sf.write(output_rvc, audio_data, sr)

            self.play_audio(output_rvc)

        except Exception as e:
            print(f"[WARN] RVC infer gagal: {e}")
            self.play_audio(temp_tts)

    def play_audio(self, file_path):
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.quit()

        if os.path.exists("temp_tts.mp3"): os.remove("temp_tts.mp3")
        if os.path.exists("temp_tts.wav"): os.remove("temp_tts.wav")
        if os.path.exists("temp_tts_casual.wav"): os.remove("temp_tts_casual.wav")
        if os.path.exists("output_anime.wav"): os.remove("output_anime.wav")

    def transcribe_file(self, audio_path):
        self._ensure_stt()
        segments, _ = self.stt_model.transcribe(audio_path, language="id")
        return "".join([s.text for s in segments]).strip()

    def synthesize_bytes(self, text, voice=None, pitch=None, emotion=None, f0method=None):
        styled_text = self._normalize_tts_text(text)
        if not styled_text:
            return self._silence_wav_bytes(), "audio/wav"
        selected_voice = voice or TTS_VOICE
        if pitch is None:
            selected_pitch = PITCH_SHIFT
        else:
            try:
                selected_pitch = int(pitch)
            except (TypeError, ValueError):
                selected_pitch = PITCH_SHIFT
        selected_pitch = max(-24, min(24, selected_pitch))

        temp_tts = os.path.join(BASE_DIR, "temp_tts.mp3")
        temp_tts_wav = os.path.join(BASE_DIR, "temp_tts.wav")
        temp_tts_casual_wav = os.path.join(BASE_DIR, "temp_tts_casual.wav")
        output_rvc = os.path.join(BASE_DIR, "output_anime.wav")
        try:
            self._edge_tts_save(styled_text, selected_voice, emotion, temp_tts)
            if self.rvc is not None:
                try:
                    import ffmpeg
                    import imageio_ffmpeg
                    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                    (
                        ffmpeg
                        .input(temp_tts)
                        .output(temp_tts_wav, ac=1, ar=44100, format="wav", loglevel="error")
                        .overwrite_output()
                        .run(cmd=ffmpeg_exe)
                    )
                    input_for_rvc = temp_tts_wav
                    if self._apply_casual_f0_file(temp_tts_wav, temp_tts_casual_wav, styled_text, emotion):
                        input_for_rvc = temp_tts_casual_wav
                    with self._maybe_quiet_rvc():
                        self.rvc.set_params(
                            f0up_key=selected_pitch,
                            f0method=f0method or RVC_F0_METHOD,
                            index_rate=RVC_INDEX_RATE if RVC_INDEX_PATH else 0,
                            filter_radius=RVC_FILTER_RADIUS,
                            rms_mix_rate=RVC_RMS_MIX_RATE,
                            protect=RVC_PROTECT,
                            f0autotune=RVC_F0_AUTOTUNE,
                        )
                        self.rvc.infer_file(input_for_rvc, output_rvc)
                    
                    audio_data, sr = sf.read(output_rvc, dtype='float32')
                    audio_data = self._smooth_audio_transitions(audio_data, sr)
                    audio_data = self._apply_humble_characteristics(audio_data, sr)
                    audio_data = self._apply_voice_warmth(audio_data, sr)
                    audio_data = self._add_natural_breath(audio_data, sr)
                    sf.write(output_rvc, audio_data, sr)
                    
                    with open(output_rvc, "rb") as f:
                        audio_bytes = f.read()
                    return audio_bytes, "audio/wav"
                except Exception as e:
                    print(f"[WARN] RVC infer gagal: {e}")
                    with open(temp_tts, "rb") as f:
                        audio_bytes = f.read()
                    return audio_bytes, "audio/mpeg"
            with open(temp_tts, "rb") as f:
                audio_bytes = f.read()
            return audio_bytes, "audio/mpeg"
        finally:
            if os.path.exists(temp_tts):
                os.remove(temp_tts)
            if os.path.exists(temp_tts_wav):
                os.remove(temp_tts_wav)
            if os.path.exists(temp_tts_casual_wav):
                os.remove(temp_tts_casual_wav)
            if os.path.exists(output_rvc):
                os.remove(output_rvc)

if __name__ == "__main__":
    bot = AnimeVoiceAssistant()
    
    try:
        while True:
            user_input = bot.listen()
            
            if user_input:
                if "halo" in user_input.lower():
                    response = "Halo juga! Senang bertemu denganmu."
                elif "siapa" in user_input.lower():
                    response = "Aku adalah asisten virtual anime kamu."
                elif "keluar" in user_input.lower():
                    asyncio.run(bot.speak_anime("Sampai jumpa lagi, Master!"))
                    break
                else:
                    response = user_input 
                
                asyncio.run(bot.speak_anime(response))
                
    except KeyboardInterrupt:
        print("\nBerhenti.")