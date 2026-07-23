/* ════════════════════════════════════════════════════════════════════
   NEKYIA — client-side voyage.
   - Wine-dark sea (background + sea-of-souls canvas)
   - Fates grid
   - Voyage-of-years SVG chart
   - Archipelago
   - The Descent (interactive soul-summoning)
   ════════════════════════════════════════════════════════════════════ */
'use strict';

const FATE_COLORS = {
  heart: '#c8323a', breath: '#7fb8c4', cancer: '#9b6db5',
  metabolic: '#d4a13a', pestilence: '#6fae5a', violence: '#d96b3c', dawn: '#8aa0b8',
};

// ───────────────────────────────────────────────────────────────────────
// Small helpers
// ───────────────────────────────────────────────────────────────────────
const $  = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const fmt = (n) => Number(n).toLocaleString('en-US');
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`fetch ${url} → ${r.status}`);
  return r.json();
}

// Honour reduced-motion globally.
const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Ambient sound toggle wiring (defined below). Each call site guards on
// `sound` existing — safe if sounds.js fails to load for any reason.
// (sound is a global from sounds.js; declared with var here for clarity.)

// ───────────────────────────────────────────────────────────────────────
// 1. The invocation counter — count up the grand total
// ───────────────────────────────────────────────────────────────────────
function animateCount(el, target, dur = 2600) {
  if (REDUCED) { el.textContent = fmt(target); return; }
  const start = performance.now();
  function tick(now) {
    const t = clamp((now - start) / dur, 0, 1);
    // ease-out cubic
    const e = 1 - Math.pow(1 - t, 3);
    el.textContent = fmt(Math.floor(e * target));
    if (t < 1) requestAnimationFrame(tick);
    else el.textContent = fmt(target);
  }
  requestAnimationFrame(tick);
}

// ───────────────────────────────────────────────────────────────────────
// 2. The wine-dark sea — the persistent background
//    A field of slow-drifting stars/sparks, deep blue, gold-tinged.
// ───────────────────────────────────────────────────────────────────────
class WineDarkSea {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.stars = [];
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.resize();
    this.spawn();
    window.addEventListener('resize', () => { this.resize(); this.spawn(); });
    if (!REDUCED) requestAnimationFrame((t) => this.loop(t));
    else this.drawStatic();
  }
  resize() {
    const { canvas } = this;
    canvas.width  = window.innerWidth  * this.dpr;
    canvas.height = window.innerHeight * this.dpr;
    canvas.style.width  = window.innerWidth + 'px';
    canvas.style.height = window.innerHeight + 'px';
  }
  spawn() {
    // Density scales with viewport, capped for perf.
    const area = window.innerWidth * window.innerHeight;
    const n = clamp(Math.floor(area / 9000), 60, 320);
    this.stars = Array.from({ length: n }, () => this.makeStar());
  }
  makeStar() {
    return {
      x: Math.random() * this.canvas.width,
      y: Math.random() * this.canvas.height,
      r: (Math.random() * 1.4 + 0.3) * this.dpr,
      vx: (Math.random() - 0.5) * 0.06 * this.dpr,
      vy: (Math.random() - 0.5) * 0.06 * this.dpr,
      a: Math.random() * 0.5 + 0.15,         // base alpha
      tw: Math.random() * Math.PI * 2,        // twinkle phase
      tws: Math.random() * 0.6 + 0.2,         // twinkle speed
      hue: Math.random() < 0.18 ? 'gold' : 'blue',
    };
  }
  loop(t) {
    this.draw(t);
    requestAnimationFrame((n) => this.loop(n));
  }
  drawStatic() { this.draw(0, true); }
  draw(t, stat = false) {
    const { ctx, canvas } = this;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const s of this.stars) {
      if (!stat) {
        s.x += s.vx; s.y += s.vy;
        if (s.x < 0) s.x = canvas.width;
        if (s.x > canvas.width) s.x = 0;
        if (s.y < 0) s.y = canvas.height;
        if (s.y > canvas.height) s.y = 0;
        s.tw += 0.01 * s.tws;
      }
      const alpha = stat ? s.a : s.a * (0.6 + 0.4 * Math.sin(s.tw));
      const col = s.hue === 'gold'
        ? `rgba(201,169,97,${alpha})`
        : `rgba(180,200,230,${alpha * 0.7})`;
      ctx.beginPath();
      ctx.fillStyle = col;
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fill();
      if (s.hue === 'gold' && s.r > 1.2 * this.dpr) {
        ctx.fillStyle = `rgba(201,169,97,${alpha * 0.18})`;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r * 3, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }
}

