/**
 * Visa Officer Avatar — 3D Ready Player Me + TalkingHead.js
 * Real talking head with lip-sync from ElevenLabs audio + alignment.
 */

// Free Ready Player Me avatar (man in suit). Override via window.AVATAR_URL.
const RPM_AVATAR_URL = 'https://cdn.jsdelivr.net/gh/met4citizen/TalkingHead@main/avatars/avatarsdk.glb';

window.avatarInit = async function (el) {
  el.innerHTML = `
    <div class="avatar-3d-wrap" style="width:280px;height:340px;border-radius:24px;overflow:hidden;border:2.5px solid #5b9aff;background:linear-gradient(135deg,#0a0e17,#141a2a);box-shadow:0 0 28px rgba(91,154,255,0.25);position:relative;">
      <div id="th-avatar" style="width:100%;height:100%;"></div>
      <div id="th-loading" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#5b9aff;font-size:12px;letter-spacing:0.5px;">Loading 3D officer…</div>
    </div>
    <div class="avatar-label" style="margin-top:10px;font-size:11px;color:#5b9aff;letter-spacing:0.6px;text-transform:uppercase;text-align:center;">Officer Reynolds · Consular Section</div>
  `;
  try {
    const mod = await import('https://cdn.jsdelivr.net/gh/met4citizen/TalkingHead@main/modules/talkinghead.mjs');
    const TalkingHead = mod.TalkingHead;
    const node = document.getElementById('th-avatar');
    const head = new TalkingHead(node, {
      ttsEndpoint: null,
      lipsyncModules: ['en'],
      cameraView: 'upper',
      avatarMood: 'neutral',
      modelFPS: 30,
    });
    await head.showAvatar({
      url: window.AVATAR_URL || RPM_AVATAR_URL,
      body: 'M',
      lipsyncLang: 'en',
      avatarMood: 'neutral',
    });
    window.__head = head;
    const lo = document.getElementById('th-loading');
    if (lo) lo.remove();
  } catch (e) {
    console.error('[Avatar] TalkingHead init failed:', e);
    const lo = document.getElementById('th-loading');
    if (lo) lo.textContent = 'Avatar load failed';
  }
};

window.avatarSpeakB64 = async function (audio_b64, words, wtimes, wdurations) {
  if (!window.__head) return false;
  try {
    const bin = atob(audio_b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const ctx = window.__audioCtx || (window.__audioCtx = new (window.AudioContext || window.webkitAudioContext)());
    if (ctx.state === 'suspended') await ctx.resume();
    const audioBuffer = await ctx.decodeAudioData(bytes.buffer);
    await window.__head.speakAudio({
      audio: audioBuffer,
      words: words || [],
      wtimes: wtimes || [],
      wdurations: wdurations || [],
    });
    return true;
  } catch (e) {
    console.error('[Avatar] speakAudio failed:', e);
    return false;
  }
};

// Legacy state stubs (no-ops with TalkingHead — it handles its own state)
window.avatarSpeak = function () {};
window.avatarStopSpeak = function () {};
window.avatarThink = function () { if (window.__head && window.__head.setMood) try { window.__head.setMood('neutral'); } catch(e){} };
window.avatarListen = function () {};
window.avatarIdle = function () {};
