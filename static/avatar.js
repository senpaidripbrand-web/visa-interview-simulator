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
      <div class="avatar-container" data-state="idle" style="display:flex;flex-direction:column;align-items:center;">
        <div class="avatar-frame" style="width:300px;height:380px;border-radius:24px;overflow:hidden;position:relative;border:2.5px solid #5b9aff;background:#0a0e17;box-shadow:0 0 28px rgba(91,154,255,0.25);transition:box-shadow 0.4s ease, border-color 0.4s ease;">
          <img id="th-poster" class="avatar-photo" src="/static/officer.png" style="width:100%;height:100%;object-fit:cover;display:block;transform-origin:center 55%;">
          <div class="avatar-scan" style="position:absolute;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,rgba(91,154,255,0.7),transparent);top:-10px;opacity:0;pointer-events:none;"></div>
          <div id="th-status" class="avatar-status" style="position:absolute;top:10px;right:10px;width:13px;height:13px;border-radius:50%;background:#3a7bdb;border:2px solid #0a0e17;transition:background 0.3s ease, box-shadow 0.3s ease;"></div>
        </div>
        <div class="avatar-label" style="margin-top:10px;font-size:11px;color:#5b9aff;letter-spacing:0.6px;text-transform:uppercase;text-align:center;">Officer Reynolds · Consular Section</div>
      </div>
    `;
  };

  function setState(state) {
    if (!containerEl) return;
    const c = containerEl.querySelector('.avatar-container');
    if (c) c.setAttribute('data-state', state);
  }

  window.avatarPlayVideo = function () { return Promise.resolve(); };

  window.avatarSpeak = function () { setState('speaking'); };
  window.avatarStopSpeak = function () { setState('idle'); };
  window.avatarThink = function () { setState('thinking'); };
  window.avatarListen = function () { setState('listening'); };
  window.avatarIdle = function () { setState('idle'); };
})();
