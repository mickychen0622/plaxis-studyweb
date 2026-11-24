
// MODEL-START
/* Mohr-Coulomb（含 ψ、tension cut-off）應力點回傳＋元素試驗。壓為正，kPa。 */
const MCLab = (() => {
  const D2R = Math.PI / 180;
  const dot3 = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];

  function material(P) {
    const E = P.E, nu = P.nu;
    const G = E / (2 * (1 + nu)), K = E / (3 * (1 - 2 * nu)), lam = K - 2 * G / 3;
    const sp = Math.sin(P.phi * D2R), cp = Math.cos(P.phi * D2R), ss = Math.sin(P.psi * D2R);
    const fs = [];
    for (const [i, j] of [[0, 1], [1, 2], [2, 0]]) for (const s of [1, -1]) {
      const a = [0, 0, 0], g = [0, 0, 0];
      a[i] = 0.5 * s - 0.5 * sp; a[j] = -0.5 * s - 0.5 * sp;
      g[i] = 0.5 * s - 0.5 * ss; g[j] = -0.5 * s - 0.5 * ss;
      fs.push({ a, b: -P.c * cp, g, type: 'mc' });
    }
    if (P.tc) for (let i = 0; i < 3; i++) {
      const a = [0, 0, 0]; a[i] = -1;
      fs.push({ a, b: -P.st, g: a.slice(), type: 'tc' });
    }
    const De = v => { const t = lam * (v[0] + v[1] + v[2]); return [t + 2 * G * v[0], t + 2 * G * v[1], t + 2 * G * v[2]]; };
    fs.forEach(f => { f.Dg = De(f.g); });
    const n = fs.length;
    const M = fs.map(fk => fs.map(fj => dot3(fk.a, fj.Dg)));
    // 所有大小 1–3 的組合
    const subsets = [];
    for (let i = 0; i < n; i++) subsets.push([i]);
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) subsets.push([i, j]);
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) for (let k = j + 1; k < n; k++) subsets.push([i, j, k]);
    const apex = sp > 1e-9 ? -P.c * cp / sp : -Infinity;   // 等向受拉頂點 σ = −c·cotφ
    return { P, G, K, lam, fs, M, subsets, De, apex, sp, cp };
  }

  function solve(A, b) {            // 小型線性系統（Gauss 消去，部分樞軸）
    const n = b.length, m = A.map((r, i) => r.concat([b[i]]));
    for (let c = 0; c < n; c++) {
      let p = c;
      for (let r = c + 1; r < n; r++) if (Math.abs(m[r][c]) > Math.abs(m[p][c])) p = r;
      if (Math.abs(m[p][c]) < 1e-12) return null;
      [m[c], m[p]] = [m[p], m[c]];
      for (let r = 0; r < n; r++) if (r !== c) {
        const k = m[r][c] / m[c][c];
        for (let q = c; q <= n; q++) m[r][q] -= k * m[c][q];
      }
    }
    return m.map((r, i) => r[n] / r[i]);
  }

  /* 主應力空間的回傳：彈性試算 s → 回到 f ≤ 0；多個面同時作用時用 Koiter 法則 */
  function returnMap(mat, s) {
    const fs = mat.fs;
    const scale = Math.max(Math.abs(s[0]), Math.abs(s[1]), Math.abs(s[2]), mat.P.c, 1);
    const tol = 1e-9 * scale;
    const fv = fs.map(f => dot3(f.a, s) + f.b);
    if (fv.every(v => v <= tol)) return { s, dep: [0, 0, 0], act: [], fmax: Math.max(...fv) };
    let best = null;
    for (const S of mat.subsets) {
      if (best && S.length > best.act.length) break;
      const A = S.map(k => S.map(j => mat.M[k][j]));
      const dl = solve(A, S.map(k => fv[k]));
      if (!dl || dl.some(x => x < -1e-12 * scale)) continue;
      const r = s.slice();
      S.forEach((j, q) => { for (let i = 0; i < 3; i++) r[i] -= dl[q] * fs[j].Dg[i]; });
      const fr = fs.map(f => dot3(f.a, r) + f.b);
      if (fr.every(v => v <= 1e-7 * scale)) {
        const dep = [0, 0, 0];
        S.forEach((j, q) => { for (let i = 0; i < 3; i++) dep[i] += dl[q] * fs[j].g[i]; });
        best = { s: r, dep, act: S, fmax: Math.max(...fr) };
        break;
      }
    }
    if (best) return best;
    // 落在錐頂（tension cut-off 關閉時）：直接回到頂點
    const a = mat.apex;
    const r = [a, a, a];
    const de = [s[0] - a, s[1] - a, s[2] - a];        // 應力差 → 由彈性柔度換回塑性應變
    const tr = (de[0] + de[1] + de[2]) / (9 * mat.K), dev = de.map(x => x - (de[0] + de[1] + de[2]) / 3);
    const dep = dev.map(x => x / (2 * mat.G) + tr);
    return { s: r, dep, act: [-1], fmax: 0 };
  }

  /* 3×3 對稱矩陣特徵分解（Jacobi） */
  function eigSym(S) {
    const a = S.map(r => r.slice()), V = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];
    for (let sweep = 0; sweep < 50; sweep++) {
      const off = Math.abs(a[0][1]) + Math.abs(a[0][2]) + Math.abs(a[1][2]);
      if (off < 1e-14 * (Math.abs(a[0][0]) + Math.abs(a[1][1]) + Math.abs(a[2][2]) + 1e-30)) break;
      for (const [p, q] of [[0, 1], [0, 2], [1, 2]]) {
        if (Math.abs(a[p][q]) < 1e-300) continue;
        const th = (a[q][q] - a[p][p]) / (2 * a[p][q]);
        const t = Math.sign(th || 1) / (Math.abs(th) + Math.sqrt(th * th + 1));
        const c = 1 / Math.sqrt(t * t + 1), s = t * c;
        for (let k = 0; k < 3; k++) { const akp = a[k][p], akq = a[k][q]; a[k][p] = c * akp - s * akq; a[k][q] = s * akp + c * akq; }
        for (let k = 0; k < 3; k++) { const apk = a[p][k], aqk = a[q][k]; a[p][k] = c * apk - s * aqk; a[q][k] = s * apk + c * aqk; }
        for (let k = 0; k < 3; k++) { const vkp = V[k][p], vkq = V[k][q]; V[k][p] = c * vkp - s * vkq; V[k][q] = s * vkp + c * vkq; }
      }
    }
    return { val: [a[0][0], a[1][1], a[2][2]], vec: V };   // vec 的第 i 欄是第 i 個特徵向量
  }

  const T = v => [[v[0], v[3], v[5]], [v[3], v[1], v[4]], [v[5], v[4], v[2]]];   // Voigt [xx,yy,zz,xy,yz,zx] → 張量
  const Vg = t => [t[0][0], t[1][1], t[2][2], t[0][1], t[1][2], t[2][0]];

  /* 一個應變增量（張量分量，剪應變為 ε 非 γ）→ 新應力；不改動輸入 */
  function update(mat, sig, de) {
    const tr = de[0] + de[1] + de[2];
    const st = sig.map((x, i) => x + (i < 3 ? mat.lam * tr + 2 * mat.G * de[i] : 2 * mat.G * de[i]));
    const e = eigSym(T(st));
    const r = returnMap(mat, e.val);
    if (!r.act.length) return { sig: st, dep: [0, 0, 0, 0, 0, 0], act: r.act, prin: e.val, fmax: r.fmax };
    const V = e.vec, out = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], dp = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
    for (let k = 0; k < 3; k++) for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) {
      out[i][j] += r.s[k] * V[i][k] * V[j][k];
      dp[i][j] += r.dep[k] * V[i][k] * V[j][k];
    }
    return { sig: Vg(out), dep: Vg(dp), act: r.act, prin: r.s, fmax: r.fmax };
  }

  /* 一維求根：f 單調遞增；割線＋二分 */
  function root(f, x0, h) {
    let a = x0, fa = f(a);
    if (Math.abs(fa) < 1e-10) return a;
    let step = h, b = a - Math.sign(fa) * step, fb = f(b), n = 0;
    while (fa * fb > 0 && n < 80) { a = b; fa = fb; step *= 2; b = a - Math.sign(fa) * step; fb = f(b); n++; }
    for (let it = 0; it < 200; it++) {
      let x = b - fb * (b - a) / (fb - fa);
      if (!(x > Math.min(a, b) && x < Math.max(a, b))) x = 0.5 * (a + b);
      const fx = f(x);
      if (Math.abs(fx) < 1e-9 || Math.abs(b - a) < 1e-16) return x;
      if (fx * fa < 0) { b = x; fb = fx; } else { a = x; fa = fx; }
    }
    return 0.5 * (a + b);
  }

  /* 元素試驗。軸向 = yy。cfg.test：TXC、TXE、CU、CUE、CYC、DSS、DSSU */
  function run(P, cfg) {
    const mat = material(P);
    const sv = cfg.sv0, sh = cfg.K0 * cfg.sv0;
    let sig = [sh, sv, sh, 0, 0, 0], eps = [0, 0, 0, 0, 0, 0], u = 0, epv = 0, epq = 0;
    const undr = ['CU', 'CUE', 'CYC'].includes(cfg.test);
    const isDSS = cfg.test === 'DSS' || cfg.test === 'DSSU';
    const nu = P.nu, nuu = cfg.nuu;
    const Kwn = 3 * (nuu - nu) / ((1 - 2 * nuu) * (1 + nu)) * mat.K;
    const N = cfg.steps, emax = cfg.emax / 100;
    // 每一步的控制應變（軸向應變或 γ）
    const ctrl = [];
    if (cfg.test === 'CYC') {
      const A = cfg.amp / 100, nc = cfg.ncyc, per = Math.max(8, Math.round(N / nc));
      for (let k = 1; k <= per * nc; k++) { const ph = (k / per) % 1; ctrl.push(A * (ph < 0.25 ? 4 * ph : ph < 0.75 ? 2 - 4 * ph : 4 * ph - 4)); }
    } else {
      const sgn = (cfg.test === 'TXE' || cfg.test === 'CUE') ? -1 : 1;
      for (let k = 1; k <= N; k++) ctrl.push(sgn * emax * k / N);
    }
    const rec = [];
    const push = (x, r) => {
      const p = (sig[0] + sig[1] + sig[2]) / 3;
      const J2 = ((sig[0] - sig[1]) ** 2 + (sig[1] - sig[2]) ** 2 + (sig[2] - sig[0]) ** 2) / 6 + sig[3] ** 2 + sig[4] ** 2 + sig[5] ** 2;
      const qi = Math.sqrt(3 * J2);
      const prin = eigSym(T(sig)).val.sort((a, b) => b - a);
      rec.push({ x, sig: sig.slice(), p, q: isDSS ? qi : sig[1] - sig[0], qi, u, pt: p + u,
        ev: eps[0] + eps[1] + eps[2], ea: eps[1], g: 2 * eps[3], epv, epq, prin,
        act: r ? r.act : [], fmax: r ? r.fmax : -1 });
    };
    push(0, null);
    let prev = 0;
    for (const c of ctrl) {
      const d = c - prev; prev = c;
      let r;
      if (cfg.test === 'TXC' || cfg.test === 'TXE') {
        const f = x => update(mat, sig, [x, d, x, 0, 0, 0]).sig[0] - sh;
        const x = root(f, -nu * d, Math.abs(d) * 0.5 + 1e-12);
        r = update(mat, sig, [x, d, x, 0, 0, 0]); eps[0] += x; eps[2] += x; eps[1] += d;
      } else if (undr) {
        const ev0 = eps[0] + eps[1] + eps[2];
        const uf = dev => { const v = Kwn * (ev0 + dev); return cfg.cav ? Math.max(v, -cfg.cavs) : v; };
        const f = x => update(mat, sig, [x, d, x, 0, 0, 0]).sig[0] + uf(d + 2 * x) - sh;
        const x = root(f, -d / 2, Math.abs(d) * 0.5 + 1e-12);
        r = update(mat, sig, [x, d, x, 0, 0, 0]); u = uf(d + 2 * x);
        eps[0] += x; eps[2] += x; eps[1] += d;
      } else if (cfg.test === 'DSS') {
        const f = y => update(mat, sig, [0, y, 0, d / 2, 0, 0]).sig[1] - sv;
        const y = root(f, 0, Math.abs(d) * 0.5 + 1e-12);
        r = update(mat, sig, [0, y, 0, d / 2, 0, 0]); eps[1] += y; eps[3] += d / 2;
      } else {        // DSSU：等體積單剪（不排水），Δu ＝ σv0 − σ′v
        r = update(mat, sig, [0, 0, 0, d / 2, 0, 0]); eps[3] += d / 2;
      }
      sig = r.sig;
      if (cfg.test === 'DSSU') u = sv - sig[1];
      epv += r.dep[0] + r.dep[1] + r.dep[2];
      const dm = (r.dep[0] + r.dep[1] + r.dep[2]) / 3;
      epq += Math.sqrt(2 / 3 * ((r.dep[0] - dm) ** 2 + (r.dep[1] - dm) ** 2 + (r.dep[2] - dm) ** 2 + 2 * (r.dep[3] ** 2 + r.dep[4] ** 2 + r.dep[5] ** 2)));
      push(c, r);
    }
    return { rec, mat, cfg, Kwn };
  }

  return { material, returnMap, update, run, eigSym };
})();
// MODEL-END

