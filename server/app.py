import os
import json
import pickle
import traceback
import threading
import logging
import re
import tensorflow as tf
from flask import Flask, request, jsonify
from flask_cors import CORS
from tensorflow.keras.models import load_model
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

from agent_core import AgentOrchestrator
from voice import AnimeVoiceAssistant
import base64
import tempfile

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

logging.getLogger("werkzeug").setLevel(logging.ERROR)
tf.get_logger().setLevel("ERROR")
logging.raiseExceptions = False

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "server.log")
_file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
_file_handler.setLevel(logging.INFO)
_file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logging.getLogger().addHandler(_file_handler)
app.logger.addHandler(_file_handler)
app.logger.setLevel(logging.INFO)

def _safe_log_exception(prefix, e):
    try:
        app.logger.exception("%s: %s", prefix, e)
    except Exception:
        try:
            with open(os.path.join(LOG_DIR, "server_fallback.log"), "a", encoding="utf-8") as f:
                f.write(f"{prefix}: {repr(e)}\n")
                f.write(traceback.format_exc())
                f.write("\n")
        except Exception:
            pass

app.logger.info("--- System Init: Loading Assets ---")

def _sanitize_reply_for_tts(text):
    s = (text or "")
    s = re.sub(r"```[\s\S]*?```", " ", s)
    s = re.sub(r"`[^`]*`", " ", s)
    s = re.sub(r"^\s*\[[A-Z_]{2,}\][^\n]*$", " ", s, flags=re.MULTILINE)
    s = re.sub(r"\[[^\]]+\]", " ", s)
    s = re.sub(r"https?://\S+", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\bwww\.\S+", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"[A-Za-z]:\\[^\s]+", " ", s)
    s = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", " ", s)
    s = re.sub(r"\b\d{3}-\d{3}-\d{3}\b", " ", s)
    s = re.sub(r"\b\w+\.(?:py|js|ts|tsx|jsx|svelte|html|css|json|md|txt)\b", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\b\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?)?\b", " ", s)
    s = re.sub(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", " ", s)
    s = re.sub(r"\b(?:python|pip|tensorflow|torch|pygame|flask|werkzeug|whisper|rvc|ffmpeg)\b", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(?:warning|traceback|error|info|debug|init)\b\s*[:\-]?", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(?:http|https)\b", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(?:PIN|IP)\b", " ", s)
    s = re.sub(r"\.{2,}", ". ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.lstrip(" .,:;|-")
    if not s:
        return ""
    if s[-1] not in ".!?":
        s += "."
    return s

class SafeKerasUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module in ("keras.src.preprocessing.text", "keras.src.legacy.preprocessing.text", "keras.preprocessing.text"):
            module = "tensorflow.keras.preprocessing.text"
        elif module.startswith("keras.src.legacy"):
            module = "tensorflow.keras"
        elif module.startswith("keras.") and not module.startswith("keras.src"):
            module = module.replace("keras.", "tensorflow.keras.", 1)
        return super().find_class(module, name)

class CompatUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module.startswith("numpy._core"):
            module = module.replace("numpy._core", "numpy.core", 1)
        return super().find_class(module, name)

try:

    model_path = os.path.join(BASE_DIR, 'models', 'chatbot_model.h5')
    token_path = os.path.join(BASE_DIR, 'models', 'tokenizer.pickle')
    label_path = os.path.join(BASE_DIR, 'models', 'label_encoder.pickle')
    data_path = os.path.join(BASE_DIR, 'data', 'intents.json')

    with open(token_path, 'rb') as handle:
        tokenizer = SafeKerasUnpickler(handle).load()
    with open(label_path, 'rb') as ecn_file:
        lbl_encoder = CompatUnpickler(ecn_file).load()

    vocab_size = None
    try:
        import h5py
        with h5py.File(model_path, "r") as f:
            vocab_size = int(f["model_weights"]["embedding"]["embedding"]["embeddings"].shape[0])
    except Exception:
        vocab_size = None

    vocab_size = vocab_size or getattr(tokenizer, "num_words", None) or (len(getattr(tokenizer, "word_index", {})) + 1)
    num_labels = len(getattr(lbl_encoder, "classes_", []))
    try:
        model = load_model(model_path, compile=False)
    except Exception:
        input_layer = tf.keras.layers.Input(shape=(30,), name="input_layer")
        x = tf.keras.layers.Embedding(vocab_size, 128, name="embedding")(input_layer)
        x = tf.keras.layers.SpatialDropout1D(0.4, name="spatial_dropout1d")(x)
        x = tf.keras.layers.Bidirectional(
            tf.keras.layers.LSTM(64, return_sequences=True, name="lstm"),
            name="bidirectional",
        )(x)
        avg_pool = tf.keras.layers.GlobalAveragePooling1D(name="global_average_pooling1d")(x)
        max_pool = tf.keras.layers.GlobalMaxPooling1D(name="global_max_pooling1d")(x)
        merged = tf.keras.layers.Concatenate(name="concatenate")([avg_pool, max_pool])
        x = tf.keras.layers.Dense(128, activation="relu", name="dense")(merged)
        x = tf.keras.layers.Dropout(0.5, name="dropout")(x)
        output_layer = tf.keras.layers.Dense(num_labels, activation="softmax", name="dense_1")(x)
        model = tf.keras.models.Model(inputs=input_layer, outputs=output_layer)
        try:
            model.load_weights(model_path)
        except Exception:
            import h5py
            with h5py.File(model_path, "r") as f:
                mw = f["model_weights"]
                model.get_layer("embedding").set_weights([mw["embedding"]["embedding"]["embeddings"][()]])
                bi = mw["bidirectional"]["bidirectional"]
                fw = bi["forward_lstm"]["lstm_cell"]
                bw = bi["backward_lstm"]["lstm_cell"]
                model.get_layer("bidirectional").set_weights([
                    fw["kernel"][()],
                    fw["recurrent_kernel"][()],
                    fw["bias"][()],
                    bw["kernel"][()],
                    bw["recurrent_kernel"][()],
                    bw["bias"][()],
                ])
                model.get_layer("dense").set_weights([
                    mw["dense"]["dense"]["kernel"][()],
                    mw["dense"]["dense"]["bias"][()],
                ])
                model.get_layer("dense_1").set_weights([
                    mw["dense_1"]["dense_1"]["kernel"][()],
                    mw["dense_1"]["dense_1"]["bias"][()],
                ])
    with open(data_path, encoding='utf-8') as file:
        data = json.load(file)

    intent_map = {i['tag']: i['responses'] for i in data['intents']}

    factory = StemmerFactory()
    stemmer = factory.create_stemmer()

    bot_agent = AgentOrchestrator(
        model=model,
        tokenizer=tokenizer,
        lbl_encoder=lbl_encoder,
        intent_map=intent_map,
        stemmer=stemmer,
        max_len=30
    )
    app.logger.info("--- System Ready: Agent Orchestrator Online ---")

except Exception as e:
    _safe_log_exception("CRITICAL ERROR LOADING ASSETS", e)
    exit(1)

voice_assistant = None
voice_assistant_lock = threading.Lock()
voice_warmup_lock = threading.Lock()
voice_warmup_state = {
    "started": False,
    "done": False,
    "ok": False,
    "error": None,
}

def get_voice():
    global voice_assistant
    if voice_assistant is not None:
        return voice_assistant
    with voice_assistant_lock:
        if voice_assistant is None:
            voice_assistant = AnimeVoiceAssistant()
        return voice_assistant

def _voice_warmup_worker():
    global voice_warmup_state
    try:
        va = get_voice()
        ok = False
        if hasattr(va, "warmup_rvc"):
            ok = bool(va.warmup_rvc())
        rvc_device = getattr(va, "rvc_device", None)
        with voice_warmup_lock:
            voice_warmup_state = {
                "started": True,
                "done": True,
                "ok": ok,
                "error": None,
                "rvc_device": rvc_device,
            }
    except Exception as e:
        with voice_warmup_lock:
            voice_warmup_state = {
                "started": True,
                "done": True,
                "ok": False,
                "error": str(e),
                "rvc_device": None,
            }

def start_voice_warmup():
    with voice_warmup_lock:
        if voice_warmup_state["started"]:
            return
        voice_warmup_state["started"] = True
    t = threading.Thread(target=_voice_warmup_worker, daemon=True)
    t.start()

@app.route('/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.get_json(silent=True) or {}
        user_input = data.get('message', '')
        session_id = data.get('session_id', 'default_user')

        if "reset" in user_input.lower().strip():
            bot_agent.reset_session(session_id)
            return jsonify({
                "reply": "Sesi percakapan telah direset.",
                "emotion": "neutral",
                "debug": {}
            })

        if not user_input.strip():
            return jsonify({
                "reply": "Silakan ketik sesuatu untuk memulai percakapan.",
                "emotion": "neutral",
                "debug": {}
            })

        result = bot_agent.process_query(user_input, session_id)
        if isinstance(result, dict) and "reply" in result:
            result["reply_tts"] = _sanitize_reply_for_tts(result.get("reply"))
        return jsonify(result)

    except Exception as e:
        _safe_log_exception("Error processing request", e)
        return jsonify({
            "reply": "Terjadi kesalahan internal pada server.",
            "emotion": "sad",
            "debug": str(e)
        }), 500

@app.route('/tts', methods=['POST'])
def tts_endpoint():
    try:
        data = request.get_json(silent=True) or {}
        text = data.get('text', '').strip()
        if not text:
            return jsonify({"error": "Text kosong"}), 400
        va = get_voice()
        voice = data.get('voice')
        pitch = data.get('pitch')
        emotion = data.get('emotion')
        f0method = data.get('f0method')
        debug_tts = bool(data.get("debug_tts"))
        audio_bytes, mime = va.synthesize_bytes(text, voice=voice, pitch=pitch, emotion=emotion, f0method=f0method)
        payload = {
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "mime": mime,
            "rvc_applied": mime == "audio/wav",
            "rvc_device": getattr(va, "rvc_device", None),
            "voice": voice or "",
            "pitch": pitch,
            "f0method": f0method
        }
        if debug_tts:
            payload["tts_text_received"] = text
            try:
                payload["tts_text_normalized"] = va._normalize_tts_text(text)
            except Exception:
                payload["tts_text_normalized"] = None
        return jsonify(payload)
    except Exception as e:
        safe_print(f"TTS error: {e}")
        _safe_log_exception("TTS error", e)
        return jsonify({"error": str(e)}), 500

@app.route('/warmup', methods=['GET', 'POST'])
def warmup_endpoint():
    start_voice_warmup()
    with voice_warmup_lock:
        payload = dict(voice_warmup_state)
    return jsonify(payload)

@app.route('/stt', methods=['POST'])
def stt_endpoint():
    try:
        if 'audio' in request.files:
            f = request.files['audio']
            suffix = ".wav"
            try:
                original = getattr(f, "filename", "") or ""
                _, ext = os.path.splitext(original)
                if ext and len(ext) <= 8:
                    suffix = ext
            except Exception:
                pass
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                f.save(tmp.name)
                temp_path = tmp.name
        else:
            data = request.get_json(silent=True) or {}
            audio_b64 = data.get('audio_base64')
            if not audio_b64:
                return jsonify({"error": "Tidak ada audio"}), 400
            raw = base64.b64decode(audio_b64)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(raw)
                temp_path = tmp.name
        va = get_voice()
        text = va.transcribe_file(temp_path)
        try:
            os.remove(temp_path)
        except Exception:
            pass
        return jsonify({"text": text})
    except Exception as e:
        _safe_log_exception("STT error", e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    start_voice_warmup()
    app.run(debug=True, port=8080, use_reloader=False)
