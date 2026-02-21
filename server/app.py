# server/app.py
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
import base64
import tempfile
from agent_core import AgentOrchestrator
from voice import AnimeVoiceAssistant

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
    except Exception: pass

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
    s = re.sub(r"\b\w+\.(?:py|js|ts|tsx|jsx|svelte|html|css|json|md|txt)\b", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    if not s: return ""
    if s[-1] not in ".!?": s += "."
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

    vocab_size = getattr(tokenizer, "num_words", None) or (len(getattr(tokenizer, "word_index", {})) + 1)
    num_labels = len(getattr(lbl_encoder, "classes_", []))
    try:
        model = load_model(model_path, compile=False)
    except Exception:
        input_layer = tf.keras.layers.Input(shape=(30,), name="input_layer")
        x = tf.keras.layers.Embedding(vocab_size, 128, name="embedding")(input_layer)
        x = tf.keras.layers.SpatialDropout1D(0.4, name="spatial_dropout1d")(x)
        x = tf.keras.layers.Bidirectional(tf.keras.layers.LSTM(64, return_sequences=True, name="lstm"), name="bidirectional")(x)
        avg_pool = tf.keras.layers.GlobalAveragePooling1D(name="global_average_pooling1d")(x)
        max_pool = tf.keras.layers.GlobalMaxPooling1D(name="global_max_pooling1d")(x)
        merged = tf.keras.layers.Concatenate(name="concatenate")([avg_pool, max_pool])
        x = tf.keras.layers.Dense(128, activation="relu", name="dense")(merged)
        x = tf.keras.layers.Dropout(0.5, name="dropout")(x)
        output_layer = tf.keras.layers.Dense(num_labels, activation="softmax", name="dense_1")(x)
        model = tf.keras.models.Model(inputs=input_layer, outputs=output_layer)
        model.load_weights(model_path)

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
    app.logger.info("--- System Ready ---")

except Exception as e:
    _safe_log_exception("CRITICAL ERROR", e)
    exit(1)

voice_assistant = None
voice_assistant_lock = threading.Lock()
voice_warmup_lock = threading.Lock()
voice_warmup_state = {"started": False, "done": False, "ok": False, "error": None}

def get_voice():
    global voice_assistant
    if voice_assistant is not None: return voice_assistant
    with voice_assistant_lock:
        if voice_assistant is None:
            voice_assistant = AnimeVoiceAssistant()
        return voice_assistant

def _voice_warmup_worker():
    global voice_warmup_state
    try:
        va = get_voice()
        ok = bool(va.warmup_rvc())
        with voice_warmup_lock:
            voice_warmup_state = {"started": True, "done": True, "ok": ok, "error": None}
    except Exception as e:
        with voice_warmup_lock:
            voice_warmup_state = {"started": True, "done": True, "ok": False, "error": str(e)}

def start_voice_warmup():
    with voice_warmup_lock:
        if voice_warmup_state["started"]: return
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
            return jsonify({"reply": "Sesi direset.", "emotion": "neutral"})
        if not user_input.strip():
            return jsonify({"reply": "...", "emotion": "neutral"})
        result = bot_agent.process_query(user_input, session_id)
        if isinstance(result, dict) and "reply" in result:
            result["reply_tts"] = _sanitize_reply_for_tts(result.get("reply"))
        return jsonify(result)
    except Exception as e:
        return jsonify({"reply": "Error internal.", "emotion": "sad", "debug": str(e)}), 500

@app.route('/tts', methods=['POST'])
def tts_endpoint():
    try:
        data = request.get_json(silent=True) or {}
        text = data.get('text', '').strip()
        if not text: return jsonify({"error": "No text"}), 400
        va = get_voice()
        audio_bytes, mime = va.synthesize_bytes(text, emotion=data.get('emotion'))
        return jsonify({
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "mime": mime
        })
    except Exception as e:
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
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                f.save(tmp.name)
                temp_path = tmp.name
        else:
            data = request.get_json(silent=True) or {}
            raw = base64.b64decode(data.get('audio_base64'))
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(raw)
                temp_path = tmp.name
        va = get_voice()
        text = va.transcribe_file(temp_path)
        try: os.remove(temp_path)
        except: pass
        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    start_voice_warmup()
    app.run(debug=True, port=8080, use_reloader=False)