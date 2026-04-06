/**
 * Visa Officer Avatar — D-ID talking head video player
 * Uses a still photo (officer.png) as the source; the backend generates
 * a real lip-synced talking video per officer message via D-ID.
 */
(function () {
  'use strict';

  let containerEl = null;

  window.avatarInit = function (el) {
    containerEl = el;
    el.innerHTML = `
      <div class="avatar-3d-wrap" style="width:300px;height:380px;border-radius:24px;overflow:hidden;border:2.5px solid #5b9aff;background:#0a0e17;box-shadow:0 0 28px rgba(91,154,255,0.25);position:relative;">
        <video id="th-video" playsinline muted poster="/static/officer.png" style="width:100%;height:100%;object-fit:cover;display:block;background:#0a0e17;"></video>
        <img id="th-poster" src="/static/officer.png" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;pointer-events:none;transition:opacity 0.3s ease;">
        <div id="th-status" style="position:absolute;top:10px;right:10px;width:12px;height:12px;border-radius:50%;background:#3a7bdb;border:2px solid #0a0e17;"></div>
      </div>
      <div class="avatar-label" style="margin-top:10px;font-size:11px;color:#5b9aff;letter-spacing:0.6px;text-transform:uppercase;text-align:center;">Officer Reynolds · Consular Section</div>
    `;
  };

  window.avatarPlayVideo = function (videoUrl) {
    return new Promise((resolve) => {
      if (!containerEl) return resolve();
      const v = document.getElementById('th-video');
      const p = document.getElementById('th-poster');
      const s = document.getElementById('th-status');
      if (!v) return resolve();

      const done = () => {
        v.removeEventListener('ended', done);
        v.removeEventListener('error', done);
        if (p) p.style.opacity = '1';
        if (s) s.style.background = '#3a7bdb';
        resolve();
      };
      v.addEventListener('ended', done);
      v.addEventListener('error', done);

      v.muted = false;
      v.src = videoUrl;
      v.load();
      v.play().then(() => {
        if (p) p.style.opacity = '0';
        if (s) s.style.background = '#4caf50';
      }).catch(done);
    });
  };

  // Legacy stubs
  window.avatarSpeak = function () {};
  window.avatarStopSpeak = function () {};
  window.avatarThink = function () {
    const s = document.getElementById('th-status');
    if (s) s.style.background = '#ff9800';
  };
  window.avatarListen = function () {
    const s = document.getElementById('th-status');
    if (s) s.style.background = '#5b9aff';
  };
  window.avatarIdle = function () {
    const s = document.getElementById('th-status');
    if (s) s.style.background = '#3a7bdb';
  };
})();
