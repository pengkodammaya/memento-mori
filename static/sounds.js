/* ════════════════════════════════════════════════════════════════════
   NEKYIA — atmospheric sound engine.

   A tiny Web Audio layer: lazily creates <audio> elements on first user
   gesture (browsers block autoplay otherwise), fades ambient layers in/out,
   and degrades silently if any sound file is missing or fails to load.

   Public API (via the `sound` singleton):
     sound.unlock()              call on first user gesture
     sound.play(name, opts?)     one-shot (chime, bell, whisper)
     sound.fadeIn(name, ms?)     start a looping ambient layer, fading in
     sound.fadeOut(name, ms?)    fade a looping layer out, then pause
     sound.setMuted(bool)        mute/unmute everything
     sound.isMuted               boolean
   ════════════════════════════════════════════════════════════════════ */
'use strict';

// Relative paths — Flask serves /static/ at /static/.
const SOUND_DIR = '/static/sounds/';
const SOUND_EXT = '.wav';   // BBC downloads come as WAV; lossless, universal support

// Which clips loop (ambient beds) vs. one-shots.
const LOOPS = new Set(['ambient-drone', 'wave-swell']);

// Default per-clip volumes (mixed relative to each other).
const VOLUME = {
  'ambient-drone': 0.45,
  'wave-swell':    0.30,
  'chime-fate':    0.55,
  'bell-summon':   0.70,
  'whisper-rise':  0.35,
  'bell-final':    0.80,
};

class SoundEngine {
  constructor() {
    this._clips = new Map();      // name → HTMLAudioElement
    this._muted = false;
    this._unlocked = false;
    this._loadFailed = new Set(); // names known to 404 — skip retries
    // Treat audio like motion: if the visitor prefers reduced motion, start muted.
    this._prefersQuiet = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (this._prefersQuiet) this._muted = true;
  }

  get isMuted() { return this._muted; }

  // The browser only lets us play after a user gesture. Call this from a
  // one-time click/keydown/scroll listener set up in app.js boot().
  unlock() {
    if (this._unlocked) return;
    this._unlocked = true;
    // "Touch" any already-created clips so they're considered unlocked too.
    for (const el of this._clips.values()) {
      el.play().then(() => el.pause()).catch(() => {});
    }
  }

  setMuted(muted) {
    this._muted = muted;
    for (const [name, el] of this._clips) {
      if (!LOOPS.has(name)) continue;
      // Reflect mute state on looping beds; one-shots are gated in play().
      const target = muted ? 0 : VOLUME[name];
      this._setVolume(name, target, 200);
    }
  }

  // Lazily create (or reuse) an <audio> element for a clip. Returns null if
  // the file is known to be missing or fails to load — callers must no-op.
  _clip(name) {
    if (this._loadFailed.has(name)) return null;
    if (this._clips.has(name)) return this._clips.get(name);
    const el = new Audio(SOUND_DIR + name + SOUND_EXT);
    el.preload = 'auto';
    el.loop = LOOPS.has(name);
    el.volume = VOLUME[name] ?? 0.5;
    // On error, mark the clip as missing so future calls skip silently.
    el.addEventListener('error', () => {
      this._clips.delete(name);
      this._loadFailed.add(name);
    });
    this._clips.set(name, el);
    return el;
  }

  // Fade volume of a clip to `target` over `ms` milliseconds (linear).
  _setVolume(name, target, ms) {
    const el = this._clip(name);
    if (!el) return;
    const start = el.volume;
    const t0 = performance.now();
    const step = (now) => {
      const t = Math.min((now - t0) / ms, 1);
      el.volume = start + (target - start) * t;
      if (t < 1) requestAnimationFrame(step);
      else if (target === 0 && LOOPS.has(name)) el.pause();
    };
    requestAnimationFrame(step);
  }

  // Play a one-shot clip. Options:
  //   { rate: 1.0 }   playback rate (pitch/speed) — used to vary chimes
  //   { delay: 0 }    ms to wait before playing — used to stagger whispers
  play(name, { rate = 1.0, delay = 0 } = {}) {
    if (this._muted) return;
    const fire = () => {
      const el = this._clip(name);
      if (!el) return;
      el.currentTime = 0;
      el.playbackRate = rate;
      el.volume = VOLUME[name] ?? 0.5;
      el.play().catch(() => {}); // ignore autoplay rejections silently
    };
    if (delay > 0) setTimeout(fire, delay);
    else fire();
  }

  // Start a looping ambient layer, fading in.
  fadeIn(name, ms = 1500) {
    if (this._muted) return;
    const el = this._clip(name);
    if (!el) return;
    el.volume = 0;
    el.play().catch(() => {}).then(() => this._setVolume(name, VOLUME[name] ?? 0.5, ms));
  }

  // Fade a looping layer out, then pause it.
  fadeOut(name, ms = 2000) {
    this._setVolume(name, 0, ms);
  }
}

// Single shared instance.
const sound = new SoundEngine();