// ───────────────────────────────────────────────────────────────────────
// 3. Sea of Souls — Book V. One particle per ~100 deaths,
//    coloured by fate, drifting like a current.
// ───────────────────────────────────────────────────────────────────────
class SeaOfSouls {
  constructor(stage, fates, total) {
    this.stage = stage;
    this.fates = fates;
    this.total = total;
    this.canvas = document.createElement('canvas');
    this.canvas.id = 'sea-particles';
    stage.appendChild(this.canvas);
    this.ctx = this.canvas.getContext('2d');
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.particles = [];
    this.mouse = { x: -9999, y: -9999 };
    this.resize();
    this.spawn();
    window.addEventListener('resize', () => { this.resize(); this.spawn(); });
    this.canvas.addEventListener('mousemove', (e) => {
      const r = this.canvas.getBoundingClientRect();
      this.mouse.x = (e.clientX - r.left) * this.dpr;
      this.mouse.y = (e.clientY - r.top) * this.dpr;
    });
    this.canvas.addEventListener('mouseleave', () => {
      this.mouse.x = this.mouse.y = -9999;
    });
    if (!REDUCED) requestAnimationFrame((t) => this.loop(t));
    else this.drawStatic();
  }
  resize() {
    const w = this.stage.clientWidth;
    const h = this.stage.clientHeight;
    this.canvas.width  = w * this.dpr;
    this.canvas.height = h * this.dpr;
    this.canvas.style.width  = w + 'px';
    this.canvas.style.height = h + 'px';
  }
  spawn() {
    // One particle per ~1000 deaths — keeps the sea readable, not 750k dots.
    const n = clamp(Math.floor(this.total / 1000), 200, 900);
    const w = this.canvas.width, h = this.canvas.height;
    // Build weighted palette from fate proportions.
    const palette = [];
    for (const f of this.fates) {
      const take = Math.round((f.count / this.total) * n);
      for (let i = 0; i < take; i++) palette.push(f.color);
    }
    while (palette.length < n) palette.push('#8aa0b8');
    // shuffle
    for (let i = palette.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [palette[i], palette[j]] = [palette[j], palette[i]];
    }
    this.particles = palette.map((col) => ({
      x: Math.random() * w,
      y: Math.random() * h,
      r: (Math.random() * 1.3 + 0.6) * this.dpr,
      vx: (Math.random() - 0.5) * 0.18 * this.dpr,
      vy: (Math.random() * 0.25 + 0.02) * this.dpr, // gentle downward drift
      a: Math.random() * 0.5 + 0.4,
      col,
    }));
  }
  loop(t) {
    this.draw();
    requestAnimationFrame((n) => this.loop(n));
  }
  drawStatic() { this.draw(true); }
  draw(stat = false) {
    const { ctx, canvas, particles } = this;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const p of particles) {
      if (!stat) {
        p.x += p.vx; p.y += p.vy;
        // wrap
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y > canvas.height) { p.y = 0; p.x = Math.random() * canvas.width; }
        // mouse repulsion — a soul stirs when you reach for it
        const dx = p.x - this.mouse.x, dy = p.y - this.mouse.y;
        const d2 = dx * dx + dy * dy;
        const R = 70 * this.dpr;
        if (d2 < R * R) {
          const d = Math.sqrt(d2) || 1;
          const f = (R - d) / R * 1.2;
          p.x += (dx / d) * f;
          p.y += (dy / d) * f;
        }
      }
      // halo (dim, wide) then core (bright, tight) — same colour, two alphas
      ctx.globalAlpha = p.a * 0.18;
      ctx.fillStyle = p.col;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r * 2.6, 0, Math.PI * 2);
      ctx.fill();
      // core
      ctx.globalAlpha = p.a;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = p.col;
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }
}

