/* =========================================================
   共用：左側導覽、深淺色、數學式、程式碼上色與複製、表格篩選、小測驗
   每頁 <body data-page="c1" data-root="../" data-title="...">
   ========================================================= */
(function () {
  const SITE = {
    title: 'Plaxis2D Simulation',
    chapters: [
      { n: 1, id: 'ch1', name: 'Principle of Numerical Simulation', zh: '數值模擬原理', href: 'ch1_principle.html' },
      { n: 2, id: 'ch2', name: 'Input: Pre-Processing', zh: '前處理：GUI 與 Command', href: 'ch2_preprocessing.html' },
      { n: 3, id: 'ch3', name: 'Data Structures', zh: 'data.db 資料結構', href: 'ch3_data.html' },
      { n: 4, id: 'ch4', name: 'Post-Processing', zh: '後處理：Python 讀取與作圖', href: 'ch4_postprocessing.html' },
      { n: 5, id: 'ch5', name: 'Material Model – Mohr-Coulomb', zh: 'Mohr-Coulomb 組成律', href: 'ch5_mohrcoulomb.html' },
      { n: 6, id: 'ch6', name: 'Material Model – PM4Sand', zh: 'PM4Sand 組成律', href: 'ch6_pm4sand.html' }
    ],
    tables: [
      { n: 1, id: 'c1', name: '計算結果', href: 'tables/c1.html' },
      { n: 2, id: 'c2', name: '施工階段', href: 'tables/c2.html' },
      { n: 3, id: 'c3', name: '網格', href: 'tables/c3.html' },
      { n: 4, id: 'c4', name: '材料', href: 'tables/c4.html' },
      { n: 5, id: 'c5', name: '模型物件', href: 'tables/c5.html' },
      { n: 6, id: 'c6', name: '專案資訊', href: 'tables/c6.html' },
      { n: 7, id: 'c7', name: '代碼對照表', href: 'tables/c7.html' }
    ]
  };
  SITE.cats = SITE.tables;   // 舊名稱
  const CIRCLED = ['', '①', '②', '③', '④', '⑤', '⑥', '⑦'];

  /* ---------- 主題 ---------- */
  function applyTheme(t) {
    if (t === 'light' || t === 'dark') document.documentElement.setAttribute('data-theme', t);
    else document.documentElement.removeAttribute('data-theme');
  }
  try { applyTheme(localStorage.getItem('pdb-theme')); } catch (e) { }

  /* ---------- 左側導覽：寬螢幕固定在左；窄螢幕由 ☰ 叫出 ---------- */
  function buildSidebar(page, root) {
    const secs = [...document.querySelectorAll('main section.sec[id]')].filter(s => s.dataset.num || s.dataset.short);
    const secList = () => `<div class="sn-secs">${secs.map(s => {
      const num = s.dataset.num || '', short = s.dataset.short || s.dataset.title || '';
      return `<a href="#${s.id}">${num ? `<span class="n">${num}</span>` : ''}<span>${short}</span></a>`;
    }).join('')}</div>`;
    const item = (o, inner, cls = '') => `<a class="sn-item${cls}${o.id === page ? ' cur' : ''}" href="${root}${o.href}">${inner}</a>${o.id === page && secs.length ? secList() : ''}`;
    const inCh3 = page === 'ch3' || SITE.tables.some(t => t.id === page);
    const subs = SITE.tables.map(c => item(c, `<b>${CIRCLED[c.n]}</b><span>${c.name}</span>`, ' sn-sub')).join('');
    const chs = SITE.chapters.map(c =>
      item(c, `<b>${c.n}</b><span>${c.name}<small>${c.zh}</small></span>`, ' sn-ch') +
      (c.id === 'ch3' ? `<div class="sn-subs${inCh3 ? ' open' : ''}">${subs}</div>` : '')).join('');
    const side = document.createElement('aside');
    side.className = 'sidenav';
    side.innerHTML = `<div class="sn-top"><a class="brand" href="${root}index.html">Plaxis2D Simulation</a>
        <button class="icon-btn" id="themeBtn" title="切換深淺色">◐</button></div>
      <nav class="sn-scroll">
        ${item({ id: 'home', href: 'index.html' }, '<b>⌂</b><span>首頁</span>')}
        <div class="sn-stage">Chapters</div>${chs}</nav>`;
    const mbar = document.createElement('header');
    mbar.className = 'mbar';
    mbar.innerHTML = `<button class="icon-btn sn-toggle" title="導覽">☰</button><a class="ln-title" href="#top">${document.body.dataset.title || SITE.title}</a>`;
    const scrim = document.createElement('div');
    scrim.className = 'sn-scrim';
    document.body.prepend(scrim);
    document.body.prepend(mbar);
    document.body.prepend(side);
    document.body.classList.add('has-side');

    const setOpen = v => document.body.classList.toggle('sn-open', v);
    mbar.querySelector('.sn-toggle').addEventListener('click', () => setOpen(!document.body.classList.contains('sn-open')));
    scrim.addEventListener('click', () => setOpen(false));
    side.addEventListener('click', e => { if (e.target.closest('a')) setOpen(false); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') setOpen(false); });
    side.querySelector('#themeBtn').addEventListener('click', () => {
      let cur = null;
      try { cur = localStorage.getItem('pdb-theme'); } catch (e) { }
      const dark = cur ? cur === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
      const next = dark ? 'light' : 'dark';
      try { localStorage.setItem('pdb-theme', next); } catch (e) { }
      applyTheme(next);
      document.dispatchEvent(new CustomEvent('themechange', { detail: next }));
    });

    // 目前所在節：側欄高亮，並捲進側欄可視範圍
    const box = side.querySelector('.sn-scroll');
    const curItem = box.querySelector('.sn-item.cur');
    if (curItem) box.scrollTop = Math.max(0, curItem.offsetTop - 80);
    const links = new Map([...box.querySelectorAll('.sn-secs a')].map(a => [a.getAttribute('href').slice(1), a]));
    if (!links.size) return;
    const io = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (!e.isIntersecting) return;
        const a = links.get(e.target.id);
        if (!a) return;
        links.forEach(x => x.classList.remove('active'));
        a.classList.add('active');
        const top = a.offsetTop, bot = top + a.offsetHeight;
        if (top < box.scrollTop + 60 || bot > box.scrollTop + box.clientHeight - 60)
          box.scrollTo({ top: top - box.clientHeight / 2, behavior: 'smooth' });
      });
    }, { rootMargin: '-30% 0px -65% 0px' });
    secs.forEach(s => io.observe(s));
  }

  /* ---------- 數學式：頁面有載入 KaTeX auto-render 才處理 ---------- */
  function initMath() {
    if (typeof window.renderMathInElement !== 'function') return;
    window.renderMathInElement(document.body, {
      delimiters: [
        { left: '$$', right: '$$', display: true },
        { left: '\\[', right: '\\]', display: true },
        { left: '\\(', right: '\\)', display: false }
      ],
      ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code', 'option'],
      throwOnError: false
    });
  }

  /* ---------- 程式碼上色（Python／SQL）：只處理字串、註解、數字、關鍵字 ---------- */
  const KW = {
    python: 'False|None|True|and|as|assert|break|class|continue|def|del|elif|else|except|finally|for|from|if|import|in|is|lambda|not|or|pass|raise|return|try|while|with|yield',
    sql: 'SELECT|FROM|WHERE|JOIN|LEFT|ON|AND|OR|NOT|IN|AS|GROUP|BY|ORDER|LIMIT|COUNT|SUM|MIN|MAX|DISTINCT|DESC|ASC|LIKE|IS|NULL|HAVING|CASE|WHEN|THEN|ELSE|END|PRAGMA|length|hex|substr|typeof|UNION|ALL'
  };
  const BUILTIN = 'print|len|range|dict|list|zip|sorted|enumerate|int|float|str|max|min|abs|round|set|tuple|open|sum|any|all';
  function highlight(code) {
    const lang = code.className.includes('lang-sql') ? 'sql' : code.className.includes('lang-plx') ? 'plx' : 'python';
    const src = code.textContent;
    const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    // plx = PLAXIS Commands：行首單字是指令（cmd），# 之後是註解
    const parts = lang === 'sql'
      ? [['c', /--[^\n]*/], ['s', /'(?:[^']|'')*'/], ['n', /\b\d+(?:\.\d+)?\b/], ['k', new RegExp(`\\b(?:${KW.sql})\\b`, 'i')]]
      : lang === 'plx'
      ? [['c', /#[^\n]*/], ['s', /"[^"\n]*"/], ['cmd', /^[ \t]*_?[a-z][a-z0-9]*\b/], ['b', /\b(?:True|False)\b/], ['n', /-?\b\d+(?:\.\d+)?(?:e-?\d+)?\b/]]
      : [['c', /#[^\n]*/], ['s', /[rfbu]{0,2}(?:'''[\s\S]*?'''|"""[\s\S]*?"""|'(?:\\.|[^'\\\n])*'|"(?:\\.|[^"\\\n])*")/], ['n', /\b\d+(?:\.\d+)?(?:e-?\d+)?\b/], ['k', new RegExp(`\\b(?:${KW.python})\\b`)], ['b', new RegExp(`\\b(?:${BUILTIN})(?=\\()`)]];
    const re = new RegExp(parts.map(p => `(${p[1].source})`).join('|'), lang === 'sql' ? 'gi' : lang === 'plx' ? 'gm' : 'g');
    let out = '', last = 0, m;
    while ((m = re.exec(src))) {
      if (m[0] === '') { re.lastIndex++; continue; }
      const k = parts.findIndex((p, i) => m[i + 1] !== undefined);
      out += esc(src.slice(last, m.index)) + `<span class="tk-${parts[k][0]}">${esc(m[0])}</span>`;
      last = m.index + m[0].length;
    }
    code.innerHTML = out + esc(src.slice(last));
  }

  function initCode() {
    document.querySelectorAll('.codeblock pre code.lang-python, .codeblock pre code.lang-sql, .codeblock pre code.lang-plx').forEach(highlight);
    document.querySelectorAll('.codeblock .cb-copy').forEach(b => b.addEventListener('click', () => {
      const txt = b.closest('.codeblock').querySelector('pre code').textContent;
      const done = () => { b.textContent = '已複製'; setTimeout(() => (b.textContent = '複製'), 1400); };
      if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(txt).then(done, () => fallback(txt, done));
      else fallback(txt, done);
    }));
    function fallback(txt, done) {
      const t = document.createElement('textarea');
      t.value = txt; t.style.position = 'fixed'; t.style.opacity = '0';
      document.body.appendChild(t); t.select();
      try { document.execCommand('copy'); done(); } catch (e) { }
      t.remove();
    }
  }

  /* ---------- 長表格篩選 ---------- */
  function initFilters() {
    document.querySelectorAll('input.filterbox[data-target]').forEach(inp => {
      const tbl = document.getElementById(inp.dataset.target);
      if (!tbl) return;
      const rows = [...tbl.querySelectorAll('tr')].slice(1);
      const cnt = document.getElementById(inp.dataset.target + '-n');
      inp.addEventListener('input', () => {
        const q = inp.value.trim().toLowerCase();
        let n = 0;
        rows.forEach(r => { const ok = !q || r.textContent.toLowerCase().includes(q); r.style.display = ok ? '' : 'none'; if (ok) n++; });
        if (cnt) cnt.textContent = n;
      });
    });
  }

  /* ---------- 小測驗 ---------- */
  function initQuizzes() {
    document.querySelectorAll('.quiz').forEach(q => {
      const fb = q.querySelector('.fb');
      const ans = +q.dataset.answer;
      const opts = [...q.querySelectorAll('.opt')];
      opts.forEach((b, i) => b.addEventListener('click', () => {
        opts.forEach(o => o.classList.remove('right', 'wrong'));
        b.classList.add(i === ans ? 'right' : 'wrong');
        opts[ans].classList.add('right');
        fb.classList.add('show');
        fb.classList.toggle('ok', i === ans);
        fb.classList.toggle('no', i !== ans);
        let v = fb.querySelector('.verdict');
        if (!v) { v = document.createElement('span'); v.className = 'verdict'; fb.prepend(v); }
        v.textContent = i === ans ? '答對了。' : '再想想，解說如下：';
      }));
    });
  }

  window.SITE = SITE;
  document.addEventListener('DOMContentLoaded', () => {
    buildSidebar(document.body.dataset.page || '', document.body.dataset.root || '');
    initMath();
    initCode();
    initFilters();
    initQuizzes();
  });
})();
