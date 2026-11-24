const M = require('./mc_model.js');
const D = Math.PI / 180;
const base = { E: 20000, nu: 0.3, c: 10, phi: 30, psi: 0, tc: true, st: 0 };
const cfg = { test: 'TXC', sv0: 100, K0: 1, steps: 300, emax: 5, nuu: 0.495, cav: false, cavs: 100, amp: 1, ncyc: 3 };
function last(r) { return r.rec[r.rec.length - 1]; }
function pr(name, v, ref) { console.log(name.padEnd(46), v.toFixed(4), ref !== undefined ? ' ref ' + ref.toFixed(4) + '  err ' + ((v - ref) / ref * 100).toFixed(3) + '%' : ''); }

for (const [phi, psi, c, s3] of [[30, 0, 10, 100], [38.8, 0, 1351, 2000], [35, 35, 0, 200]]) {
  const P = { ...base, phi, psi, c };
  const r = M.run(P, { ...cfg, test: 'TXC', sv0: s3 });
  const L = last(r), sp = Math.sin(phi * D), N = (1 + sp) / (1 - sp);
  pr(`TXC φ${phi} ψ${psi} c${c} σ3 ${s3}: q_f`, L.q, (N - 1) * s3 + 2 * c * Math.sqrt(N));
  pr('   q_f via 6(c cosφ+p sinφ)/(3−sinφ)', L.q, 6 * (c * Math.cos(phi * D) + L.p * sp) / (3 - sp));
  // plastic dilatancy ratio over last 50 steps
  const A = r.rec[r.rec.length - 51];
  const dev = L.epv - A.epv, dgam = (L.ea - A.ea) - (L.sig[0] - A.sig[0]) * 0 - ((L.ev - L.ea) / 2 - (A.ev - A.ea) / 2);
  pr('   dεv/dγ (total, at failure) vs −sinψ', (L.ev - A.ev) / dgam, -Math.sin(psi * D) || -1e-30);
}
{ // TXE
  const P = { ...base, phi: 30, c: 0 };
  const r = M.run(P, { ...cfg, test: 'TXE', sv0: 100 });
  const L = last(r);
  pr('TXE φ30 c0 σr100: |q_f| (σa=σr/Nφ)', -L.q, 100 - 100 / 3);
  pr('   q/(p) vs Me', -L.q / L.p, 6 * 0.5 / 3.5);
}
{ // CU ψ0
  const P = { ...base, phi: 30, c: 0 };
  const r = M.run(P, { ...cfg, test: 'CU', sv0: 100 });
  const L = last(r);
  pr('CU ψ0: p′ at end', L.p, 100); pr('   q_f', L.q, 1.2 * 100); pr('   Δu', L.u, 100 + L.q / 3 - L.p);
  const r2 = M.run({ ...P, psi: 10 }, { ...cfg, test: 'CU', sv0: 100 });
  console.log('CU ψ10: q at 1%,2.5%,5%', [100, 150, 300].map(i => r2.rec[i * 1].q.toFixed(1)).join(' '), ' u', last(r2).u.toFixed(1));
  const r3 = M.run({ ...P, psi: 10 }, { ...cfg, test: 'CU', sv0: 100, cav: true, cavs: 100 });
  console.log('CU ψ10 cav: q end', last(r3).q.toFixed(1), ' u', last(r3).u.toFixed(1));
}
for (const psi of [0, 15, 30]) { // DSS drained
  const P = { ...base, phi: 30, psi, c: 0 };
  const r = M.run(P, { ...cfg, test: 'DSS', sv0: 100, K0: 0.5, emax: 20, steps: 600 });
  const L = last(r), sp = 0.5, sps = Math.sin(psi * D);
  pr(`DSS ψ${psi}: τ/σv`, L.sig[3] / L.sig[1], sp * Math.cos(psi * D) / (1 - sp * sps));
}
{ // tension cut-off: rock, extension
  const P = { E: 15e6, nu: 0.24, c: 1351, phi: 38.8, psi: 0, tc: true, st: 289 };
  const r = M.run(P, { ...cfg, test: 'TXE', sv0: 500, emax: 0.05 });
  const L = last(r);
  console.log('TXE rock σr500: σa end', L.sig[1].toFixed(2), 'act', L.act, ' (expect −289)');
  const r2 = M.run({ ...P, tc: false }, { ...cfg, test: 'TXE', sv0: 500, emax: 0.05 });
  const sp = Math.sin(38.8 * D), N = (1 + sp) / (1 - sp);
  pr('  TC off σa end vs (σ1−2c√N)/N', last(r2).sig[1], (500 - 2 * 1351 * Math.sqrt(N)) / N);
}
{ // cyclic
  const P = { ...base, phi: 30, c: 0 };
  const r = M.run(P, { ...cfg, test: 'CYC', sv0: 100, amp: 1, ncyc: 3, steps: 600 });
  console.log('CYC: p′ range', Math.min(...r.rec.map(x => x.p)).toFixed(2), Math.max(...r.rec.map(x => x.p)).toFixed(2), ' q range', Math.min(...r.rec.map(x => x.q)).toFixed(1), Math.max(...r.rec.map(x => x.q)).toFixed(1));
}
{ // timing
  const t = Date.now();
  M.run({ ...base, phi: 30, psi: 10, c: 5 }, { ...cfg, test: 'DSS', steps: 1000, emax: 10 });
  console.log('DSS 1000 steps ms', Date.now() - t);
}
