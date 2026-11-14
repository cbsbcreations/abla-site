// Site script for abla.co: menus, header, button labels, star field, word reveal, scroll reveal, order-flow steps, demo form.
(function () {
  var root = document.documentElement;
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Close open menus when clicking elsewhere
  document.addEventListener('click', function (e) {
    document.querySelectorAll('details.dd[open], details.mobile-menu[open]').forEach(function (d) { if (!d.contains(e.target)) d.removeAttribute('open'); });
  });

  // Copy WhatsApp number
  document.querySelectorAll('[data-copy]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var text = btn.getAttribute('data-copy');
      var done = function () { var old = btn.textContent; btn.textContent = btn.getAttribute('data-done') || 'OK'; setTimeout(function () { btn.textContent = old; }, 1800); };
      try { navigator.clipboard.writeText(text).then(done, function () { selectNum(); }); } catch (err) { selectNum(); }
    });
  });
  function selectNum() {
    var el = document.querySelector('.wa-number'); if (!el) return;
    var r = document.createRange(); r.selectNodeContents(el); var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
  }

  // Demo form: opens WhatsApp with the request to Abla's number (data-wa), or else the email app (data-to).
  // While neither is set (placeholders in the preview), it only shows the note under the button.
  var form = document.querySelector('form.lead-form');
  if (form) form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (!form.reportValidity()) return;
    var lines = [];
    form.querySelectorAll('.field').forEach(function (f) {
      var lab = f.querySelector('label'), inp = f.querySelector('input, textarea');
      if (lab && inp && inp.value.trim()) lines.push(lab.textContent.trim() + ': ' + inp.value.trim());
    });
    var picked = [];
    form.querySelectorAll('input[name=interest]:checked').forEach(function (c) { picked.push(c.parentNode.textContent.trim()); });
    var leg = form.querySelector('legend');
    if (picked.length && leg) lines.push(leg.textContent.trim() + ' ' + picked.join(', '));
    var rest = form.querySelector('[name=restaurant]');
    var subject = (form.getAttribute('data-subject') || 'Demo') + (rest && rest.value.trim() ? ' - ' + rest.value.trim() : '');
    var wa = (form.getAttribute('data-wa') || '').replace(/[^0-9]/g, ''), to = form.getAttribute('data-to') || '';
    var msg = form.querySelector('.form-msg'); if (msg) msg.hidden = false;
    if (wa) window.location.href = 'https://wa.me/' + wa + '?text=' + encodeURIComponent(subject + '\n' + lines.join('\n'));
    else if (to) window.location.href = 'mailto:' + to + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(lines.join('\n'));
  });

  // Header state
  var header = document.querySelector('.site-header');
  if (header) {
    var onScroll = function () { header.classList.toggle('scrolled', window.scrollY > 24); };
    onScroll(); window.addEventListener('scroll', onScroll, { passive: true });
  }

  // Button labels roll up on hover
  document.querySelectorAll('a.btn').forEach(function (btn) {
    for (var i = 0; i < btn.childNodes.length; i++) {
      var n = btn.childNodes[i];
      if (n.nodeType === 3 && n.textContent.trim()) {
        var t = n.textContent.trim();
        var wrap = document.createElement('span'); wrap.className = 'roll';
        var inner = document.createElement('span'); inner.className = 'roll-in'; inner.setAttribute('data-t', t); inner.textContent = t;
        wrap.appendChild(inner); btn.replaceChild(wrap, n);
        break;
      }
    }
  });

  // Star field behind the page
  (function stars() {
    var c = document.createElement('canvas');
    c.className = 'stars'; c.setAttribute('aria-hidden', 'true');
    document.body.insertBefore(c, document.body.firstChild);
    var ctx = c.getContext && c.getContext('2d'); if (!ctx) return;
    var W = 0, H = 0, list = [], running = false, t0 = performance.now();
    function make() {
      var dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = window.innerWidth; H = window.innerHeight;
      c.width = W * dpr; c.height = H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var n = Math.round(W * H / 5200); list = [];
      for (var i = 0; i < n; i++) {
        var depth = Math.random();
        list.push({ x: Math.random() * W, y: Math.random() * H * 1.6, r: 0.35 + depth * 0.95, a: 0.25 + Math.random() * 0.6, s: 0.6 + Math.random() * 1.8, p: Math.random() * 6.28, d: 0.05 + depth * 0.3, v: 0.004 + depth * 0.012 });
      }
    }
    function draw(now) {
      var time = (now - t0) / 1000, sy = window.scrollY || 0, span = H * 1.6;
      ctx.clearRect(0, 0, W, H);
      for (var i = 0; i < list.length; i++) {
        var s = list[i];
        var y = (s.y - sy * s.d - (reduce ? 0 : time * s.v * 60)) % span; if (y < 0) y += span;
        if (y > H) continue;
        var tw = reduce ? 1 : 0.55 + 0.45 * Math.sin(time * s.s + s.p);
        ctx.globalAlpha = s.a * tw;
        ctx.fillStyle = s.r > 1.05 ? '#FFE3C4' : '#FFFFFF';
        ctx.beginPath(); ctx.arc(s.x, y, s.r, 0, 6.2832); ctx.fill();
      }
      ctx.globalAlpha = 1;
    }
    function loop(now) { if (!running) return; draw(now); requestAnimationFrame(loop); }
    function start() { if (reduce || running) return; running = true; requestAnimationFrame(loop); }
    make(); draw(performance.now()); start();
    window.addEventListener('resize', function () { make(); draw(performance.now()); });
    if (reduce) window.addEventListener('scroll', function () { draw(performance.now()); }, { passive: true });
    document.addEventListener('visibilitychange', function () { if (document.hidden) running = false; else start(); });
  })();

  // Headlines: words blur in one by one
  function splitWords(el) {
    var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null), nodes = [], n, idx = 0;
    while ((n = walker.nextNode())) nodes.push(n);
    nodes.forEach(function (node) {
      var parts = node.textContent.split(/(\s+)/), frag = document.createDocumentFragment();
      parts.forEach(function (p) {
        if (!p) return;
        if (/^\s+$/.test(p)) { frag.appendChild(document.createTextNode(p)); return; }
        var s = document.createElement('span'); s.className = 'w'; s.style.setProperty('--i', idx++); s.textContent = p; frag.appendChild(s);
      });
      node.parentNode.replaceChild(frag, node);
    });
    el.classList.add('split-ready');
  }
  if (!reduce && 'IntersectionObserver' in window) {
    var heads = document.querySelectorAll('.hero h1, .section-head h2, .cta h2');
    var ho = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('in'); ho.unobserve(en.target); } });
    }, { rootMargin: '0px 0px -6% 0px' });
    heads.forEach(function (h) { splitWords(h); ho.observe(h); });
  }

  // Reveal on scroll
  var sel = '.section-head > p, .section-head > .eyebrow, .card, .feature, .shot, .price, .faq details, .steps li, .cta p, .cta .btn-row, .stats';
  var items = Array.prototype.slice.call(document.querySelectorAll(sel));
  items.forEach(function (el) { el.classList.add('rv'); });
  var native = window.CSS && CSS.supports && CSS.supports('animation-timeline: view()');
  if (!reduce && !native && 'IntersectionObserver' in window) {
    root.classList.add('rv-js');
    var vh = window.innerHeight || 800;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.remove('below'); io.unobserve(en.target); } });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    items.forEach(function (el) {
      if (el.getBoundingClientRect().top > vh * 0.92) {
        var sibs = el.parentElement ? Array.prototype.indexOf.call(el.parentElement.children, el) : 0;
        el.style.setProperty('--d', Math.min(sibs, 5) * 0.07 + 's');
        el.classList.add('below');
        io.observe(el);
      }
    });
  }

  // Order flow: the sticky screen follows the step in view
  var stage = document.querySelector('.flow-stage');
  if (stage && 'IntersectionObserver' in window) {
    var steps = document.querySelectorAll('.flow-steps li');
    var fo = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        stage.setAttribute('data-step', en.target.getAttribute('data-s'));
        steps.forEach(function (li) { li.classList.toggle('on', li === en.target); });
      });
    }, { rootMargin: '-45% 0px -45% 0px' });
    steps.forEach(function (li) { fo.observe(li); });
  }

  // Soft light that follows the pointer on cards
  if (!reduce && window.matchMedia('(hover: hover)').matches) {
    document.querySelectorAll('.card, .price').forEach(function (el) {
      el.addEventListener('pointermove', function (e) {
        var r = el.getBoundingClientRect();
        el.style.setProperty('--mx', (e.clientX - r.left) + 'px');
        el.style.setProperty('--my', (e.clientY - r.top) + 'px');
      });
    });
  }
})();
