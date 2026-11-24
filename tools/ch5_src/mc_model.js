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
if (typeof module !== 'undefined') module.exports = MCLab;
