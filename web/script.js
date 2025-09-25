(() => {
  const api = {
    health: '/api/health',
    langs: '/api/languages',
    translate: '/api/translate',
    stt: '/api/speech-to-text',
    tts: '/api/text-to-speech'
  };

  const el = (id) => document.getElementById(id);
  const healthEl = el('health');
  const srcText = el('sourceText');
  const outText = el('translatedText');
  const srcLang = el('sourceLang');
  const tgtLang = el('targetLang');
  const langInfo = el('langInfo');
  const alerts = el('alerts');
  const audioInput = el('audioInput');
  const ttsText = el('ttsText');
  const ttsAudio = el('ttsAudio');

  function setBadge(text, ok = true) {
    healthEl.textContent = text;
    healthEl.className = 'badge' + (ok ? '' : ' alert');
  }

  async function checkHealth() {
    try {
      const r = await fetch(api.health);
      const j = await r.json();
      if (j.status === 'healthy') setBadge('Server ✓'); else setBadge('Server issue', false);
    } catch (e) {
      setBadge('Server unreachable', false);
    }
  }

  function showAlert(msg, type = 'alert') {
    const d = document.createElement('div');
    d.className = type;
    d.textContent = msg;
    alerts.innerHTML = '';
    alerts.appendChild(d);
  }

  async function loadLanguages() {
    try {
      const r = await fetch(api.langs);
      const j = await r.json();
      tgtLang.innerHTML = '';
      Object.entries(j.languages).forEach(([code, name]) => {
        const opt = document.createElement('option');
        opt.value = code; opt.textContent = name;
        if (code === 'en') opt.selected = true;
        tgtLang.appendChild(opt);
      });
      langInfo.textContent = `Loaded ${j.total} languages.`;
    } catch (e) {
      showAlert('Failed to load languages');
    }
  }

  async function translate() {
    const text = (srcText.value || '').trim();
    const source = srcLang.value || 'auto';
    const target = tgtLang.value;
    if (!text) return showAlert('Please enter text to translate');
    try {
      const r = await fetch(api.translate, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, source, target })
      });
      const j = await r.json();
      if (j.success) {
        outText.value = j.translated_text;
        langInfo.textContent = `Detected: ${j.source_language} → ${j.target_language}`;
      } else {
        showAlert(j.error || 'Translation failed');
      }
    } catch (e) {
      showAlert('Network error');
    }
  }

  function swap() {
    const tmp = srcText.value;
    srcText.value = outText.value;
    outText.value = tmp || '';
  }

  function clearAll() {
    srcText.value = '';
    outText.value = '';
    alerts.innerHTML = '';
    langInfo.textContent = '';
  }

  async function stt() {
    if (!audioInput.files || !audioInput.files[0]) return showAlert('Select an audio file');
    const fd = new FormData();
    fd.append('audio', audioInput.files[0]);
    try {
      const r = await fetch(api.stt, { method: 'POST', body: fd });
      const j = await r.json();
      if (j.success) {
        srcText.value = j.text;
        showAlert('Transcribed successfully', 'success');
      } else {
        showAlert(j.error || 'STT failed');
      }
    } catch (e) {
      showAlert('Network error');
    }
  }

  async function tts() {
    const text = (ttsText.value || srcText.value || '').trim();
    const language = tgtLang.value || 'en';
    if (!text) return showAlert('Enter text for TTS');
    try {
      const r = await fetch(api.tts, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, language })
      });
      const j = await r.json();
      if (j.success && j.audio_url) {
        ttsAudio.src = j.audio_url;
        ttsAudio.style.display = '';
        ttsAudio.play().catch(() => {});
      } else {
        showAlert(j.error || 'TTS failed');
      }
    } catch (e) {
      showAlert('Network error');
    }
  }

  // Event listeners
  document.addEventListener('DOMContentLoaded', async () => {
    await checkHealth();
    await loadLanguages();
    document.getElementById('btnTranslate').addEventListener('click', translate);
    document.getElementById('btnSwap').addEventListener('click', swap);
    document.getElementById('btnClear').addEventListener('click', clearAll);
    document.getElementById('btnSTT').addEventListener('click', stt);
    document.getElementById('btnTTS').addEventListener('click', tts);
  });
})();
