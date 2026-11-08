/* ==========================================================
   Incubator runtime — core.js (shared engine, inlined by build.py)
   Exposes window.INC for the template-specific signature script.
   ========================================================== */
(() => {
  'use strict';
  const CFG = window.INC_CONFIG || {};
  const doc = document.documentElement;

  /* ---------- Utilities ---------- */
  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => [...c.querySelectorAll(s)];
  const lerp = (a, b, t) => a + (b - a) * t;
  const clamp = (v, min, max) => Math.min(Math.max(v, min), max);
  const mapRange = (v, a, b, c, d) => c + (d - c) * clamp((v - a) / (b - a), 0, 1);
  const throttle = (fn, wait) => { let last = 0; return (...args) => { const now = performance.now(); if (now - last >= wait) { last = now; fn(...args); } }; };
  const debounce = (fn, wait) => { let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), wait); }; };
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isTouch = window.matchMedia('(hover: none)').matches;

  /* ---------- Easing ---------- */
  const ease = {
    linear: t => t,
    outCubic: t => 1 - Math.pow(1 - t, 3),
    inOutQuart: t => (t < 0.5 ? 8 * t ** 4 : 1 - Math.pow(-2 * t + 2, 4) / 2),
    outExpo: t => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t)),
    outBack: t => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
    outElastic: t => (t === 0 || t === 1 ? t : Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * ((2 * Math.PI) / 3)) + 1)
  };
  /* Tween helper: INC.tween(ms, easeFn, p => {...}) → Promise */
  const tween = (duration, easeFn, onUpdate) => new Promise(resolve => {
    if (reduceMotion || duration <= 0) { onUpdate(1); resolve(); return; }
    const t0 = performance.now();
    const step = now => {
      const p = clamp((now - t0) / duration, 0, 1);
      onUpdate(easeFn(p));
      if (p < 1) requestAnimationFrame(step); else resolve();
    };
    requestAnimationFrame(step);
  });

  /* ---------- Public API ---------- */
  const frameFns = [], readyFns = [], resizeFns = [];
  const mouse = { x: innerWidth / 2, y: innerHeight / 2, nx: 0, ny: 0 };
  const scroll = { current: window.scrollY, target: window.scrollY, velocity: 0, progress: 0 };
  const INC = window.INC = {
    $, $$, lerp, clamp, mapRange, throttle, debounce, ease, tween, reduceMotion, isTouch, mouse, scroll, isReady: false,
    onFrame: fn => { frameFns.push(fn); },
    onResize: fn => { resizeFns.push(fn); },
    onReady: fn => { if (INC.isReady) fn(); else readyFns.push(fn); }
  };

  /* ==========================================================
     Inertial smooth scroll (lerp over a fixed #scrollWrap)
     Disabled by <html data-smooth="off">, touch, reduced motion.
     ========================================================== */
  const wrap = $('#scrollWrap');
  const smoothOn = !!wrap && !reduceMotion && !isTouch && doc.dataset.smooth !== 'off';
  if (!smoothOn) doc.classList.add('no-smooth');
  const setBodyHeight = () => { if (smoothOn) document.body.style.height = `${wrap.getBoundingClientRect().height}px`; };
  if (smoothOn && 'ResizeObserver' in window) new ResizeObserver(setBodyHeight).observe(wrap);

  const updateScroll = () => {
    const prev = scroll.current;
    scroll.target = window.scrollY;
    scroll.current = smoothOn ? lerp(scroll.current, scroll.target, CFG.scrollEase || 0.085) : scroll.target;
    if (Math.abs(scroll.target - scroll.current) < 0.05) scroll.current = scroll.target;
    scroll.velocity = scroll.current - prev;
    scroll.progress = clamp(scroll.current / Math.max(1, doc.scrollHeight - innerHeight), 0, 1);
    if (smoothOn) wrap.style.transform = `translate3d(0, ${-scroll.current}px, 0)`;
  };

  /* Eased anchor navigation */
  const scrollToEl = el => {
    const end = clamp(el.getBoundingClientRect().top + scroll.current - (CFG.anchorOffset || 0), 0, doc.scrollHeight - innerHeight);
    const start = window.scrollY;
    return tween(CFG.anchorDuration || 1300, ease.inOutQuart, p => window.scrollTo(0, start + (end - start) * p));
  };
  INC.scrollTo = scrollToEl;
  document.addEventListener('click', e => {
    const a = e.target.closest('a[href^="#"]');
    if (!a) return;
    const id = a.getAttribute('href').slice(1);
    const el = id && document.getElementById(id);
    if (!el) return;
    e.preventDefault();
    doc.classList.remove('nav-open');
    scrollToEl(el);
  });

  /* ---------- Pointer tracking (mouse + touch) ---------- */
  const setPointer = (x, y) => { mouse.x = x; mouse.y = y; mouse.nx = x / innerWidth - 0.5; mouse.ny = y / innerHeight - 0.5; };
  window.addEventListener('pointermove', e => setPointer(e.clientX, e.clientY), { passive: true });
  window.addEventListener('touchmove', e => { const t = e.touches[0]; if (t) setPointer(t.clientX, t.clientY); }, { passive: true });

  /* ==========================================================
     Split text → .split-unit spans (chars | words)
     ========================================================== */
  $$('[data-split]').forEach(el => {
    const text = el.textContent;
    const parts = el.dataset.split === 'words' ? text.split(/(\s+)/) : [...text];
    el.setAttribute('aria-label', text.trim());
    el.textContent = '';
    parts.forEach((part, i) => {
      if (!part) return;
      if (/^\s+$/.test(part)) { el.append(part); return; }
      const span = document.createElement('span');
      span.className = 'split-unit';
      span.setAttribute('aria-hidden', 'true');
      span.style.setProperty('--i', i);
      span.textContent = part;
      el.append(span);
    });
  });

  /* ==========================================================
     Scroll reveals (Intersection Observer + stagger)
     ========================================================== */
  $$('[data-stagger]').forEach(group => {
    const step = Number(group.dataset.stagger) || 90;
    [...group.children].filter(c => c.matches('[data-animation], [data-split]'))
      .forEach((c, i) => c.style.setProperty('--delay', `${i * step}ms`));
  });
  const revealIO = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      revealIO.unobserve(entry.target);
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -8% 0px' });

  /* Counters: data-count="240" data-pad="3" data-decimals="1" */
  const runCounter = el => {
    const end = Number(el.dataset.count), dec = Number(el.dataset.decimals) || 0, pad = Number(el.dataset.pad) || 0;
    const fmt = v => (dec ? v.toFixed(dec) : String(Math.round(v))).padStart(pad, '0');
    tween(Number(el.dataset.duration) || 1800, ease.outExpo, p => { el.textContent = fmt(end * p); });
  };
  const counterIO = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      counterIO.unobserve(entry.target);
      runCounter(entry.target);
    });
  }, { threshold: 0.6 });

  /* Typewriter: data-type="line one|line two" */
  const typeText = (el, lines, speed = 22) => new Promise(resolve => {
    const caret = document.createElement('span');
    caret.className = 'caret';
    caret.setAttribute('aria-hidden', 'true');
    el.setAttribute('aria-label', lines.join(' '));
    const done = [];
    let li = 0, ci = 0;
    const render = partial => { el.textContent = [...done, partial].filter(Boolean).join('\n'); el.appendChild(caret); };
    const step = () => {
      if (li >= lines.length) { render(''); resolve(); return; }
      ci++;
      render(lines[li].slice(0, ci));
      if (ci >= lines[li].length) { done.push(lines[li]); li++; ci = 0; setTimeout(step, reduceMotion ? 0 : 240); }
      else setTimeout(step, reduceMotion ? 0 : speed);
    };
    step();
  });
  INC.typeText = typeText;
  const typeIO = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      typeIO.unobserve(entry.target);
      typeText(entry.target, entry.target.dataset.type.split('|'), Number(entry.target.dataset.typeSpeed) || 22);
    });
  }, { threshold: 0, rootMargin: '0px 0px -10% 0px' });

  /* Text scramble on hover (text-only elements): data-scramble */
  const GLYPHS = CFG.glyphs || '!<>-_\\/[]{}=+*^?#01';
  const scramble = el => {
    if (reduceMotion) return;
    cancelAnimationFrame(el._scr || 0);
    const text = el._text || (el._text = el.textContent);
    const queue = [...text].map((ch, i) => ({ ch, start: Math.floor(Math.random() * 6), end: 6 + i + Math.floor(Math.random() * 8) }));
    let frame = 0;
    const update = () => {
      let out = '', done = 0;
      for (const q of queue) {
        if (frame >= q.end) { done++; out += q.ch; }
        else if (frame >= q.start && q.ch.trim()) out += GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
        else out += q.ch;
      }
      el.textContent = out;
      if (done < queue.length) { frame++; el._scr = requestAnimationFrame(update); }
    };
    update();
  };
  INC.scramble = scramble;
  $$('[data-scramble]').forEach(el => el.addEventListener('pointerenter', () => scramble(el)));

  /* ==========================================================
     Magnetic elements: data-magnetic="0.35"
     ========================================================== */
  if (!isTouch && !reduceMotion) {
    $$('[data-magnetic]').forEach(el => {
      const strength = Number(el.dataset.magnetic) || 0.35;
      el.addEventListener('pointermove', e => {
        const r = el.getBoundingClientRect();
        el.style.transform = `translate3d(${(e.clientX - r.left - r.width / 2) * strength}px, ${(e.clientY - r.top - r.height / 2) * strength}px, 0)`;
      });
      el.addEventListener('pointerleave', () => { el.style.transform = ''; });
    });
  }

  /* Spotlight vars inside elements: data-spot → --mx / --my */
  $$('[data-spot]').forEach(el => el.addEventListener('pointermove', e => {
    const r = el.getBoundingClientRect();
    el.style.setProperty('--mx', `${e.clientX - r.left}px`);
    el.style.setProperty('--my', `${e.clientY - r.top}px`);
  }));

  /* ==========================================================
     Parallax: data-speed (scroll, relative to viewport centre)
     and data-mouse (pointer depth). Not for data-animation nodes.
     ========================================================== */
  const parallaxEls = $$('[data-speed], [data-mouse]');
  const measureParallax = () => parallaxEls.forEach(el => {
    el.style.transform = '';
    const r = el.getBoundingClientRect();
    el._base = r.top + scroll.current + r.height / 2;
  });
  const updateParallax = () => {
    if (reduceMotion) return;
    for (const el of parallaxEls) {
      const s = Number(el.dataset.speed) || 0, m = Number(el.dataset.mouse) || 0;
      const y = (el._base - scroll.current - innerHeight / 2) * s;
      el.style.transform = `translate3d(${mouse.nx * m * 100}px, ${y + mouse.ny * m * 100}px, 0)`;
    }
  };

  /* ==========================================================
     Navigation: [data-nav] active links + [data-nav-indicator],
     [data-nav-hide] hide on scroll down, [data-nav-toggle] menu
     ========================================================== */
  const navs = $$('[data-nav]');
  let activeId = '';
  const moveIndicators = () => navs.forEach(nav => {
    const ind = $('[data-nav-indicator]', nav), link = $('a.is-active', nav);
    if (!ind || !link || !ind.offsetParent) return;
    const pr = ind.offsetParent.getBoundingClientRect(), lr = link.getBoundingClientRect();
    ind.style.width = `${lr.width}px`;
    ind.style.height = `${lr.height}px`;
    ind.style.transform = `translate3d(${lr.left - pr.left}px, ${lr.top - pr.top}px, 0)`;
  });
  const setActive = id => {
    activeId = id;
    navs.forEach(nav => $$('a[href^="#"]', nav).forEach(a => {
      const on = a.getAttribute('href') === `#${id}`;
      a.classList.toggle('is-active', on);
      if (on) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current');
    }));
    doc.dataset.section = id;
    moveIndicators();
  };
  INC.setActive = setActive;
  const sectionIO = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) setActive(e.target.id); });
  }, { rootMargin: '-45% 0px -50% 0px' });
  $$('main section[id]').forEach(s => sectionIO.observe(s));

  const hideEls = $$('[data-nav-hide]');
  let lastY = window.scrollY;
  window.addEventListener('scroll', throttle(() => {
    const y = window.scrollY;
    hideEls.forEach(el => el.classList.toggle('is-hidden', y > lastY && y > 240 && !doc.classList.contains('nav-open')));
    doc.classList.toggle('is-scrolled', y > 40);
    lastY = y;
  }, 100), { passive: true });
  $$('[data-nav-toggle]').forEach(btn => btn.addEventListener('click', () => {
    const open = doc.classList.toggle('nav-open');
    btn.setAttribute('aria-expanded', String(open));
  }));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') doc.classList.remove('nav-open'); });

  /* Clocks: data-clock */
  const clocks = $$('[data-clock]');
  const tickClock = () => {
    const d = new Date();
    const str = [d.getHours(), d.getMinutes(), d.getSeconds()].map(n => String(n).padStart(2, '0')).join(':');
    clocks.forEach(c => { c.textContent = str; });
  };
  if (clocks.length) { tickClock(); setInterval(tickClock, 1000); }
  const progressEls = $$('[data-progress]');

  /* ==========================================================
     Custom cursor — variant chosen by INC_CONFIG.cursor
     Parts with data-lag follow the pointer, data-axis = lines.
     ========================================================== */
  const CURSORS = {
    ring: '<span class="c-dot" data-lag="1"></span><span class="c-ring" data-lag="0.16"></span>',
    crosshair: '<span class="c-line-x" data-axis="x"></span><span class="c-line-y" data-axis="y"></span><span class="c-core" data-lag="0.25"></span>',
    blend: '<span class="c-blob" data-lag="0.14"></span>',
    label: '<span class="c-pill" data-lag="0.18"><span class="c-pill__text"></span></span>',
    trail: Array.from({ length: 10 }, (_, i) => `<span class="c-trail" style="--k:${(1 - i * 0.08).toFixed(2)}" data-lag="${(0.4 - i * 0.032).toFixed(3)}"></span>`).join(''),
    spotlight: '<span class="c-spot"></span><span class="c-dot" data-lag="0.3"></span>'
  };
  let cursorEl = null, cursorParts = [];
  if (!isTouch && !reduceMotion && CURSORS[CFG.cursor]) {
    cursorEl = document.createElement('div');
    cursorEl.className = `inc-cursor inc-cursor--${CFG.cursor}`;
    cursorEl.setAttribute('aria-hidden', 'true');
    cursorEl.innerHTML = CURSORS[CFG.cursor];
    document.body.appendChild(cursorEl);
    doc.classList.add('has-cursor');
    cursorParts = $$('[data-lag], [data-axis]', cursorEl).map(el => ({ el, lag: Number(el.dataset.lag) || 1, axis: el.dataset.axis, x: mouse.x, y: mouse.y }));
    const label = $('.c-pill__text', cursorEl);
    document.addEventListener('pointerover', e => {
      const hot = e.target.closest('a, button, [data-magnetic], [data-cursor]');
      doc.classList.toggle('cursor-hover', !!hot);
      doc.classList.toggle('cursor-text', !hot && !!e.target.closest('p, h1, h2, h3, blockquote'));
      if (label) label.textContent = hot ? (hot.dataset.cursor || 'View') : '';
    });
    document.addEventListener('pointerdown', () => doc.classList.add('cursor-down'));
    document.addEventListener('pointerup', () => doc.classList.remove('cursor-down'));
  }
  const updateCursor = () => {
    if (!cursorEl) return;
    cursorEl.style.setProperty('--cx', `${mouse.x}px`);
    cursorEl.style.setProperty('--cy', `${mouse.y}px`);
    for (const p of cursorParts) {
      if (p.axis === 'x') { p.el.style.transform = `translate3d(${mouse.x}px, 0, 0)`; continue; }
      if (p.axis === 'y') { p.el.style.transform = `translate3d(0, ${mouse.y}px, 0)`; continue; }
      p.x = lerp(p.x, mouse.x, p.lag);
      p.y = lerp(p.y, mouse.y, p.lag);
      p.el.style.transform = `translate3d(${p.x}px, ${p.y}px, 0)`;
    }
  };

  /* ==========================================================
     Preloader — simulated progress, then staggered page reveal
     ========================================================== */
  const loader = $('#incLoader');
  const finishLoad = () => {
    document.body.classList.remove('is-loading');
    document.body.classList.add('is-ready');
    if (loader) { loader.classList.add('is-done'); setTimeout(() => loader.classList.add('is-gone'), 1600); }
    setBodyHeight();
    measureParallax();
    $$('[data-animation], [data-split]').forEach(el => revealIO.observe(el));
    $$('[data-count]').forEach(el => counterIO.observe(el));
    $$('[data-type]').forEach(el => typeIO.observe(el));
    if (!activeId) { const first = $('main section[id]'); if (first) setActive(first.id); }
    INC.isReady = true;
    readyFns.splice(0).forEach(fn => fn());
  };
  const runLoader = () => {
    if (!loader) { finishLoad(); return; }
    const pctEls = $$('[data-loader-pct]', loader), bar = $('[data-loader-bar]', loader);
    const grid = $('[data-loader-grid]', loader), word = $('[data-loader-words]', loader);
    const cells = [];
    if (grid) for (let i = 0; i < 40; i++) { const c = document.createElement('i'); grid.appendChild(c); cells.push(c); }
    const order = cells.map((_, i) => i).sort(() => Math.random() - 0.5);
    const words = word ? word.dataset.loaderWords.split('|') : [];
    let progress = 0;
    const step = () => {
      progress = Math.min(100, progress + Math.random() * 8 + 3);
      pctEls.forEach(el => { el.textContent = String(Math.floor(progress)).padStart(Number(el.dataset.loaderPct) || 0, '0'); });
      if (bar) bar.style.transform = `scaleX(${progress / 100})`;
      order.slice(0, Math.floor((progress / 100) * cells.length)).forEach(i => cells[i].classList.add('is-on'));
      if (words.length) word.textContent = words[Math.min(words.length - 1, Math.floor((progress / 100) * words.length))];
      if (progress < 100) setTimeout(step, reduceMotion ? 0 : 55);
      else setTimeout(finishLoad, reduceMotion ? 0 : 320);
    };
    step();
  };

  /* ==========================================================
     Main RAF loop + init
     ========================================================== */
  const loop = now => {
    updateScroll();
    updateParallax();
    updateCursor();
    for (const el of progressEls) el.style.transform = `scaleX(${scroll.progress})`;
    for (const fn of frameFns) fn(now, scroll, mouse);
    requestAnimationFrame(loop);
  };
  window.addEventListener('resize', debounce(() => {
    setBodyHeight();
    measureParallax();
    moveIndicators();
    resizeFns.forEach(fn => fn());
  }, 150));

  setBodyHeight();
  requestAnimationFrame(loop);
  /* Defer so the template's signature script can register hooks first */
  setTimeout(runLoader, 0);
})();