/* ================= 共用：SVG 作圖 ================= */
const PLT = (() => {
  const nice = (span, n) => { const raw = span / n, p = Math.pow(10, Math.floor(Math.log10(raw))), m = raw / p; return (m < 1.5 ? 1 : m < 3 ? 2 : m < 7 ? 5 : 10) * p; };
  const tfmt = (v, st) => { const d = Math.max(0, -Math.floor(Math.log10(st) + 1e-9)); return Math.abs(v) < st * 1e-6 ? '0' : v.toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d }); };
  let uid = 0;
  /* o: W,H,xr,yr,xl,yl,equal（等比例，左下角固定） */
  function chart(svg, o) {
    const W = o.W, H = o.H, ml = o.ml || 62, mr = 24, mt = 12, mb = 44;
    let [x0, x1] = o.xr, [y0, y1] = o.yr;
    if (!(x1 > x0)) x1 = x0 + 1; if (!(y1 > y0)) y1 = y0 + 1;
    if (o.equal) {
      const k = Math.min((W - ml - mr) / (x1 - x0), (H - mt - mb) / (y1 - y0));
      x1 = x0 + (W - ml - mr) / k; y1 = y0 + (H - mt - mb) / k;
    }
    const X = x => ml + (x - x0) / (x1 - x0) * (W - ml - mr), Y = y => H - mb - (y - y0) / (y1 - y0) * (H - mt - mb);
    const id = 'clp' + (++uid), parts = [];
    const c = {
      X, Y, x0, x1, y0, y1,
      path(xs, ys, st) { let d = ''; let pen = false; for (let i = 0; i < xs.length; i++) { const a = xs[i], b = ys[i]; if (!isFinite(a) || !isFinite(b)) { pen = false; continue; } d += (pen ? 'L' : 'M') + X(a).toFixed(1) + ' ' + Y(b).toFixed(1); pen = true; } if (d) parts.push(`<path d="${d}" style="fill:none;${st}"/>`); },
      raw(s) { parts.push(s); },
      dot(x, y, st, r = 4.5) { if (isFinite(x) && isFinite(y)) parts.push(`<circle cx="${X(x).toFixed(1)}" cy="${Y(y).toFixed(1)}" r="${r}" style="${st}"/>`); },
      text(x, y, s, st = '', anchor = 'start') { parts.push(`<text x="${X(x).toFixed(1)}" y="${Y(y).toFixed(1)}" text-anchor="${anchor}" style="font-size:12px;${st}">${s}</text>`); },
      done() {
        const sx = nice(x1 - x0, 5), sy = nice(y1 - y0, 5), tk = [];
        for (let v = Math.ceil(x0 / sx) * sx; v <= x1 + sx * 1e-9; v += sx) {
          const px = X(v).toFixed(1);
          tk.push(`<line class="tick" x1="${px}" y1="${H - mb}" x2="${px}" y2="${H - mb - 5}"/><line class="tick" x1="${px}" y1="${mt}" x2="${px}" y2="${mt + 5}"/><text class="tick-label" x="${px}" y="${H - mb + 17}" text-anchor="middle">${tfmt(v, sx)}</text>`);
        }
        for (let v = Math.ceil(y0 / sy) * sy; v <= y1 + sy * 1e-9; v += sy) {
          const py = Y(v).toFixed(1);
          tk.push(`<line class="tick" x1="${ml}" y1="${py}" x2="${ml + 5}" y2="${py}"/><line class="tick" x1="${W - mr}" y1="${py}" x2="${W - mr - 5}" y2="${py}"/><text class="tick-label" x="${ml - 7}" y="${(+py + 4).toFixed(1)}" text-anchor="end">${tfmt(v, sy)}</text>`);
        }
        const zero = (y0 < 0 && y1 > 0) ? `<line x1="${ml}" x2="${W - mr}" y1="${Y(0)}" y2="${Y(0)}" style="stroke:var(--line);stroke-width:1"/>` : '';
        const zerox = (x0 < 0 && x1 > 0) ? `<line y1="${mt}" y2="${H - mb}" x1="${X(0)}" x2="${X(0)}" style="stroke:var(--line);stroke-width:1"/>` : '';
        svg.innerHTML = `<defs><clipPath id="${id}"><rect x="${ml}" y="${mt}" width="${W - ml - mr}" height="${H - mt - mb}"/></clipPath></defs>`
          + zero + zerox + `<g clip-path="url(#${id})">${parts.join('')}</g>`
          + `<rect class="axis-frame" x="${ml}" y="${mt}" width="${W - ml - mr}" height="${H - mt - mb}"/>` + tk.join('')
          + `<text class="axis-label" x="${(ml + W - mr) / 2}" y="${H - 8}" text-anchor="middle">${o.xl}</text>`
          + `<text class="axis-label" transform="translate(15 ${(mt + H - mb) / 2}) rotate(-90)" text-anchor="middle">${o.yl}</text>`;
      }
    };
    return c;
  }
  function range(arrs, pad = 0.08, incl = []) {
    let lo = Infinity, hi = -Infinity;
    arrs.forEach(a => a.forEach(v => { if (isFinite(v)) { if (v < lo) lo = v; if (v > hi) hi = v; } }));
    incl.forEach(v => { if (v < lo) lo = v; if (v > hi) hi = v; });
    if (!isFinite(lo)) { lo = 0; hi = 1; }
    if (hi - lo < 1e-12) { const m = Math.abs(hi) || 1; lo -= 0.1 * m; hi += 0.1 * m; }
    const d = (hi - lo) * pad; return [lo - d, hi + d];
  }
  return { chart, range };
})();

