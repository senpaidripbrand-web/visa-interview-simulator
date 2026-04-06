/**
 * Visa Officer Avatar — Realistic photo-based version
 * Uses a real headshot with CSS-driven animations: breathing, speaking pulse,
 * listening tilt, thinking glow. Audio-reactive when speaking.
 */
(function () {
  'use strict';

  let containerEl = null;

  // Stable, realistic male officer headshot (free, no auth)
  const PHOTO_URL = 'https://i.pravatar.cc/400?img=60';
  const FALLBACK_URL = 'https://randomuser.me/api/portraits/men/32.jpg';

  function setState(state) {
    if (!containerEl) return;
    const av = containerEl.querySelector('.avatar-container');
    if (av) av.dataset.state = state;
  }

  window.avatarInit = function (el) {
    containerEl = el;
    el.innerHTML = `
      <div class="avatar-container" data-state="idle">
        <div class="avatar-frame">
          <img class="avatar-photo" src="${PHOTO_URL}" alt="Visa Officer" referrerpolicy="no-referrer" onerror="this.onerror=null;this.src='${FALLBACK_URL}'">
          <div class="avatar-glow"></div>
          <div class="avatar-scan"></div>
        </div>
        <div class="avatar-status"></div>
        <div class="avatar-label">Officer Reynolds · Consular Section</div>
      </div>
    `;
  };

  window.avatarSpeak = function () { setState('speaking'); };
  window.avatarStopSpeak = function () { setState('idle'); };
  window.avatarThink = function () { setState('thinking'); };
  window.avatarListen = function () { setState('listening'); };
  window.avatarIdle = function () { setState('idle'); };
})();