// ───────────────────────────────────────────────────────────────────────
// 4. The Fates — Book XI(a)
// ───────────────────────────────────────────────────────────────────────
function renderFates(fates, total) {
  const grid = $('#fates-grid');
  grid.innerHTML = fates.map((f) => `
    <article class="fate-card" style="--fate-color:${f.color}">
      <div class="fate-glyph">${f.glyph}</div>
      <h3 class="fate-label">${f.label}</h3>
      <p class="fate-ms">${f.ms}</p>
      <div class="fate-count">${fmt(f.count)}</div>
      <div class="fate-pct">${f.pct}% of all souls · median age ${f.median_age}</div>
      <p class="fate-odyssey">"${f.odyssey}"</p>
      <div class="fate-detail">
        <span class="label">Most common within this fate</span>
        <ul>
          ${f.top_causes.map((c) => `
            <li><span>${c.cause}</span><span class="c">${fmt(c.count)}</span></li>
          `).join('')}
        </ul>
      </div>
    </article>
  `).join('');

  // Each fate chimes on hover — pitched by its rank in the catalogue.
  // Lower rank (more common) plays a steadier tone; rarer fates ring higher.
  grid.addEventListener('mouseenter', (e) => {
    const card = e.target.closest('.fate-card');
    if (!card || typeof sound === 'undefined') return;
    const idx = Array.from(grid.children).indexOf(card);
    // pitch from 0.85 (heaviest fate) up to ~1.4 (rarest)
    const rate = 0.85 + (idx / Math.max(1, grid.children.length - 1)) * 0.55;
    sound.play('chime-fate', { rate });
  }, true);
}

// ───────────────────────────────────────────────────────────────────────
// 5. Voyage of Years — Book IX. Custom SVG area chart.
// ───────────────────────────────────────────────────────────────────────
function renderVoyage(data) {
  const svg = $('#voyage-svg');
  const aside = $('#voyage-aside');
  const W = 1000, H = 360, P = { l: 36, r: 16, t: 16, b: 34 };
  const innerW = W - P.l - P.r, innerH = H - P.t - P.b;

  const rows = data.by_gender;
  const maxC = Math.max(...rows.map((r) => Math.max(r.male, r.female)));
  const maxY = Math.max(...rows.map((r) => r.age));
  const xOf = (age) => P.l + (age / maxY) * innerW;
  const yOf = (c) => P.t + innerH - (c / maxC) * innerH;

  // build smoothed area paths (simple line)
  const linePath = (key) => rows.map((r, i) =>
    `${i === 0 ? 'M' : 'L'} ${xOf(r.age).toFixed(1)} ${yOf(r[key]).toFixed(1)}`
  ).join(' ');
  const areaPath = (key) =>
    `${linePath(key)} L ${xOf(rows[rows.length - 1].age).toFixed(1)} ${P.t + innerH}`
    + ` L ${xOf(rows[0].age).toFixed(1)} ${P.t + innerH} Z`;

  // axes
  const ageTicks = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90];
  const yTicks = 4;
  let gridH = '';
  for (let i = 0; i <= yTicks; i++) {
    const y = P.t + (i / yTicks) * innerH;
    gridH += `<line x1="${P.l}" y1="${y}" x2="${W - P.r}" y2="${y}"/>`;
    gridH += `<text x="${P.l - 6}" y="${y + 3}" text-anchor="end">${fmt(Math.round(maxC - (i / yTicks) * maxC))}</text>`;
  }
  let axisX = '';
  for (const a of ageTicks) {
    axisX += `<line x1="${xOf(a)}" y1="${P.t + innerH}" x2="${xOf(a)}" y2="${P.t + innerH + 5}"/>`;
    axisX += `<text x="${xOf(a)}" y="${P.t + innerH + 20}" text-anchor="middle">${a}</text>`;
  }

  // find the modal age overall for an annotation
  let peakAge = 0, peakC = 0;
  for (const r of rows) {
    const tot = r.male + r.female;
    if (tot > peakC) { peakC = tot; peakAge = r.age; }
  }
  const peakX = xOf(peakAge);

  svg.innerHTML = `
    <g class="voyage-grid">${gridH}</g>
    <g class="voyage-axis">${axisX}</g>
    <text x="${P.l}" y="${P.t - 4}" class="voyage-axis">deaths</text>
    <text x="${W - P.r}" y="${P.t + innerH + 30}" class="voyage-axis" text-anchor="end">age</text>
    <path class="voyage-area-male"   d="${areaPath('male')}"/>
    <path class="voyage-area-female" d="${areaPath('female')}"/>
    <path fill="none" stroke="#5a7fa0" stroke-width="1.4" d="${linePath('male')}"/>
    <path fill="none" stroke="#c4839b" stroke-width="1.4" d="${linePath('female')}"/>
    <line class="voyage-peak-line" x1="${peakX}" y1="${P.t}" x2="${peakX}" y2="${P.t + innerH}"/>
    <text class="voyage-peak-label" x="${peakX + 6}" y="${P.t + 14}">peak at age ${peakAge}</text>
  `;

  // aside narrative
  const infant = data.single.find((r) => r.age === 0)?.count ?? 0;
  const elders = data.single.filter((r) => r.age >= 75).reduce((s, r) => s + r.count, 0);
  aside.innerHTML = `
    <h3>The Shape of a Life</h3>
    <p class="vo-note">The median voyager reached <span class="vo-big">${data.median}</span> years before the end found them.</p>
    <p class="vo-note">A first steep valley marks the dawn — <span class="vo-big">${fmt(infant)}</span> souls who never saw a first birthday. Then the line goes quiet through childhood, before climbing hard into the working years.</p>
    <p class="vo-note">Most anchor here, in the long plateau of the seventh and eighth decades — <span class="vo-big">${fmt(elders)}</span> departed after their seventy-fifth year. Few outlast the sea; the curve thins to a whisper past ninety.</p>
  `;
}