/* ================= 5.6 元素試驗室 ================= */
(() => {
  const $ = id => document.getElementById(id);
  const D2R = Math.PI / 180;
  const fmt = (x, d = 0) => !isFinite(x) ? '—' : (Math.abs(x) < 0.5 * Math.pow(10, -d) ? 0 : x).toLocaleString('zh-TW', { maximumFractionDigits: d, minimumFractionDigits: d });
  const BLUE = 'stroke:var(--blue);stroke-width:2', GHOST = 'stroke:var(--gray);stroke-width:1.6',
    INK = 'stroke:var(--ink);stroke-width:1.3', INKD = 'stroke:var(--ink);stroke-width:1.2;stroke-dasharray:6 4',
    TCL = 'stroke:var(--red);stroke-width:1.3;stroke-dasharray:5 4', TOT = 'stroke:var(--gray);stroke-width:1.4;stroke-dasharray:5 4',
    PT = 'fill:var(--red);stroke:var(--bg);stroke-width:1.5';
  const TESTS = { TXC: '排水三軸壓縮', TXE: '排水三軸伸張', CU: '不排水三軸壓縮', CUE: '不排水三軸伸張', CYC: '不排水循環三軸', DSS: '排水單剪', DSSU: '等體積單剪' };
  const SOIL = { E: 20, nu: 0.3, c: 0, phi: 30, psi: 0, tc: true, st: 0 };
  const ROCK = { E: 15000, nu: 0.24, c: 1351, phi: 38.8, psi: 0, tc: true, st: 289 };
  const PRE = [
    { n: '排水三軸 ψ = 0', m: SOIL, t: { test: 'TXC', sv: 100, k0: 1, emax: 5 }, note: '降伏後 q 持平；εv 在降伏後變成水平線——塑性流動不改變體積。' },
    { n: 'ψ = φ（關聯流動）', m: { ...SOIL, psi: 30 }, t: { test: 'TXC', sv: 100, k0: 1, emax: 5 }, ghost: { m: SOIL }, note: '強度和 ψ = 0（灰）完全一樣，但體積一路膨脹：每 1 % 軸向塑性應變帶來 2 % 的體積膨脹，而且不會停。' },
    { n: '不排水 ψ = 0', m: SOIL, t: { test: 'CU', sv: 100, k0: 1, emax: 5 }, note: '有效應力路徑垂直上升（p′ 幾乎不變），碰到破壞線就停；灰色虛線是總應力路徑，兩者水平距離就是超額孔壓。' },
    { n: '不排水 ψ > 0：強度無上限', m: { ...SOIL, psi: 10 }, t: { test: 'CU', sv: 100, k0: 1, emax: 10 }, ghost: { m: SOIL }, note: '碰到破壞線後沿線一直往上爬，孔壓持續下降。真實的砂會在臨界狀態停下，MC 不會。' },
    { n: '加 cavitation cut-off', m: { ...SOIL, psi: 10 }, t: { test: 'CU', sv: 100, k0: 1, emax: 10, cav: true }, ghost: { m: { ...SOIL, psi: 10 }, t: { cav: false } }, note: '超額孔壓到 −100 kPa 後不再下降，之後等同排水剪動，強度停止上升。PLAXIS 的 Undrained (A) 配 ψ > 0 一定要開。' },
    { n: '壓縮 vs 伸張', m: SOIL, t: { test: 'TXE', sv: 100, k0: 1, emax: 5 }, ghost: { t: { test: 'TXC' } }, note: '伸張的 |q| 只有壓縮的 (3 − sinφ)/(3 + sinφ) = 0.714 倍；π 平面上停在離軸較近的伸張角。' },
    { n: '單剪 DSS', m: SOIL, t: { test: 'DSS', sv: 100, k0: 0.5, emax: 10 }, ghost: { m: { ...SOIL, psi: 30 } }, note: 'τ/σ′v 停在 sinφ cosψ/(1 − sinφ sinψ)：ψ = 0 為 0.5，ψ = φ（灰）為 tanφ = 0.577。p′–q 圖上終點落在壓縮線與伸張線之間。' },
    { n: '不排水循環：孔壓不累積', m: SOIL, t: { test: 'CYC', sv: 100, k0: 1, amp: 0.8, ncyc: 3 }, note: '每一圈都撞到壓縮線與伸張線，但 p′ 始終不變，超額孔壓不會一圈一圈累積——MC 算不出液化。' },
    { n: '岩體 e7：伸張遇張力截斷', m: ROCK, t: { test: 'TXE', sv: 500, k0: 1, emax: 0.05 }, ghost: { m: { ...ROCK, tc: false } }, note: '軸向應力降到 −289 kPa 就停（張力截斷）；灰色是關閉張力截斷的結果，要到 −1.18 MPa 才碰到 MC 伸張角。' },
    { n: '岩體 e7：三軸壓縮 σ′3 = 2 MPa', m: ROCK, t: { test: 'TXC', sv: 2000, k0: 1, emax: 0.3 }, note: 'q_f ＝ (Nφ − 1)σ′3 ＋ 2c√Nφ ＝ 12.35 MPa。岩體 E 大，0.08 % 應變就破壞。' }
  ];
  const inputs = ['t_test', 't_sv', 't_k0', 't_emax', 't_amp', 't_ncyc', 't_nuu', 't_cav', 'm_E', 'm_nu', 'm_c', 'm_phi', 'm_psi', 'm_tc', 'm_st'];
  const S = { res: null, ghost: null, idx: 0, playing: false, note: '' };

  function setVals(m, t) {
    const base = { test: 'TXC', sv: 100, k0: 1, emax: 5, amp: 0.8, ncyc: 3, nuu: 0.495, cav: false };
    t = { ...base, ...t };
    $('t_test').value = t.test; $('t_sv').value = t.sv; $('t_k0').value = t.k0; $('t_emax').value = t.emax;
    $('t_amp').value = t.amp; $('t_ncyc').value = t.ncyc; $('t_nuu').value = t.nuu; $('t_cav').checked = t.cav;
    $('m_E').value = m.E; $('m_nu').value = m.nu; $('m_c').value = m.c; $('m_phi').value = m.phi; $('m_psi').value = m.psi;
    $('m_tc').checked = m.tc; $('m_st').value = m.st;
  }
  function read() {
    const num = (id, d) => { const v = parseFloat($(id).value); return isFinite(v) ? v : d; };
    const phi = num('m_phi', 30); let psi = num('m_psi', 0);
    if (psi > phi) { psi = phi; $('m_psi').value = phi; }
    const P = { E: Math.max(0.01, num('m_E', 20)) * 1000, nu: num('m_nu', 0.3), c: Math.max(0, num('m_c', 0)), phi, psi, tc: $('m_tc').checked, st: Math.max(0, num('m_st', 0)) };
    const test = $('t_test').value;
    const cfg = { test, sv0: Math.max(0.1, num('t_sv', 100)), K0: num('t_k0', 1), emax: Math.max(0.001, num('t_emax', 5)), steps: 400,
      amp: Math.max(0.001, num('t_amp', 0.8)), ncyc: Math.min(20, Math.max(1, Math.round(num('t_ncyc', 3)))), nuu: num('t_nuu', 0.495), cav: $('t_cav').checked, cavs: 100 };
    if (test === 'CYC') cfg.steps = 160 * cfg.ncyc;
    return { P, cfg };
  }
  function syncUI() {
    const t = $('t_test').value, und = ['CU', 'CUE', 'CYC'].includes(t);
    document.querySelectorAll('#lab [data-und]').forEach(e => e.classList.toggle('hidden', !und));
    document.querySelectorAll('#lab [data-cyc]').forEach(e => e.classList.toggle('hidden', t !== 'CYC'));
    document.querySelectorAll('#lab [data-mono]').forEach(e => e.classList.toggle('hidden', t === 'CYC'));
    $('m_st').disabled = !$('m_tc').checked;
    $('o_k0').textContent = (+$('t_k0').value).toFixed(2); $('o_nuu').textContent = (+$('t_nuu').value).toFixed(3);
    $('o_nu').textContent = (+$('m_nu').value).toFixed(2); $('o_phi').textContent = (+$('m_phi').value).toFixed(1) + '°'; $('o_psi').textContent = (+$('m_psi').value).toFixed(1) + '°';
    document.querySelectorAll('#lab input[type=range]').forEach(r => { if (r.id === 'scrub') return; r.style.setProperty('--pct', ((r.value - r.min) / (r.max - r.min) * 100) + '%'); });
  }
  function run(keepIdx) {
    syncUI();
    const { P, cfg } = read();
    S.res = MCLab.run(P, cfg); S.res.P = P;
    const n = S.res.rec.length - 1;
    $('scrub').max = n;
    S.idx = keepIdx ? Math.min(S.idx, n) : n;
    $('scrub').value = S.idx;
    draw();
  }
  const isDSS = r => r.cfg.test === 'DSS' || r.cfg.test === 'DSSU';
  const isUnd = r => ['CU', 'CUE', 'CYC', 'DSSU'].includes(r.cfg.test);
  const xOf = r => r.rec.map(s => (isDSS(r) ? s.g : s.ea) * 100);
  const ssOf = r => r.rec.map(s => isDSS(r) ? s.sig[3] : s.q);
  const volOf = r => r.rec.map(s => isUnd(r) ? s.u : s.ev * 100);

  function stateOf(s, mat) {
    if (!s.act.length) return ['彈性', 'el'];
    if (s.act[0] === -1) return ['錐頂（apex）', 'pl'];
    const nm = s.act.filter(k => mat.fs[k].type === 'mc').length, nt = s.act.length - nm;
    if (nt && !nm) return ['張力截斷', 'tc'];
    if (nt && nm) return ['MC＋張力截斷', 'tc'];
    return [nm === 1 ? 'MC 破壞面' : nm === 2 ? 'MC 角點（兩面）' : 'MC 角點（三面）', 'pl'];
  }

  function draw() {
    const r = S.res, g = S.ghost, i = S.idx, s = r.rec[i], P = r.P;
    const sp = Math.sin(P.phi * D2R), cp = Math.cos(P.phi * D2R);
    const dss = isDSS(r), und = isUnd(r);
    $('pos').textContent = `第 ${i} / ${r.rec.length - 1} 步　${dss ? 'γ' : 'εa'} = ${fmt(xOf(r)[i], 3)} %`;
    const sub = (arr) => arr.slice(0, i + 1);
    // ---------- p′–q ----------
    {
      const ps = r.rec.map(x => x.p), qs = r.rec.map(x => x.q), pts = r.rec.map(x => x.pt);
      const gp = g ? g.res.rec.map(x => x.p) : [], gq = g ? g.res.rec.map(x => x.q) : [];
      const xr = PLT.range([ps, gp, und ? pts : []], 0.1, [0]);
      const yr = PLT.range([qs, gq], 0.12, [0]);
      if (P.tc && P.c > 0) xr[0] = Math.min(xr[0], -P.st - 0.05 * (xr[1] - xr[0]));
      const ch = PLT.chart($('g_pq'), { W: 400, H: 310, xr, yr, xl: 'p′ (kPa)', yl: dss ? 'q = √(3J₂) (kPa)' : 'q = σ′a − σ′r (kPa)' });
      const N = 160, pp = [], qc = [], qe = [], tc1 = [], tc2 = [];
      for (let k = 0; k <= N; k++) {
        const p = ch.x0 + (ch.x1 - ch.x0) * k / N, base = P.c * cp + p * sp;
        pp.push(p);
        qc.push(base >= 0 ? 6 * base / (3 - sp) : NaN); qe.push(base >= 0 ? 6 * base / (3 + sp) * (dss ? 1 : -1) : NaN);
        tc1.push(p + P.st >= 0 ? 3 * (p + P.st) : NaN); tc2.push(p + P.st >= 0 ? -1.5 * (p + P.st) : NaN);
      }
      ch.path(pp, qc, INK); ch.path(pp, qe, dss ? INKD : INK);
      if (P.tc && !dss) { ch.path(pp, tc1, TCL); ch.path(pp, tc2, TCL); }
      if (g) ch.path(gp, gq, GHOST);
      if (und) ch.path(sub(pts), sub(qs), TOT);
      ch.path(ps, qs, 'stroke:var(--blue);stroke-width:2;opacity:.25');
      ch.path(sub(ps), sub(qs), BLUE);
      ch.dot(s.p, s.q, PT);
      const lx = ch.x0 + 0.62 * (ch.x1 - ch.x0), lb = P.c * cp + lx * sp;
      if (lb > 0) {
        const yc = 6 * lb / (3 - sp);
        if (yc > ch.y0 && yc < ch.y1 - 0.06 * (ch.y1 - ch.y0)) ch.text(lx, yc + 0.03 * (ch.y1 - ch.y0), '三軸壓縮', 'fill:var(--ink)', 'end');
        const ye = 6 * lb / (3 + sp) * (dss ? 1 : -1);
        if (ye > ch.y0 && ye < ch.y1) ch.text(lx + 0.2 * (ch.x1 - ch.x0), ye * 1.0 + (dss ? -0.04 : 0.04) * (ch.y1 - ch.y0), '三軸伸張', 'fill:var(--ink)', 'end');
      }
      ch.done();
      $('cap_pq').textContent = und ? '（藍：有效應力；灰虛線：總應力）' : '';
    }
    // ---------- 應力–應變 ----------
    {
      const xs = xOf(r), ys = ssOf(r), gx = g ? xOf(g.res) : [], gy = g ? ssOf(g.res) : [];
      const ch = PLT.chart($('g_ss'), { W: 400, H: 310, xr: PLT.range([xs, gx], 0.04, [0]), yr: PLT.range([ys, gy], 0.1, [0]),
        xl: dss ? 'γ (%)' : 'εa (%)', yl: dss ? 'τxy (kPa)' : 'q (kPa)' });
      if (g) ch.path(gx, gy, GHOST);
      ch.path(xs, ys, 'stroke:var(--blue);stroke-width:2;opacity:.25'); ch.path(sub(xs), sub(ys), BLUE); ch.dot(xs[i], ys[i], PT); ch.done();
      $('cap_ss').textContent = dss ? '應力–應變 τxy–γ' : '應力–應變 q–εa';
    }
    // ---------- 體積或孔壓 ----------
    {
      const xs = xOf(r), ys = volOf(r);
      const gok = g && isUnd(g.res) === und, gx = gok ? xOf(g.res) : [], gy = gok ? volOf(g.res) : [];
      const ch = PLT.chart($('g_vol'), { W: 400, H: 310, xr: PLT.range([xs, gx], 0.04, [0]), yr: PLT.range([ys, gy], 0.12, [0]),
        xl: dss ? 'γ (%)' : 'εa (%)', yl: und ? 'Δu (kPa)' : 'εv (%)，壓縮為正' });
      if (gok) ch.path(gx, gy, GHOST);
      ch.path(xs, ys, 'stroke:var(--blue);stroke-width:2;opacity:.25'); ch.path(sub(xs), sub(ys), BLUE); ch.dot(xs[i], ys[i], PT); ch.done();
      $('cap_vol').textContent = und ? '超額孔隙水壓 Δu' : '體積應變 εv（負值 ＝ 膨脹）';
    }
    drawPi(r, i); drawMohr(r, i);
    // ---------- 讀值 ----------
    const [stxt, scls] = stateOf(s, r.mat);
    const t = (s.prin[0] - s.prin[2]) / 2, c0 = (s.prin[0] + s.prin[2]) / 2, cap = c0 * sp + P.c * cp;
    const cells = [
      ['狀態', `<span class="state ${scls}">${stxt}</span>`],
      ['p′ (kPa)', fmt(s.p, 1)], [dss ? 'q (kPa)' : 'q ＝ σ′a − σ′r (kPa)', fmt(s.q, 1)],
      ['σ′1 ／ σ′3 (kPa)', fmt(s.prin[0], 0) + ' ／ ' + fmt(s.prin[2], 0)],
      ['強度發揮度 t／(s sinφ + c cosφ)', cap > 0 ? fmt(t / cap * 100, 1) + ' %' : '—'],
      [und ? 'Δu (kPa)' : 'εv (%)', und ? fmt(s.u, 1) : fmt(s.ev * 100, 3)],
      ['累積塑性體積應變 εvp (%)', fmt(s.epv * 100, 3)]
    ];
    $('stats').innerHTML = cells.map(([k, v]) => `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`).join('');
    $('note').innerHTML = (S.note ? S.note + ' ' : '') + (und ? `不排水：水的等效體積模數 Kw/n ＝ ${fmt(r.Kwn / 1000, 1)} MPa（νu ${r.cfg.nuu}）。` : '');
  }

  // π 平面：TX 用 (σ′x, σ′y=軸向, σ′z)；DSS 用排序後的主應力
  function drawPi(r, i) {
    const svg = $('g_pi'), W = 400, H = 330, cx = 200, cy = 160, P = r.P;
    const sp = Math.sin(P.phi * D2R), cp = Math.cos(P.phi * D2R), k = Math.sqrt(2 / 3);
    const E = [[0, 1], [-Math.cos(Math.PI / 6), -0.5], [Math.cos(Math.PI / 6), -0.5]];   // 上、左下、右下
    const dss = isDSS(r);
    const trip = s => dss ? s.prin.slice() : [s.sig[1], s.sig[0], s.sig[2]];
    const proj = t => [k * (t[0] * E[0][0] + t[1] * E[1][0] + t[2] * E[2][0]), k * (t[0] * E[0][1] + t[1] * E[1][1] + t[2] * E[2][1])];
    const s = r.rec[i], p = s.p, base = P.c * cp + p * sp;
    const rc = base > 0 ? k * 6 * base / (3 - sp) : 0, re = base > 0 ? k * 6 * base / (3 + sp) : 0;
    let poly = [];
    for (let j = 0; j < 6; j++) {         // 角度 90°（壓縮 a）起，每 60° 交替壓縮／伸張
      const ang = (90 + 60 * j) * D2R, rr = j % 2 === 0 ? rc : re;
      poly.push([rr * Math.cos(ang), rr * Math.sin(ang)]);
    }
    if (P.tc) {                            // σ_i ≥ −σt ⇒ P·e_i ≥ −(σt + p)√(3/2)
      const lim = -(P.st + p) * Math.sqrt(1.5);
      for (const e of E) {
        const inside = q => q[0] * e[0] + q[1] * e[1] >= lim - 1e-9, out = [];
        for (let j = 0; j < poly.length; j++) {
          const A = poly[j], B = poly[(j + 1) % poly.length], ia = inside(A), ib = inside(B);
          if (ia) out.push(A);
          if (ia !== ib) { const da = A[0] * e[0] + A[1] * e[1] - lim, db = B[0] * e[0] + B[1] * e[1] - lim, t = da / (da - db); out.push([A[0] + t * (B[0] - A[0]), A[1] + t * (B[1] - A[1])]); }
        }
        poly = out;
      }
    }
    const path = r.rec.slice(0, i + 1).map(x => proj(trip(x)));
    const gpath = S.ghost ? S.ghost.res.rec.map(x => proj((isDSS(S.ghost.res) ? x.prin.slice() : [x.sig[1], x.sig[0], x.sig[2]]))) : [];
    let R = Math.max(rc, 1e-9);
    path.concat(gpath).forEach(q => { R = Math.max(R, Math.hypot(q[0], q[1])); });
    const sc = 118 / (R * 1.08);
    const X = q => (cx + q[0] * sc).toFixed(1), Y = q => (cy - q[1] * sc).toFixed(1);
    const lab = dss ? ['σ′1', 'σ′2', 'σ′3'] : ['σ′a（y）', 'σ′r（x）', 'σ′r（z）'];
    let h = '';
    E.forEach((e, j) => {
      h += `<line x1="${cx}" y1="${cy}" x2="${(cx + e[0] * 136).toFixed(1)}" y2="${(cy - e[1] * 136).toFixed(1)}" style="stroke:var(--line);stroke-width:1"/>`;
      h += `<line x1="${cx}" y1="${cy}" x2="${(cx - e[0] * 136).toFixed(1)}" y2="${(cy + e[1] * 136).toFixed(1)}" style="stroke:var(--line);stroke-width:1;stroke-dasharray:3 4"/>`;
      h += `<text x="${(cx + e[0] * 150).toFixed(1)}" y="${(cy - e[1] * 150 + 4).toFixed(1)}" text-anchor="middle" style="font-size:12.5px;fill:var(--muted)">${lab[j]}</text>`;
    });
    if (poly.length) h += `<polygon points="${poly.map(q => X(q) + ',' + Y(q)).join(' ')}" style="fill:var(--accent-soft);stroke:var(--ink);stroke-width:1.4"/>`;
    if (gpath.length) h += `<polyline points="${gpath.map(q => X(q) + ',' + Y(q)).join(' ')}" style="fill:none;stroke:var(--gray);stroke-width:1.5"/>`;
    h += `<polyline points="${path.map(q => X(q) + ',' + Y(q)).join(' ')}" style="fill:none;stroke:var(--blue);stroke-width:2"/>`;
    const q = path[path.length - 1];
    h += `<circle cx="${X(q)}" cy="${Y(q)}" r="5" style="fill:var(--red);stroke:var(--bg);stroke-width:1.5"/>`;
    h += `<text x="8" y="${H - 26}" style="font-size:11.5px;fill:var(--muted)">六角形：p′ ＝ ${fmt(p, 0)} kPa 的 MC 截面${P.tc ? '（已扣張力截斷）' : ''}</text>`;
    h += `<text x="8" y="${H - 9}" style="font-size:11.5px;fill:var(--muted)">實線軸：壓縮角方向；虛線軸：伸張角方向</text>`;
    svg.innerHTML = h;
  }

  function drawMohr(r, i) {
    const s = r.rec[i], P = r.P, [s1, s2, s3] = s.prin;
    const tn = Math.tan(P.phi * D2R), apex = tn > 1e-9 ? -P.c / tn : -Infinity;
    let lo = Math.min(s3, 0), hi = Math.max(s1, 1);
    if (P.tc) lo = Math.min(lo, -P.st); else if (isFinite(apex)) lo = Math.min(lo, Math.max(apex, -0.6 * (hi - lo)));
    const span = hi - lo; lo -= 0.06 * span; hi += 0.06 * span;
    const tt = (s1 - s3) / 2, env3 = P.c + Math.max(s3, isFinite(apex) ? apex : s3) * tn;
    const ytop = Math.max(1.3 * tt, Math.min(1.15 * env3, 6 * tt + 1)) + 1e-6;
    const ch = PLT.chart($('g_mohr'), { W: 640, H: 330, xr: [lo, hi], yr: [0, ytop], xl: 'σn (kPa)', yl: 'τ (kPa)', equal: true });
    const xa = Math.max(isFinite(apex) ? apex : ch.x0, P.tc ? -P.st : -Infinity, ch.x0);
    ch.path([xa, ch.x1], [P.c + xa * tn, P.c + ch.x1 * tn], 'stroke:var(--ink);stroke-width:1.6');
    if (P.tc) ch.path([-P.st, -P.st], [0, Math.max(0, P.c - P.st * tn)], 'stroke:var(--red);stroke-width:1.6;stroke-dasharray:5 4');
    const circ = (a, b, st) => { const c = (a + b) / 2, rr = Math.abs(a - b) / 2, xs = [], ys = []; for (let k = 0; k <= 90; k++) { const t = Math.PI * k / 90; xs.push(c + rr * Math.cos(t)); ys.push(rr * Math.sin(t)); } ch.path(xs, ys, st); };
    circ(s1, s2, 'stroke:var(--gray);stroke-width:1.2'); circ(s2, s3, 'stroke:var(--gray);stroke-width:1.2');
    circ(s1, s3, BLUE);
    [s1, s2, s3].forEach(v => ch.dot(v, 0, 'fill:var(--blue)', 3.5));
    ch.text(ch.x1 - 0.01 * (ch.x1 - ch.x0), P.c + ch.x1 * tn - 0.0 * (ch.y1 - ch.y0), 'τ ＝ c + σn tanφ', 'fill:var(--ink)', 'end');
    ch.done();
  }

  // ---------- 事件 ----------
  const box = $('presets');
  PRE.forEach((pr, j) => {
    const b = document.createElement('button'); b.className = 'btn'; b.type = 'button'; b.textContent = pr.n;
    b.addEventListener('click', () => {
      box.querySelectorAll('.btn').forEach(x => x.classList.remove('on')); b.classList.add('on');
      stop();
      if (pr.ghost) {
        const gm = { ...pr.m, ...(pr.ghost.m || {}) }, gt = { ...pr.t, ...(pr.ghost.t || {}) };
        setVals(gm, gt); run(); S.ghost = { res: S.res, label: describe() };
      } else S.ghost = null;
      setVals(pr.m, pr.t); S.note = pr.note; run();
      $('ghostlbl').textContent = S.ghost ? '對照：' + S.ghost.label : '';
    });
    box.appendChild(b);
  });
  function describe() { const { P, cfg } = read(); return `${TESTS[cfg.test]}，φ ${P.phi}°、ψ ${P.psi}°、c ${P.c}${P.tc ? '、σt ' + P.st : '、無張力截斷'}${cfg.cav ? '、cavitation' : ''}`; }
  inputs.forEach(id => $(id).addEventListener('input', () => { S.note = ''; box.querySelectorAll('.btn').forEach(x => x.classList.remove('on')); run(true); }));
  $('scrub').addEventListener('input', () => { S.idx = +$('scrub').value; draw(); });
  $('b_ghost').addEventListener('click', () => { S.ghost = { res: S.res, label: describe() }; $('ghostlbl').textContent = '對照：' + S.ghost.label; draw(); });
  $('b_clear').addEventListener('click', () => { S.ghost = null; $('ghostlbl').textContent = ''; draw(); });
  let raf = 0;
  function stop() { S.playing = false; cancelAnimationFrame(raf); $('b_play').textContent = '▶ 播放'; }
  $('b_play').addEventListener('click', () => {
    if (S.playing) return stop();
    const n = S.res.rec.length - 1;
    if (S.idx >= n) S.idx = 0;
    S.playing = true; $('b_play').textContent = '❚❚ 暫停';
    const per = Math.max(1, Math.round(n / 240));
    const tick = () => { S.idx = Math.min(n, S.idx + per); $('scrub').value = S.idx; draw(); if (S.idx >= n) return stop(); raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick);
  });
  box.querySelector('.btn').click();
})();

