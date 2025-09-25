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
  const statusBar = el('statusBar');
  
  // Status bar functionality
  function showStatus(message, type = 'info', duration = 3000) {
    statusBar.textContent = message;
    statusBar.className = `status-bar ${type}`;
    statusBar.style.display = 'block';
    
    setTimeout(() => {
      statusBar.style.display = 'none';
    }, duration);
  }
  
  // Copy translation to clipboard
  async function copyTranslation() {
    const text = outText.value.trim();
    if (!text) {
      showStatus('لا يوجد نص للنسخ', 'error');
      return;
    }
    
    try {
      await navigator.clipboard.writeText(text);
      showStatus('تم نسخ الترجمة بنجاح! 📋', 'success');
    } catch (e) {
      // Fallback for older browsers
      outText.select();
      document.execCommand('copy');
      showStatus('تم نسخ الترجمة بنجاح! 📋', 'success');
    }
  }
  
  // Download translation as text file
  function downloadTranslation() {
    const text = outText.value.trim();
    if (!text) {
      showStatus('لا يوجد نص للتحميل', 'error');
      return;
    }
    
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `translation_${new Date().getTime()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showStatus('تم تحميل الترجمة كملف نصي! 💾', 'success');
  }
  
  // Enable text selection in textareas
  function enableTextSelection() {
    // Remove readonly temporarily to allow selection
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
      textarea.style.userSelect = 'text';
      textarea.style.webkitUserSelect = 'text';
      textarea.style.mozUserSelect = 'text';
      textarea.style.msUserSelect = 'text';
    });
  }
  
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
    
    showStatus('جاري الترجمة...', 'info');
    
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
        showStatus('تمت الترجمة بنجاح! ✨', 'success');
      } else {
        showAlert(j.error || 'Translation failed');
        showStatus('فشل في الترجمة', 'error');
      }
    } catch (e) {
      showAlert('Network error');
      showStatus('خطأ في الشبكة', 'error');
    }
  }
  
  function swap() {
    const tmp = srcText.value;
    srcText.value = outText.value;
    outText.value = tmp || '';
    showStatus('تم تبديل النصوص', 'info', 2000);
  }
  
  function clearAll() {
    srcText.value = '';
    outText.value = '';
    alerts.innerHTML = '';
    langInfo.textContent = '';
    showStatus('تم مسح جميع النصوص', 'info', 2000);
  }
  
  async function stt() {
    if (!audioInput.files || !audioInput.files[0]) return showAlert('Select an audio file');
    
    showStatus('جاري تحويل الصوت إلى نص...', 'info');
    
    const fd = new FormData();
    fd.append('audio', audioInput.files[0]);
    try {
      const r = await fetch(api.stt, { method: 'POST', body: fd });
      const j = await r.json();
      if (j.success) {
        srcText.value = j.text;
        showAlert('Transcribed successfully', 'success');
        showStatus('تم تحويل الصوت إلى نص بنجاح! 🎵', 'success');
      } else {
        showAlert(j.error || 'STT failed');
        showStatus('فشل في تحويل الصوت', 'error');
      }
    } catch (e) {
      showAlert('Network error');
      showStatus('خطأ في الشبكة', 'error');
    }
  }
  
  async function tts() {
    const text = (ttsText.value || srcText.value || '').trim();
    const language = tgtLang.value || 'en';
    if (!text) return showAlert('Enter text for TTS');
    
    showStatus('جاري تحويل النص إلى صوت...', 'info');
    
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
        showStatus('تم تحويل النص إلى صوت بنجاح! 🔊', 'success');
      } else {
        showAlert(j.error || 'TTS failed');
        showStatus('فشل في تحويل النص إلى صوت', 'error');
      }
    } catch (e) {
      showAlert('Network error');
      showStatus('خطأ في الشبكة', 'error');
    }
  }
  
  // Event listeners
  document.addEventListener('DOMContentLoaded', async () => {
    await checkHealth();
    await loadLanguages();
    
    // Enable text selection for all textareas
    enableTextSelection();
    
    // Original event listeners
    document.getElementById('btnTranslate').addEventListener('click', translate);
    document.getElementById('btnSwap').addEventListener('click', swap);
    document.getElementById('btnClear').addEventListener('click', clearAll);
    document.getElementById('btnSTT').addEventListener('click', stt);
    document.getElementById('btnTTS').addEventListener('click', tts);
    
    // New feature event listeners
    document.getElementById('btnCopyTranslation').addEventListener('click', copyTranslation);
    document.getElementById('btnDownloadTranslation').addEventListener('click', downloadTranslation);
    
    // Show welcome message
    setTimeout(() => {
      showStatus('مرحباً بك في HumanTranslator! 🌍', 'info', 2500);
    }, 1000);
  });
})();