// ───────────────────────────────────────────────────────────────────────
// 6. The Archipelago — Book III
// ───────────────────────────────────────────────────────────────────────
function renderArchipelago(data) {
  const maxCount = Math.max(...data.states.map((s) => s.count));
  $('#regions-river').innerHTML = data.regions.map((r) => `
    <div class="region-pill">
      <span class="rp-en">${r.label}</span>
      <span class="rp-ms">${r.ms}</span>
      <span class="rp-count">${fmt(r.count)}</span>
    </div>
  `).join('');

  $('#states-grid').innerHTML = data.states.map((s) => `
    <div class="state-card">
      <div class="sc-bar" style="--bar:${(s.count / maxCount * 100).toFixed(1)}%"></div>
      <div class="sc-inner">
        <div class="sc-name">${s.state}</div>
        <div class="sc-region">${s.region}</div>
        <div class="sc-count">${fmt(s.count)}</div>
        <div class="sc-pct">${s.pct}% of the catalogue</div>
        <div class="sc-districts">
          ${s.top_districts.map((d) => `
            <div class="d"><span class="n">${d.district}</span><span>${fmt(d.count)}</span></div>
          `).join('')}
        </div>
      </div>
    </div>
  `).join('');
}

// ───────────────────────────────────────────────────────────────────────
// 7. The Descent — Book XI(b). Interactive soul summoning.
// ───────────────────────────────────────────────────────────────────────
const EPITAPHS = {
  heart:      ['who set out at dawn and never returned from the harbour', 'whose heart, like a tide, simply turned', 'carried off in the hour they least expected'],
  breath:     ['who drew one last breath and let the wind have it', 'whose lungs filled their last cup of air', 'for whom the breathing stopped, soft as a sigh'],
  cancer:     ['who fought a long war within their own body', 'whose cells forgot the treaty of living', 'carried off by the slow rebellion within'],
  metabolic:  ['betrayed in the end by their own sweet blood', 'whose organs, one by one, struck their colours', 'whom the body undid from within'],
  pestilence: ['taken by the invisible army that crossed every sea', 'who fell when the plague came ashore', 'lost to the small, blind things that hunt us'],
  violence:   ['lost to the sudden storm of the road', 'whose end came sharp and quick', 'taken by a hand — their own, or another\'s'],
  dawn:       ['who never saw the noon of their life', 'lost at the very beginning of the voyage', 'whose mind, at last, drifted out with the tide'],
};

function epitaphFor(fate) {
  const arr = EPITAPHS[fate] || EPITAPHS.dawn;
  return arr[Math.floor(Math.random() * arr.length)];
}

