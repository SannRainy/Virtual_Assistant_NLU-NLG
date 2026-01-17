# Arsitektur Proyek: AI Virtual Akademik UNIPMA

Repository ini terdiri dari 2 komponen utama:

- `client/`: Frontend web (Svelte + Vite) untuk UI chat + avatar VRM (Three.js).
- `server/`: Backend API (Flask) untuk chat (intent classifier), TTS (Edge-TTS +  RVC), STT (Whisper), dan warmup.

## Struktur Folder

```
ICNN_Project/
  client/
    public/
      AlisaV2.vrm
    src/
      components/
        Avatar.svelte
      utils/
        behaviors.js
      App.svelte
      main.js
      app.css
    package.json
    vite.config.js
    svelte.config.js
    README.md

  server/
    app.py
    agent_core.py
    voice.py
    requirements.txt
    train_engine.py
    generate_dataset.py
    data/
      intents.json
      raw_data.txt
      response_templates.json
    models/
      chatbot_model.h5
      tokenizer.pickle
      label_encoder.pickle
      (RVC assets: *.pth, *.index)
    modelsbackup/
      (backup model training lama)
    utils/
      text_preprocessing.py
      session_manager.py
      response_generator.py
      mock_database.py
      clarification_data.py
      __init__.py

  all-packages.txt
```

## Alur Utama Runtime

### 1) Chat (User → AI)

1. User mengetik di UI (`client/src/App.svelte`).
2. Frontend memanggil `POST /chat` ke backend (`server/app.py`).
3. Backend memproses di `AgentOrchestrator` (`server/agent_core.py`):
   - normalisasi + stemming,
   - inferensi model intent classifier (Keras),
   - pilih tool / template response,
   - return JSON: `reply`, `reply_tts`, `emotion`, `intent`, `confidence`, `debug`.
4. Frontend menampilkan `reply` di chat.

### 2) TTS (AI Reply → Suara)

1. Frontend memanggil `POST /tts` sambil mengirim `text` (umumnya memakai `reply_tts`) + `voice/pitch/emotion`.
2. Backend menjalankan TTS di `server/voice.py`:
   - TTS: `edge_tts` menghasilkan audio.
   - Opsional: RVC voice conversion (jika model RVC aktif).
3. Backend mengembalikan audio base64 + MIME.
4. Frontend memutar audio dan mengirim `isSpeaking` + `speechLevel` ke avatar.

### 3) Avatar (Gerak VRM)

1. `client/src/components/Avatar.svelte` memuat VRM (`public/AlisaV2.vrm`) via `three-vrm`.
2. Avatar merespon:
   - `emotion` → ekspresi (joy/sorrow/surprised/fun/oh).
   - `isSpeaking` + `speechLevel` → mouth/lipsync + head/chest bob halus.
   - idle behavior → gesture ringan (diatur di `client/src/utils/behaviors.js`).

## Endpoint Backend (Flask)

Base URL default di frontend: `http://127.0.0.1:8080`

- `POST /chat`
  - Body: `{ "message": "...", "session_id": "user_1" }`
  - Return: `{ reply, reply_tts, emotion, intent, confidence, debug }`

- `POST /tts`
  - Body: `{ "text": "...", "voice": "...", "pitch": 0, "emotion": "happy" }`
  - Return: `{ audio_base64, mime, ... }`

- `POST /stt`
  - Input bisa file upload (`audio`) atau JSON base64.
  - Return: `{ "text": "..." }`

- `GET|POST /warmup`
  - Trigger warmup pipeline voice/RVC.

## Data & Model

- `server/data/intents.json`: definisi intent + contoh kalimat + respon statis.
- `server/data/response_templates.json`: template jawaban dengan placeholder.
- `server/models/chatbot_model.h5`: model klasifikasi intent (Keras).
- `server/models/tokenizer.pickle` dan `label_encoder.pickle`: tokenizer + label encoder.
- `server/models/*.pth` dan `*.index`: aset RVC untuk voice conversion.

## Modul Penting (server/utils)

- `text_preprocessing.py`: normalisasi teks.
- `session_manager.py`: memory slot per sesi (nim/prodi/semester/dll).
- `response_generator.py`: gabung template + mock db + variasi response.
- `mock_database.py`: sumber data tiruan untuk tool intent.
- `clarification_data.py`: kalimat klarifikasi saat confidence sedang.

## Cara Menjalankan (Dev)

Frontend:

```
cd client
npm install
npm run dev
```

Backend:

```
cd server
pip install -r requirements.txt
python app.py
```

Catatan:
- Frontend mengasumsikan backend aktif di `http://127.0.0.1:8080`.
- Pipeline voice (RVC/Whisper) bisa memakan resource; endpoint `/warmup` dipakai untuk pemanasan.

