/**
 * Visa Officer Avatar Component
 *
 * Minimalist SVG-based animated avatar for a US visa interview officer.
 *
 * Usage:
 *   1. Include avatar.css
 *   2. Include avatar.js
 *   3. Call avatarInit(containerElement) to render
 *   4. Use avatarSpeak(), avatarStopSpeak(), avatarThink(), avatarListen(), avatarIdle()
 */

(function () {
  'use strict';

  let containerEl = null;

  const SKIN = '#d4a87c';
  const SKIN_SHADOW = '#c49768';
  const HAIR = '#2a1f14';
  const SUIT = '#1e2a42';
  const SUIT_LIGHT = '#263350';
  const SHIRT = '#dce3ed';
  const TIE = '#3a5a9f';
  const TIE_DARK = '#2d4778';
  const LIP = '#b8816e';
  const EYE_WHITE = '#eef0f2';
  const IRIS = '#3d2b1a';
  const BROW = '#2a1f14';

  function createSVG() {
    const svg = `
    <svg class="avatar-svg" viewBox="0 0 180 180" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <clipPath id="avatar-clip">
          <circle cx="90" cy="90" r="88"/>
        </clipPath>
        <linearGradient id="skin-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${SKIN}"/>
          <stop offset="100%" stop-color="${SKIN_SHADOW}"/>
        </linearGradient>
        <linearGradient id="suit-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${SUIT_LIGHT}"/>
          <stop offset="100%" stop-color="${SUIT}"/>
        </linearGradient>
        <linearGradient id="tie-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${TIE}"/>
          <stop offset="100%" stop-color="${TIE_DARK}"/>
        </linearGradient>
      </defs>

      <g clip-path="url(#avatar-clip)">
        <!-- Background -->
        <rect width="180" height="180" fill="#141b2d"/>

        <g class="head-group">
          <!-- Neck -->
          <rect x="76" y="118" width="28" height="24" rx="4" fill="url(#skin-grad)"/>

          <!-- Shoulders / Suit -->
          <ellipse cx="90" cy="172" rx="72" ry="40" fill="url(#suit-grad)"/>
          <!-- Lapels -->
          <path d="M 60 140 Q 72 155 78 172 L 58 172 Z" fill="${SUIT_LIGHT}" opacity="0.5"/>
          <path d="M 120 140 Q 108 155 102 172 L 122 172 Z" fill="${SUIT_LIGHT}" opacity="0.5"/>

          <!-- Shirt collar -->
          <path d="M 78 132 L 84 148 L 90 138 L 96 148 L 102 132"
                fill="none" stroke="${SHIRT}" stroke-width="3.5" stroke-linejoin="round"/>
          <!-- Shirt front -->
          <rect x="86" y="138" width="8" height="34" rx="1" fill="${SHIRT}" opacity="0.85"/>

          <!-- Tie -->
          <path d="M 90 138 L 85 160 L 90 172 L 95 160 Z" fill="url(#tie-grad)"/>
          <ellipse cx="90" cy="140" rx="4" ry="2.5" fill="${TIE}"/>

          <!-- Head shape -->
          <ellipse cx="90" cy="82" rx="38" ry="44" fill="url(#skin-grad)"/>

          <!-- Ears -->
          <ellipse cx="52" cy="85" rx="6" ry="9" fill="${SKIN_SHADOW}"/>
          <ellipse cx="53" cy="85" rx="3.5" ry="6" fill="${SKIN}" opacity="0.7"/>
          <ellipse cx="128" cy="85" rx="6" ry="9" fill="${SKIN_SHADOW}"/>
          <ellipse cx="127" cy="85" rx="3.5" ry="6" fill="${SKIN}" opacity="0.7"/>

          <!-- Hair -->
          <path d="M 52 72 Q 52 38 90 35 Q 128 38 128 72
                   Q 128 55 115 48 Q 100 42 90 43 Q 80 42 65 48 Q 52 55 52 72 Z"
                fill="${HAIR}"/>
          <!-- Hair sides -->
          <path d="M 52 72 Q 50 62 53 55 Q 56 50 52 72 Z" fill="${HAIR}"/>
          <path d="M 128 72 Q 130 62 127 55 Q 124 50 128 72 Z" fill="${HAIR}"/>

          <!-- Eyebrows -->
          <g class="brow-group">
            <path d="M 68 72 Q 73 68 82 70" stroke="${BROW}" stroke-width="2.2"
                  fill="none" stroke-linecap="round"/>
            <path d="M 98 70 Q 107 68 112 72" stroke="${BROW}" stroke-width="2.2"
                  fill="none" stroke-linecap="round"/>
          </g>

          <!-- Eyes -->
          <g class="eye-group" style="transform-origin: 75px 80px">
            <!-- Left eye -->
            <ellipse cx="75" cy="80" rx="8" ry="5.5" fill="${EYE_WHITE}"/>
            <circle cx="75" cy="80" r="3.5" fill="${IRIS}"/>
            <circle cx="75" cy="80" r="2" fill="#1a120a"/>
            <circle cx="76.5" cy="78.5" r="1" fill="#fff" opacity="0.7"/>
          </g>
          <g class="eye-group" style="transform-origin: 105px 80px">
            <!-- Right eye -->
            <ellipse cx="105" cy="80" rx="8" ry="5.5" fill="${EYE_WHITE}"/>
            <circle cx="105" cy="80" r="3.5" fill="${IRIS}"/>
            <circle cx="105" cy="80" r="2" fill="#1a120a"/>
            <circle cx="106.5" cy="78.5" r="1" fill="#fff" opacity="0.7"/>
          </g>

          <!-- Nose -->
          <path d="M 88 82 Q 87 92 84 96 Q 88 98 90 98 Q 92 98 96 96 Q 93 92 92 82"
                fill="none" stroke="${SKIN_SHADOW}" stroke-width="1.2" opacity="0.5"/>

          <!-- Mouth -->
          <g class="mouth-group" style="transform-origin: 90px 107px">
            <path d="M 82 106 Q 86 110 90 110 Q 94 110 98 106"
                  stroke="${LIP}" stroke-width="2" fill="none" stroke-linecap="round"/>
            <!-- Lower lip hint -->
            <path d="M 84 108 Q 87 112 90 112 Q 93 112 96 108"
                  fill="${LIP}" opacity="0.3"/>
          </g>

          <!-- Jaw / chin shadow -->
          <ellipse cx="90" cy="120" rx="22" ry="4" fill="${SKIN_SHADOW}" opacity="0.15"/>
        </g>
      </g>
    </svg>`;
    return svg;
  }

  /**
   * Initialize the avatar inside a container element.
   * @param {HTMLElement} el - The container to render into.
   */
  function avatarInit(el) {
    if (!el) {
      console.error('avatarInit: container element is required');
      return;
    }
    containerEl = el;
    containerEl.classList.add('avatar-container');
    containerEl.setAttribute('data-state', 'idle');
    containerEl.innerHTML = `
      <div class="avatar-frame">
        ${createSVG()}
      </div>
      <div class="avatar-status"></div>
    `;
  }

  function setState(state) {
    if (!containerEl) {
      console.warn('Avatar not initialized. Call avatarInit() first.');
      return;
    }
    containerEl.setAttribute('data-state', state);
  }

  /** Start speaking animation. */
  function avatarSpeak() {
    setState('speaking');
  }

  /** Stop speaking, return to idle. */
  function avatarStopSpeak() {
    setState('idle');
  }

  /** Enter thinking state. */
  function avatarThink() {
    setState('thinking');
  }

  /** Enter listening state. */
  function avatarListen() {
    setState('listening');
  }

  /** Return to idle state. */
  function avatarIdle() {
    setState('idle');
  }

  // Expose API globally
  window.avatarInit = avatarInit;
  window.avatarSpeak = avatarSpeak;
  window.avatarStopSpeak = avatarStopSpeak;
  window.avatarThink = avatarThink;
  window.avatarListen = avatarListen;
  window.avatarIdle = avatarIdle;

})();