function renderSoul(soul, i) {
  const card = document.createElement('article');
  card.className = 'soul-card';
  card.style.setProperty('--soul-color', soul.fate_color);
  card.style.animationDelay = `${i * 0.12}s`;
  const genderWord = soul.gender === 'male' ? 'A man' : 'A woman';
  card.innerHTML = `
    <div class="soul-glyph">${soul.fate_glyph}</div>
    <p class="soul-line"><span class="k">A soul of</span><span class="v">${soul.age}</span> years</p>
    <p class="soul-line"><span class="k">${genderWord} from</span><span class="v">${soul.district}, ${soul.state}</span></p>
    <p class="soul-line"><span class="k">${soul.ethnicity}</span></p>
    <p class="soul-line cause">taken by ${soul.cause}</p>
    <p class="soul-epitaph">— ${epitaphFor(soul.fate)}</p>
  `;
  // A soft whisper as each soul rises — staggered to match the fade-in.
  if (typeof sound !== 'undefined') {
    sound.play('whisper-rise', { delay: i * 120 });
  }
  return card;
}

async function initDescent() {
  // populate filter dropdowns
  const [facetsResp] = await Promise.all([getJSON('/api/facets')]);
  const fill = (id, list) => {
    const sel = $(id);
    for (const v of list) {
      const o = document.createElement('option');
      o.value = v; o.textContent = v;
      sel.appendChild(o);
    }
  };
  fill('#f-cause', facetsResp.causes);
  fill('#f-state', facetsResp.states);
  fill('#f-ethnicity', facetsResp.ethnicities);

  $('#descent-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = $('#summon-btn');
    btn.classList.add('loading');
    const well = $('#souls-well');
    well.innerHTML = `<p class="souls-empty">The souls are rising from the trench…</p>`;
    // A deep bell tolls as the offering is poured.
    if (typeof sound !== 'undefined') sound.play('bell-summon');

    const params = new URLSearchParams();
    const cause = $('#f-cause').value;       if (cause) params.set('cause', cause);
    const state = $('#f-state').value;       if (state) params.set('state', state);
    const eth   = $('#f-ethnicity').value;   if (eth) params.set('ethnicity', eth);
    const g     = $('#f-gender').value;      if (g) params.set('gender', g);
    const amin  = $('#f-age-min').value;     if (amin !== '') params.set('age_min', amin);
    const amax  = $('#f-age-max').value;     if (amax !== '') params.set('age_max', amax);
    params.set('n', '6');

    try {
      const data = await getJSON('/api/souls?' + params.toString());
      if (!data.souls.length) {
        well.innerHTML = `<p class="souls-empty">No soul in the catalogue answers to this offering. Loosen the filters and pour again.</p>`;
        return;
      }
      well.innerHTML = `<div class="souls-meta">${data.count} soul${data.count > 1 ? 's' : ''} rose from the catalogue</div>`;
      const list = document.createElement('div');
      list.className = 'souls-list';
      data.souls.forEach((s, i) => list.appendChild(renderSoul(s, i)));
      well.appendChild(list);
    } catch (err) {
      well.innerHTML = `<p class="souls-empty">The trench gave no answer. (${err.message})</p>`;
    } finally {
      btn.classList.remove('loading');
    }
  });
}

// ───────────────────────────────────────────────────────────────────────
// 8. Voyage nav — highlight the current book as you scroll.
// ───────────────────────────────────────────────────────────────────────
function initNavObserver() {
  const links = $$('.voyage-nav a');
  const sections = $$('section.book');
  const map = new Map(links.map((a) => [a.getAttribute('href').slice(1), a]));
  const obs = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (e.isIntersecting) {
        links.forEach((l) => l.classList.remove('is-active'));
        const a = map.get(e.target.id);
        if (a) a.classList.add('is-active');
      }
    }
  }, { rootMargin: '-40% 0px -50% 0px' });
  sections.forEach((s) => obs.observe(s));
}