/* ================= 5.7 Mohr 圓試算 ================= */
(() => {
  const P = { c: 1351, phi: 38.8, st: 289, s3: 2000, s1: 9000 };
  const fmt = (x, d = 0) => !isFinite(x) ? '—' : (Math.abs(x) < 0.5 * Math.pow(10, -d) ? 0 : x).toLocaleString('zh-TW', { maximumFractionDigits: d, minimumFractionDigits: d });
  const D2R = Math.PI / 180;
  function draw() {
    const c = Math.max(0, P.c), phi = Math.min(Math.max(P.phi, 0), 89) * D2R, st = Math.max(0, P.st);
    const s1 = Math.max(P.s1, P.s3), s3 = Math.min(P.s1, P.s3);
    const sn = Math.sin(phi), cs = Math.cos(phi), tn = Math.tan(phi), N = (1 + sn) / (1 - sn);
    const s = (s1 + s3) / 2, t = (s1 - s3) / 2, f = t - s * sn - c * cs, cap = s * sn + c * cs;
    const s1f = N * s3 + 2 * c * Math.sqrt(N), apex = phi > 1e-6 ? -c / tn : -Infinity;
    const state = s3 < -st - 1e-9 ? 'tc' : (f >= -1e-9 ? 'pl' : 'el');
    let lo = Math.min(s3, -st, 0), hi = Math.max(s1, s1f, 1);
    const span = hi - lo; lo -= 0.06 * span; hi += 0.05 * span;
    const ch = PLT.chart(document.getElementById('mohr'), { W: 640, H: 330, xr: [lo, hi], yr: [0, Math.max(t, (s1f - s3) / 2, c, 1) * 1.25], xl: 'σn (kPa，壓為正)', yl: 'τ (kPa)', equal: true });
    ch.raw(`<rect x="${ch.X(ch.x0)}" y="${ch.Y(ch.y1)}" width="${Math.max(0, ch.X(-st) - ch.X(ch.x0))}" height="${ch.Y(0) - ch.Y(ch.y1)}" style="fill:var(--pband);opacity:.45"/>`);
    const xa = Math.max(isFinite(apex) ? apex : ch.x0, -st);
    ch.path([xa, ch.x1], [c + xa * tn, c + ch.x1 * tn], 'stroke:var(--ink);stroke-width:1.8');
    if (isFinite(apex) && apex < -st) ch.path([Math.max(apex, ch.x0), -st], [c + Math.max(apex, ch.x0) * tn, c - st * tn], 'stroke:var(--ink);stroke-width:1.1;stroke-dasharray:4 3');
    ch.path([-st, -st], [0, Math.max(0, c - st * tn)], 'stroke:var(--red);stroke-width:1.8');
    const circ = (a, b, st2) => { const cc = (a + b) / 2, rr = Math.abs(a - b) / 2, xs = [], ys = []; for (let k = 0; k <= 120; k++) { const th = Math.PI * k / 120; xs.push(cc + rr * Math.cos(th)); ys.push(rr * Math.sin(th)); } ch.path(xs, ys, st2); };
    circ(s3, s1f, 'stroke:var(--gray);stroke-width:1.3;stroke-dasharray:5 4');
    const col = state === 'el' ? 'var(--blue)' : state === 'pl' ? 'var(--red)' : 'var(--orange)';
    circ(s3, s1, `stroke:${col};stroke-width:2.2`);
    ch.dot(s3, 0, `fill:${col}`, 3.5); ch.dot(s1, 0, `fill:${col}`, 3.5);
    ch.text(-st, (ch.y1 - ch.y0) * 0.04, '−σt', 'fill:var(--red)', 'end');
    ch.text(ch.x1 - 0.02 * (ch.x1 - ch.x0), ch.y1 - 0.07 * (ch.y1 - ch.y0), '灰虛線：同一 σ′3 下的破壞圓', 'fill:var(--muted)', 'end');
    ch.done();
    const el = document.getElementById('mstate');
    el.className = 'state ' + state;
    el.textContent = state === 'tc' ? '受拉超過 σt：觸發 tension cut-off' : state === 'pl' ? '達到或超出降伏面：f ≥ 0，PLAXIS 會回傳到面上' : '彈性：f < 0';
    const Mc = 6 * sn / (3 - sn), Me = 6 * sn / (3 + sn);
    const rows = [
      ['f ＝ t − s·sinφ − c·cosφ', fmt(f) + ' kPa'],
      ['強度發揮度 t／(s·sinφ + c·cosφ)', cap > 0 ? fmt(t / cap * 100, 1) + ' %' : '—'],
      ['Nφ ＝ (1 + sinφ)／(1 − sinφ)', fmt(N, 3)],
      ['同一 σ′3 下的破壞 σ′1f ＝ Nφσ′3 + 2c√Nφ', fmt(s1f) + ' kPa'],
      ['單軸抗壓強度 2c√Nφ', fmt(2 * c * Math.sqrt(N)) + ' kPa'],
      ['MC 隱含的單軸抗拉強度 2c·cosφ／(1 + sinφ)', fmt(2 * c * cs / (1 + sn)) + ' kPa'],
      ['錐頂 −c·cotφ', isFinite(apex) ? fmt(apex) + ' kPa' : '—'],
      ['Mc ／ Me ／ re/rc', fmt(Mc, 3) + ' ／ ' + fmt(Me, 3) + ' ／ ' + fmt((3 - sn) / (3 + sn), 3)]
    ];
    document.getElementById('readout').innerHTML = rows.map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td></tr>`).join('');
  }
  ['c', 'phi', 'st', 's3', 's1'].forEach(k => {
    const r = document.getElementById('r_' + k), n = document.getElementById('n_' + k);
    const pct = () => r.style.setProperty('--pct', ((r.value - r.min) / (r.max - r.min) * 100) + '%');
    r.value = P[k]; n.value = P[k]; pct();
    r.addEventListener('input', () => { P[k] = parseFloat(r.value); n.value = r.value; pct(); draw(); });
    n.addEventListener('input', () => { const v = parseFloat(n.value); if (isFinite(v)) { P[k] = v; r.value = v; pct(); draw(); } });
  });
  draw();
})();

/* ================= 5.11 分頁 ================= */
document.querySelectorAll('#wtabs button').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('#wtabs button').forEach(x => x.classList.toggle('on', x === b));
  document.querySelectorAll('#s11 .tabpane').forEach(p => p.classList.toggle('on', p.id === b.dataset.t));
}));
