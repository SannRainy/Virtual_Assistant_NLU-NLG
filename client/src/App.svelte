<script>
  import { afterUpdate, onMount } from 'svelte';
  import { fade, fly } from 'svelte/transition';
  import Avatar from './components/Avatar.svelte';

  let inputText = "";
  let chatHistory = [];
  let isLoading = false;
  let chatBox; 
  let isAiSpeaking = false; 
  let currentEmotion = "neutral";
  let sessionId = "";
  let ttsVoice = "id-ID-GadisNeural";
  let ttsPitch = 0;
  let ttsF0Method = "rmvpe";
  let autoSpeak = true;
  let useTypewriter = true;
  let isOnline = true;
  let lastError = "";
  let toastText = "";
  let toastTimer = 0;
  let isRecording = false;
  let mediaRecorder = null;
  let recordedChunks = [];
  let mediaStream = null;
  let inputEl;
  let typingInterval;
  let ttsAudio = null;
  let audioContext = null;
  let analyserNode = null;
  let analyserData = null;
  let analyserRaf = 0;
  let mediaSourceNode = null;
  
  let mouthCues = { a: 0, i: 0, u: 0, e: 0, o: 0 }; 

  const apiBase = 'http://127.0.0.1:8080';

  onMount(() => {
    const storedSession = localStorage.getItem("alisa_session_id");
    if (storedSession) {
      sessionId = storedSession;
    } else {
      sessionId = (crypto?.randomUUID?.() || `u_${Math.random().toString(16).slice(2)}_${Date.now()}`);
      localStorage.setItem("alisa_session_id", sessionId);
    }

    try {
      const raw = localStorage.getItem("alisa_chat_history");
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          chatHistory = parsed.map(m => ({
            ...m,
            id: m?.id || (crypto?.randomUUID?.() || `m_${Math.random().toString(16).slice(2)}_${Date.now()}`),
            time: m?.time ? new Date(m.time) : new Date()
          }));
        }
      }
    } catch (e) {}

    const ping = async () => {
      try {
        const res = await fetch(`${apiBase}/warmup`, { method: 'GET' });
        isOnline = res.ok;
        if (res.ok) lastError = "";
      } catch (e) {
        isOnline = false;
        lastError = "Server tidak terhubung";
      }
    };
    ping();
    const id = setInterval(ping, 15000);
    fetch(`${apiBase}/warmup`, { method: 'POST' }).catch(() => {});
    return () => clearInterval(id);
  });

  const scrollToBottom = () => {
    if (chatBox) {
      const distanceFromBottom = chatBox.scrollHeight - chatBox.scrollTop - chatBox.clientHeight;
      if (distanceFromBottom < 140) {
        chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: 'smooth' });
      }
    }
  };

  afterUpdate(() => {
    scrollToBottom();
    if (toastText && toastTimer) {
      clearTimeout(toastTimer);
    }
    if (toastText) {
      toastTimer = setTimeout(() => {
        toastText = "";
        toastTimer = 0;
      }, 2500);
    }
    try {
      const serialized = chatHistory.slice(-80).map(m => ({ ...m, time: m?.time ? m.time.toISOString() : new Date().toISOString() }));
      localStorage.setItem("alisa_chat_history", JSON.stringify(serialized));
    } catch (e) {}
  });

  function toast(message) {
    toastText = message;
  }

  function stopAllAudio() {
    if (ttsAudio) {
      try { ttsAudio.pause(); } catch (e) {}
      ttsAudio = null;
    }
    stopSpeechMeter();
    isAiSpeaking = false;
  }

  function autosizeInput() {
    if (!inputEl) return;
    inputEl.style.height = "0px";
    const next = Math.min(160, Math.max(44, inputEl.scrollHeight));
    inputEl.style.height = `${next}px`;
  }

  function stopSpeechMeter() {
    if (analyserRaf) {
      cancelAnimationFrame(analyserRaf);
      analyserRaf = 0;
    }
    mouthCues = { a: 0, i: 0, u: 0, e: 0, o: 0 };
    try {
      if (mediaSourceNode) mediaSourceNode.disconnect();
    } catch (e) {}
    try {
      if (analyserNode) analyserNode.disconnect();
    } catch (e) {}
    mediaSourceNode = null;
    analyserNode = null;
    analyserData = null;
  }

  async function startSpeechMeter(audioEl) {
    try {
      if (!audioContext) {
        audioContext = new (window.AudioContext || window.AudioContext)();
      }
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
      }
      stopSpeechMeter();
      mediaSourceNode = audioContext.createMediaElementSource(audioEl);
      analyserNode = audioContext.createAnalyser();
      analyserNode.fftSize = 512; 
      analyserNode.smoothingTimeConstant = 0.5;
      analyserData = new Uint8Array(analyserNode.frequencyBinCount);
      mediaSourceNode.connect(analyserNode);
      analyserNode.connect(audioContext.destination);

      const tick = () => {
        if (!analyserNode || !analyserData) return;
        analyserNode.getByteFrequencyData(analyserData);
        
        const bufferLength = analyserData.length;
        const bassEnd = Math.floor(bufferLength * 0.1); 
        const midEnd = Math.floor(bufferLength * 0.4);   
        
        let bass = 0, mid = 0, treble = 0;

        for (let i = 0; i < bassEnd; i++) bass += analyserData[i];
        for (let i = bassEnd; i < midEnd; i++) mid += analyserData[i];
        for (let i = midEnd; i < bufferLength; i++) treble += analyserData[i];

        bass /= (bassEnd * 255);
        mid /= ((midEnd - bassEnd) * 255);
        treble /= ((bufferLength - midEnd) * 255);

        const volume = Math.min(1, (bass + mid + treble) * 1.5);
        
        if (volume > 0.05) {
            let a = 0, i_val = 0, u = 0, e = 0, o = 0;

            if (bass > mid && bass > treble) {
                u = bass * 1.2;
                o = bass * 0.8;
            } else if (treble > mid && treble > bass) {
                i_val = treble * 1.2;
                e = treble * 0.8;
            } else {
                a = mid * 1.5;
            }

            mouthCues = {
                a: Math.min(1, a * 1.5),
                i: Math.min(1, i_val * 1.5),
                u: Math.min(1, u * 1.5),
                e: Math.min(1, e * 1.5),
                o: Math.min(1, o * 1.5)
            };
        } else {
            mouthCues = { a: 0, i: 0, u: 0, e: 0, o: 0 };
        }

        analyserRaf = requestAnimationFrame(tick);
      };
      analyserRaf = requestAnimationFrame(tick);
    } catch (e) {
      stopSpeechMeter();
    }
  }

  async function prepareTtsAudio(text, emotion) {
    try {
      if (!autoSpeak) return null;
      const res = await fetch(`${apiBase}/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          voice: ttsVoice,
          pitch: ttsPitch,
          emotion,
          f0method: ttsF0Method
        })
      });
      if (!res.ok) return null;
      const payload = await res.json();
      if (!payload.audio_base64) return null;
      
      const audio = new Audio(`data:${payload.mime};base64,${payload.audio_base64}`);
      
      await new Promise((resolve, reject) => {
          audio.oncanplaythrough = resolve;
          audio.onerror = reject;
          setTimeout(resolve, 10000); 
      });

      return audio;
    } catch (e) {
      return null;
    }
  }

  function startTypewriter(replyText, index, duration) {
    if (!useTypewriter) {
      chatHistory = chatHistory.map((m, i) => {
        if (i === index) return { ...m, text: replyText };
        return m;
      });
      return;
    }
    const stepMs = 30;
    const totalSteps = Math.max(1, Math.floor(duration / stepMs));
    let step = 0;

    clearInterval(typingInterval);
    typingInterval = setInterval(() => {
      step += 1;
      const progress = Math.min(step / totalSteps, 1);
      const visibleChars = Math.floor(replyText.length * progress);
      chatHistory = chatHistory.map((m, i) => {
        if (i === index) {
          return { ...m, text: replyText.slice(0, visibleChars) };
        }
        return m;
      });
      if (progress >= 1) {
        clearInterval(typingInterval);
      }
    }, stepMs);
  }

  async function resetChat() {
    stopAllAudio();
    try {
      await fetch(`${apiBase}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: "reset", session_id: sessionId })
      });
    } catch (e) {}
    chatHistory = [];
    toast("Chat direset");
  }

  async function startRecording() {
    if (isRecording) return;
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recordedChunks = [];
      const preferredTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/ogg'
      ];
      const mimeType = preferredTypes.find(t => MediaRecorder.isTypeSupported(t)) || '';
      mediaRecorder = new MediaRecorder(mediaStream, mimeType ? { mimeType } : undefined);
      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) recordedChunks.push(e.data);
      };
      mediaRecorder.onstop = async () => {
        try {
          const blob = new Blob(recordedChunks, { type: mediaRecorder?.mimeType || 'audio/webm' });
          const form = new FormData();
          form.append('audio', blob, 'recording.webm');
          const res = await fetch(`${apiBase}/stt`, { method: 'POST', body: form });
          if (!res.ok) throw new Error("STT gagal");
          const data = await res.json();
          if (data?.text) {
            inputText = data.text;
            toast("Teks dari suara siap dikirim");
          }
        } catch (e) {
          toast("Gagal transkrip suara");
        } finally {
          try { mediaStream?.getTracks?.().forEach(t => t.stop()); } catch (e) {}
          mediaStream = null;
          mediaRecorder = null;
          recordedChunks = [];
          isRecording = false;
        }
      };
      mediaRecorder.start();
      isRecording = true;
      toast("Rekam suara... klik lagi untuk stop");
    } catch (e) {
      toast("Mic tidak tersedia/izin ditolak");
      isRecording = false;
      mediaRecorder = null;
      recordedChunks = [];
      try { mediaStream?.getTracks?.().forEach(t => t.stop()); } catch (e) {}
      mediaStream = null;
    }
  }

  function stopRecording() {
    try {
      mediaRecorder?.stop?.();
    } catch (e) {
      isRecording = false;
    }
  }

  function toggleRecording() {
    if (isRecording) stopRecording();
    else startRecording();
  }

  async function sendMessage() {
    if (!inputText.trim()) return;
    if (isLoading) return;

    stopAllAudio();
    const userMsg = { id: crypto?.randomUUID?.() || `m_${Math.random().toString(16).slice(2)}`, role: 'user', text: inputText, time: new Date() };
    chatHistory = [...chatHistory, userMsg];
    
    const messageToSend = inputText;
    inputText = ""; 
    isLoading = true;

    try {
      const res = await fetch(`${apiBase}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            message: messageToSend,
            session_id: sessionId
        })
      });

      if (!res.ok) throw new Error('Network response was not ok');
      const data = await res.json();

      if (data.reply) {
        const replyText = data.reply;
        const ttsText = data.reply_tts || replyText;
        const emotion = data.emotion || "neutral";

        let preparedAudio = null;
        if (autoSpeak) {
            preparedAudio = await prepareTtsAudio(ttsText, emotion);
        }

        const aiMsg = { 
          id: crypto?.randomUUID?.() || `m_${Math.random().toString(16).slice(2)}`,
          role: 'ai', 
          text: "", 
          emotion,
          time: new Date()
        };
        chatHistory = [...chatHistory, aiMsg];
        const index = chatHistory.length - 1;

        currentEmotion = emotion;
        const duration = Math.min(Math.max(replyText.length * 100, 2000), 7000);

        isLoading = false; 

        isAiSpeaking = true;
        startTypewriter(replyText, index, duration);

        if (preparedAudio) {
          if (ttsAudio) {
             try { ttsAudio.pause(); } catch(e){}
          }
          ttsAudio = preparedAudio;
          
          ttsAudio.addEventListener('ended', () => {
            isAiSpeaking = false;
            stopSpeechMeter();
          });
          ttsAudio.addEventListener('pause', () => stopSpeechMeter());
          
          startSpeechMeter(ttsAudio);
          
          const playPromise = ttsAudio.play();
          if (playPromise && playPromise.then) {
            playPromise.catch(err => {
              isAiSpeaking = false;
            });
          }
        } else {
          setTimeout(() => {
            isAiSpeaking = false;
          }, duration);
        }
      }

    } catch (error) {
      isOnline = false;
      lastError = "Gagal terhubung ke server";
      const errorMsg = { id: crypto?.randomUUID?.() || `m_${Math.random().toString(16).slice(2)}`, role: 'system', text: "Gagal terhubung ke server.", time: new Date() };
      chatHistory = [...chatHistory, errorMsg];
      isAiSpeaking = false;
      isLoading = false;
    } 
  }

  function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      toast("Tersalin");
    } catch (e) {
      toast("Gagal menyalin");
    }
  }

  const quickPrompts = [
    "Halo Alisa",
    "Jadwal kuliah prodi saya",
    "Deadline KRS kapan?",
    "Cek nilai",
    "UKT saya berapa?",
    "Lokasi gedung perkuliahan"
  ];
</script>

<main class="relative w-screen h-screen overflow-hidden bg-black text-white font-sans">
  
  <div class="absolute inset-0 z-0">
    <img 
      src="/RoomV1.jpg" 
      alt="Classroom Background" 
      class="w-full h-full object-cover opacity-100 grayscale-0"
    />
    <div class="absolute inset-0 bg-slate-950/40 backdrop-blur-[1px]"></div>
  </div>

  <div class="absolute inset-0 z-1 pointer-events-none">
    <Avatar isSpeaking={isAiSpeaking} emotion={currentEmotion} mouthCues={mouthCues} />
  </div>

  <div class="absolute top-4 left-4 right-4 z-20 pointer-events-auto flex items-start justify-between gap-3">
    <div class="inline-flex items-center gap-2 px-3 py-2 rounded-2xl bg-black/40 border border-white/10 backdrop-blur-md">
      <div class="w-2.5 h-2.5 rounded-full {isOnline ? 'bg-emerald-400' : 'bg-red-400'}"></div>
      <div class="text-xs text-white/80 leading-none">{isOnline ? "Online" : (lastError || "Offline")}</div>
      <div class="hidden sm:block text-white/30">•</div>
      <div class="hidden sm:block text-xs text-white/60 leading-none">Session {sessionId.slice(0, 8)}</div>
    </div>

    <div class="flex items-center gap-2">
      <button on:click={resetChat} class="px-3 py-2 rounded-2xl bg-black/40 hover:bg-black/50 border border-white/10 backdrop-blur-md text-xs transition-colors">
        Reset
      </button>
    </div>
  </div>

  <div class="absolute inset-0 z-10 flex flex-col justify-end pointer-events-none bg-gradient-to-t from-slate-950/80 via-transparent to-transparent">
    
    <div class="w-full max-w-3xl mx-auto p-4 pb-6 overflow-y-auto max-h-[55vh] flex flex-col gap-4 pointer-events-auto scroll-smooth no-scrollbar" bind:this={chatBox}>
      {#if chatHistory.length === 0}
        <div class="text-center text-white/50 mt-auto mb-4" in:fade>
          <h1 class="text-3xl font-bold mb-2 tracking-tight drop-shadow-lg">Alisa AI</h1>
          <p class="text-sm drop-shadow-md">Silakan sapa saya untuk memulai percakapan.</p>
          <div class="mt-4 flex flex-wrap justify-center gap-2">
            {#each quickPrompts as p}
              <button on:click={() => { inputText = p; sendMessage(); }} class="px-3 py-2 rounded-xl bg-white/10 hover:bg-white/15 border border-white/10 text-xs text-white/90">
                {p}
              </button>
            {/each}
          </div>
        </div>
      {/if}

      {#each chatHistory as msg (msg.id)}
        <div class="flex w-full {msg.role === 'user' ? 'justify-end' : 'justify-start'}" in:fly={{ y: 20, duration: 300 }}>
          
          <div class="
            relative max-w-[85%] px-5 py-3.5 rounded-2xl backdrop-blur-sm shadow-md border border-white/10 text-[0.95rem] leading-relaxed
            {msg.role === 'user' ? 'bg-blue-600/60 text-white rounded-br-none' : 
             msg.role === 'system' ? 'bg-red-500/60 text-white text-xs' : 
             'bg-slate-950/40 text-slate-100 rounded-bl-none'}
          ">
            <p class="drop-shadow-sm">{msg.text}</p>
            
            {#if msg.role !== 'system'}
              <div class="flex justify-between items-center mt-1.5 opacity-80 text-[0.65rem] font-medium tracking-wide">
                {#if msg.role === 'ai'}
                   <span class="uppercase bg-white/10 px-1.5 py-0.5 rounded text-white/90">{msg.emotion}</span>
                {:else}
                   <span></span>
                {/if}
                <span>{msg.time.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
              </div>
            {/if}

            {#if msg.role === 'ai' && msg.text}
              <div class="absolute -top-2 right-2 flex gap-1 opacity-0 hover:opacity-100 focus-within:opacity-100 transition-opacity">
                <button on:click={() => copyText(msg.text)} class="px-2 py-1 rounded-full bg-black/40 border border-white/10 text-[0.7rem]">
                  Copy
                </button>
              </div>
            {/if}
          </div>

        </div>
      {/each}

      {#if isLoading}
        <div class="flex justify-start" in:fade>
          <div class="bg-slate-950/40 px-4 py-3 rounded-2xl rounded-bl-none border border-white/10 flex gap-1.5 items-center backdrop-blur-sm">
            <div class="w-1.5 h-1.5 bg-white/70 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
            <div class="w-1.5 h-1.5 bg-white/70 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
            <div class="w-1.5 h-1.5 bg-white/70 rounded-full animate-bounce"></div>
          </div>
        </div>
      {/if}
    </div>

    <div class="w-full max-w-3xl mx-auto p-5 pt-2 pointer-events-auto">
      <div class="flex items-center gap-2 bg-slate-900/50 backdrop-blur-md p-2 rounded-full border border-white/10 shadow-xl transition-all hover:bg-slate-900/70 focus-within:bg-slate-900/80 focus-within:border-white/20">
        
        <textarea
          bind:this={inputEl}
          bind:value={inputText}
          on:keydown={handleKeydown}
          on:input={autosizeInput}
          rows="1"
          placeholder="Ketik pesan untuk Alisa..." 
          class="flex-1 bg-transparent border-none text-white px-4 py-2 focus:outline-none placeholder-white/50 text-base resize-none max-h-40"
        ></textarea>

        <button
          on:click={toggleRecording}
          aria-label={isRecording ? "Stop rekam" : "Rekam suara"}
          class="bg-white/10 hover:bg-white/15 text-white w-12 h-12 rounded-full flex items-center justify-center transition-all active:scale-95 border border-white/10"
        >
          {#if isRecording}
            <div class="w-3 h-3 rounded bg-red-400"></div>
          {:else}
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5">
              <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3z"></path>
              <path d="M19 11a7 7 0 0 1-14 0"></path>
              <line x1="12" y1="19" x2="12" y2="23"></line>
              <line x1="8" y1="23" x2="16" y2="23"></line>
            </svg>
          {/if}
        </button>
        
        <button 
          on:click={sendMessage}
          aria-label="Kirim pesan"
          class="bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 text-white w-12 h-12 rounded-full flex items-center justify-center transition-all active:scale-95 shadow-lg group"
          disabled={isLoading || !inputText.trim()}
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5 ml-0.5 group-hover:translate-x-0.5 transition-transform">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>

      </div>
    </div>

  </div>

  {#if toastText}
    <div class="absolute top-20 left-1/2 -translate-x-1/2 sm:left-auto sm:translate-x-0 sm:right-4 z-30 pointer-events-none" in:fade>
      <div class="px-4 py-2 rounded-full bg-black/50 border border-white/10 backdrop-blur-md text-sm text-white/90 shadow-lg">
        {toastText}
      </div>
    </div>
  {/if}
</main>

<style>
  .no-scrollbar::-webkit-scrollbar { display: none; }
  .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
</style>