// ───────────────────────────────────────────────────────────────────────
// 9a. Atmospheric sound — unlock on first gesture, run ambient beds,
//     and fade layers in/out as the visitor descends through the books.
// ───────────────────────────────────────────────────────────────────────
function initSound() {
  if (typeof sound === 'undefined') return;

  // Restore the visitor's last preference. Default to muted unless they've
  // explicitly opted in — audio should always be a choice.
  let optedIn = false;
  try {
    // Key bumped (v2) to invalidate stale 'on' values saved under the buggy
    // toggle that never unmuted — forces everyone back to the muted default.
    optedIn = localStorage.getItem('nekyia:sound-v2') === 'on';
  } catch (e) { /* localStorage may be blocked */ }
  if (!optedIn) sound.setMuted(true);

  // The toggle button drives everything. First click also serves as the
  // user gesture that unlocks audio per browser autoplay policy.
  const toggle = $('#sound-toggle');
  const syncToggle = () => {
    if (!toggle) return;
    toggle.classList.toggle('is-on', !sound.isMuted);
    toggle.setAttribute('aria-pressed', sound.isMuted ? 'false' : 'true');
    toggle.title = sound.isMuted ? 'Enable sound' : 'Mute sound';
  };
  syncToggle();
  if (toggle) {
    toggle.addEventListener('click', () => {
      sound.unlock();
      const nowOn = sound.isMuted;     // muted now → this click means "turn on"
      sound.setMuted(!nowOn);          // mute iff turning off
      if (nowOn && !sound.isMuted) {
        // Just enabled — start the ambient bed if not already running.
        sound.fadeIn('ambient-drone', 2000);
      }
      try { localStorage.setItem('nekyia:sound-v2', nowOn ? 'on' : 'off'); } catch (e) {}
      syncToggle();
    });
  }

  // Ambient layers tied to scroll position.
  // Sea of Souls — swell layer fades in.
  const seaObs = new IntersectionObserver((entries, obs) => {
    for (const e of entries) {
      if (e.isIntersecting) {
        if (!sound.isMuted) sound.fadeIn('wave-swell', 3000);
        obs.disconnect();
      }
    }
  }, { rootMargin: '100px' });
  const bookV = $('#book-v');
  if (bookV) seaObs.observe(bookV);

  // The Return — drone fades out, final bell tolls.
  const returnObs = new IntersectionObserver((entries, obs) => {
    for (const e of entries) {
      if (e.isIntersecting) {
        sound.fadeOut('ambient-drone', 3000);
        sound.fadeOut('wave-swell', 2000);
        sound.play('bell-final', { delay: 400 });
        obs.disconnect();
      }
    }
  }, { rootMargin: '100px' });
  const bookReturn = $('#book-xxiii');
  if (bookReturn) returnObs.observe(bookReturn);
}

// ───────────────────────────────────────────────────────────────────────
// 9b. Boot the voyage.
// ───────────────────────────────────────────────────────────────────────
async function boot() {
  // Background sea — runs immediately.
  new WineDarkSea($('#sea-canvas'));

  // Animate invocation counter.
  const counter = $('.stat-number[data-count]');
  if (counter) {
    const target = Number(counter.dataset.count);
    // delay to let the title land
    setTimeout(() => animateCount(counter, target), 2100);
  }

  // Fetch all data in parallel.
  const [fatesResp, ageResp, archiResp] = await Promise.all([
    getJSON('/api/fates'),
    getJSON('/api/age'),
    getJSON('/api/archipelago'),
  ]);

  // Sea of Souls — needs fate proportions.
  $('#sea-total').textContent = fmt(fatesResp.total);
  // Lazy-init the sea canvas when its book scrolls into view (perf).
  const seaObs = new IntersectionObserver((entries, obs) => {
    for (const e of entries) {
      if (e.isIntersecting) {
        new SeaOfSouls($('#sea-stage'), fatesResp.fates, fatesResp.total);
        obs.disconnect();
      }
    }
  }, { rootMargin: '200px' });
  seaObs.observe($('#book-v'));

  // Fates.
  renderFates(fatesResp.fates, fatesResp.total);

  // Voyage of Years.
  renderVoyage(ageResp);

  // Archipelago.
  renderArchipelago(archiResp);

  // Descent form.
  await initDescent();

  // Atmospheric sound — toggle, ambient beds, scroll-cued fades.
  initSound();

  // Nav highlight.
  initNavObserver();
}

document.addEventListener('DOMContentLoaded', boot);
