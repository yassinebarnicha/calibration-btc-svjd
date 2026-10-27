/* Tests of sources/replication.js (static replication with listed options).

     node tests/test_replication.js
   Exit code 1 if any check fails. No dependency besides Node. */
"use strict";
const path = require("path");
const R = require(path.join(__dirname, "..", "sources", "replication.js"));
const P = require(path.join(__dirname, "..", "sources", "pricer.js"));

let echecs = 0, total = 0;
function verifier(nom, ok, detail) {
  total++;
  if (!ok) echecs++;
  console.log((ok ? "ok      " : "FAILED  ") + nom + (detail ? "  (" + detail + ")" : ""));
}
const proche = (a, b, tol) => Math.abs(a - b) <= tol;
const tousProches = (a, b, tol) => a.length === b.length && a.every((x, i) => proche(x, b[i], tol));

// ---- 1. quadrature widths: same rule and numbers as TooManyOptions' test suite ----
verifier("quadrature widths [2, 5, 11, 20] -> [3, 4.5, 7.5, 9]",
         tousProches(R.largeursQuadrature([2, 5, 11, 20]), [3, 4.5, 7.5, 9], 1e-12));

// ---- 2. TooManyOptions' market test, with open interest in place of volume ----
{
  const S0 = 10, f = s => (s - 10) ** 2;
  const liste = [[1, 0, 5], [2, 0, 12], [5, 0, 3], [9, 0, 40], [11, 1, 10], [13, 1, 2], [15, 1, 25], [18, 1, 1],
                 [9, 1, 50], [11, 0, 50]]                         // last two are in the money: never used
    .map(([K, c, oi]) => ({ K, c: !!c, oi, mark: 1, bid: 1, ask: 1 }));
  const sel = R.selectionner(liste, S0, { oiMin: 10 });
  const port = R.poids(f, S0, sel.puts.map(o => o.K), sel.calls.map(o => o.K), "gamma");
  verifier("filter: puts [2, 9], calls [11, 15]",
           tousProches(sel.puts.map(o => o.K), [2, 9], 0) && tousProches(sel.calls.map(o => o.K), [11, 15], 0));
  verifier("gamma weights: puts [14, 9], calls [6, 8] (as in TooManyOptions)",
           tousProches(port.puts.map(o => o.w), [14, 9], 1e-4) && tousProches(port.calls.map(o => o.w), [6, 8], 1e-4),
           JSON.stringify([port.puts.map(o => +o.w.toFixed(6)), port.calls.map(o => +o.w.toFixed(6))]));
}

// ---- 3. interpolation method: exact at every strike, for smooth and kinked payoffs ----
{
  const F = 100000;
  const putsK = [40000, 55000, 70000, 80000, 90000, 95000, 98000];
  const callsK = [102000, 105000, 110000, 120000, 140000, 170000];
  const K = putsK.concat(callsK);
  const cas = {
    "quadratic (S - F)^2 / F": s => (s - F) ** 2 / F,
    "log contract": s => (s - F) / F - Math.log(s / F),
    "straddle at 110 000 (a listed strike)": s => Math.abs(s - 110000),
    "call spread 105 000 / 140 000": s => Math.max(s - 105000, 0) - Math.max(s - 140000, 0),
  };
  for (const [nom, f] of Object.entries(cas)) {
    const port = R.poids(f, F, putsK, callsK, "interp");
    const err = Math.max(...K.map(k => Math.abs(R.valeurEcheance(port, F, k) - f(k)) / Math.max(1, Math.abs(f(k)))));
    verifier("interp exact at the strikes: " + nom, err < 1e-9, "max relative error " + err.toExponential(2));
  }
  // payoffs that are linear between strikes are replicated exactly everywhere in [Kmin, Kmax]
  for (const nom of ["straddle at 110 000 (a listed strike)", "call spread 105 000 / 140 000"]) {
    const f = cas[nom], port = R.poids(f, F, putsK, callsK, "interp");
    const S = Array.from({ length: 2001 }, (_, i) => 40000 + 130000 * i / 2000);
    const err = Math.max(...S.map(s => Math.abs(R.valeurEcheance(port, F, s) - f(s))));
    verifier("interp exact on the whole strike range: " + nom, err < 1e-6, "max error " + err.toExponential(2) + " $");
  }
  // a call payoff at a listed strike: one call of weight 1, nothing else
  const port = R.poids(s => Math.max(s - 120000, 0), F, putsK, callsK, "interp");
  const actifs = port.puts.concat(port.calls).filter(o => Math.abs(o.w) > 1e-9);
  verifier("call payoff -> exactly one call at 120 000 with weight 1",
           actifs.length === 1 && actifs[0].K === 120000 && proche(actifs[0].w, 1, 1e-9)
           && proche(port.cash, 0, 1e-6) && proche(port.futures, 0, 1e-12));
  // a linear payoff needs no option: cash f(F) and f'(F) futures
  const lin = R.poids(s => 2 * s + 5, F, putsK, callsK, "interp");
  verifier("linear payoff -> no option, cash f(F), futures f'(F)",
           lin.puts.concat(lin.calls).every(o => Math.abs(o.w) < 1e-9) && proche(lin.cash, 2 * F + 5, 1e-6)
           && proche(lin.futures, 2, 1e-9));
}

// ---- 4. pricing: model-free variance from Black-76 prices returns the flat volatility ----
{
  const F = 100000, T = 60 / 365, r = 0.05, sig = 0.6, actu = Math.exp(-r * T);
  const f = s => (2 / T) * ((s - F) / F - Math.log(s / F));            // log-contract payoff: E[f] = variance
  const prix = (K, c) => P.b76(F, K, T, r, sig, c);
  for (const methode of ["interp", "gamma"]) {
    const g = R.grilleDense(F, 6 * sig * Math.sqrt(T), 600);
    const port = R.poids(f, F, g.puts, g.calls, methode);
    const variance = R.valeurAujourdhui(port, actu, prix) / actu;
    verifier("variance swap under flat Black-76 vol 60 %, dense strikes (" + methode + ")",
             proche(Math.sqrt(variance), sig, 0.002), "implied vol " + (100 * Math.sqrt(variance)).toFixed(3) + " %");
  }
  // a call replicated with the interpolation method costs exactly the call
  const putsK = [80000, 90000, 95000], callsK = [105000, 110000, 120000];
  const port = R.poids(s => Math.max(s - 110000, 0), F, putsK, callsK, "interp");
  verifier("call 110 000 replicated: cost = Black-76 price of that call",
           proche(R.valeurAujourdhui(port, actu, prix), prix(110000, true), 1e-6));
  // executable cost: buys at the ask, sales at the bid, mark when a side is missing
  const cote = (K, c) => ({ bid: K === 105000 ? 0 : prix(K, c) * 0.98, ask: prix(K, c) * 1.02, mark: prix(K, c) });
  const spread = R.poids(s => Math.max(s - 105000, 0) - Math.max(s - 120000, 0), F, putsK, callsK, "interp");
  const ex = R.coutExecutable(spread, actu, cote);
  const attendu = 1.02 * prix(105000, true) - 0.98 * prix(120000, true);
  verifier("executable cost of a call spread = ask(long) - bid(short)", proche(ex.valeur, attendu, 1e-6) && ex.manquants === 0,
           ex.valeur.toFixed(4) + " vs " + attendu.toFixed(4));
  // a kink exactly at the highest strike: the payoff must stay flat beyond it (one-sided slope outside the range)
  const S = [125000, 150000, 200000];
  verifier("kink at the highest strike: flat beyond it",
           S.every(s => proche(R.valeurEcheance(spread, F, s), 15000, 1e-6)),
           S.map(s => R.valeurEcheance(spread, F, s).toFixed(2)).join(", "));
}

// ---- 5. the catalogue of payoffs ----
{
  const F = 100000, T = 45 / 365, r = 0.04, sig = 0.55, actu = Math.exp(-r * T);
  const p = { F, K: 95000, K2: 120000, T, a: 2 };
  const putsK = [40000, 55000, 70000, 80000, 90000, 95000, 98000];
  const callsK = [102000, 105000, 110000, 120000, 140000, 170000];
  const K = putsK.concat(callsK);
  const ids = R.CATALOGUE.map(c => c.id);
  verifier("catalogue: " + ids.length + " payoffs, unique ids, each with a group, a name and f",
           new Set(ids).size === ids.length && R.CATALOGUE.every(c => c.groupe && c.nom && typeof c.f === "function"
             && Array.isArray(c.params) && c.params.every(q => ["K", "K2", "a"].includes(q))));
  const fini = R.CATALOGUE.filter(c => ![0.2, 0.5, 0.9, 1, 1.1, 2, 4].every(m => isFinite(c.f(m * F, { ...p, a: c.a !== undefined ? c.a : 1 }))));
  verifier("catalogue: every payoff finite from 0.2 F to 4 F", !fini.length, fini.map(c => c.id).join(", "));
  let pire = 0, quel = "";
  for (const c of R.CATALOGUE) {
    const q = { ...p, a: c.a !== undefined ? c.a : 1 }, f = s => c.f(s, q);
    const port = R.poids(f, F, putsK, callsK, "interp");
    const e = Math.max(...K.map(k => Math.abs(R.valeurEcheance(port, F, k) - f(k)) / Math.max(1, Math.abs(f(k)))));
    if (e > pire) { pire = e; quel = c.id; }
  }
  verifier("catalogue: interpolation weights exact at every listed strike, for every payoff", pire < 1e-9,
           "worst " + pire.toExponential(2) + (quel ? " (" + quel + ")" : ""));
  // payoffs made of listed options: replicated by those options, whatever the method of pricing
  const prix = (k, c) => P.b76(F, k, T, r, sig, c);
  const C = k => prix(k, true), Pu = k => prix(k, false);
  const attendus = {
    call: C(95000), put: Pu(95000), spread: C(95000) - C(120000), putspread: Pu(120000) - Pu(95000),
    straddle: C(95000) + Pu(95000), strangle: Pu(95000) + C(120000), riskrev: C(120000) - Pu(95000),
    collar: actu * F + Pu(95000) - C(120000), covered: actu * F - C(120000),
  };
  const ecarts = Object.entries(attendus).map(([id, v]) => {
    const c = R.parId(id), q = { ...p, a: 1 };
    const port = R.poids(s => c.f(s, q), F, putsK, callsK, "interp");
    return [id, Math.abs(R.valeurAujourdhui(port, actu, prix) - v)];
  });
  verifier("catalogue: calls, puts, spreads, straddle, strangle, risk reversal, collar, covered call cost exactly their options",
           ecarts.every(([, e]) => e < 1e-6), ecarts.filter(([, e]) => e >= 1e-6).map(([i, e]) => i + " " + e.toExponential(2)).join(", "));
  // corridor variance: closed form = log contract when the corridor is the whole line; f'' = 2 / (T k^2) inside
  const logc = s => (s - F) / F - Math.log(s / F);
  verifier("corridor [1, 1e12] = log contract",
           [0.3, 0.8, 1, 1.25, 3].every(m => proche(R.corridor(m * F, F, 1, 1e12), logc(m * F), 1e-9)));
  const cor = R.parId("corridor"), fc = s => cor.f(s, p);
  verifier("corridor: f'' = 2 / (T K^2) inside [K, K2], 0 outside, f(F) = 0",
           proche(R.derivee2(fc, 105000) * T * 105000 ** 2 / 2, 1, 1e-4) && proche(R.derivee2(fc, 60000), 0, 1e-12)
           && proche(R.derivee2(fc, 150000), 0, 1e-12) && proche(fc(F), 0, 1e-12));
  // under flat Black-76, gamma swap and wide-corridor variance both price at sigma^2
  const g = R.grilleDense(F, 6 * sig * Math.sqrt(T), 600);
  for (const [id, q] of [["gammaswap", p], ["corridor", { ...p, K: F * Math.exp(-6 * sig * Math.sqrt(T)), K2: F * Math.exp(6 * sig * Math.sqrt(T)) }]]) {
    const c = R.parId(id), port = R.poids(s => c.f(s, q), F, g.puts, g.calls, "interp");
    const vol = Math.sqrt(R.valeurAujourdhui(port, actu, prix) / actu);
    verifier(id + " under flat Black-76 vol 55 % prices at sigma^2", proche(vol, sig, 0.002), "implied vol " + (100 * vol).toFixed(3) + " %");
  }
  // a narrower corridor is cheaper (less variance accrues inside it)
  const etroit = R.poids(fc, F, g.puts, g.calls, "interp");
  verifier("corridor [95 000, 120 000] is worth less than the full variance swap",
           R.valeurAujourdhui(etroit, actu, prix) / actu < sig * sig);
  // the page must hold a rendered formula for every payoff of the catalogue
  const page = require("fs").readFileSync(path.join(__dirname, "..", "sources", "template_full.html"), "utf8");
  const bloc = (/const TEX_PAY = \{([\s\S]*?)\n    \};/.exec(page) || [, ""])[1];
  const manque = ids.filter(id => !new RegExp("\\b" + id + ": tex\\(").test(bloc));
  verifier("template: a formula (tex) for every payoff of the catalogue", !manque.length, manque.join(", "));
}

// ---- 6. payoff expressions ----
{
  const ev = (txt, vars, x) => R.compiler(txt, vars)(x);
  verifier("parser: precedence 2 + 3 * 4 ^ 2 = 50", ev("2 + 3 * 4 ^ 2", ["S"], [0]) === 50);
  verifier("parser: -S^2 = -(S^2)", ev("-S^2", ["S"], [3]) === -9);
  verifier("parser: 2^3^2 = 512 (right-associative)", ev("2^3^2", ["S"], [0]) === 512);
  verifier("parser: max(S - K, 0) with S = 120, K = 100", ev("max(S - K, 0)", ["S", "K"], [120, 100]) === 20);
  verifier("parser: (S - F) / F - log(S / F) at S = F is 0", ev("(S - F) / F - log(S / F)", ["S", "F"], [5, 5]) === 0);
  verifier("parser: 1.5e3 * abs(S) / 2", ev("1.5e3 * abs(S) / 2", ["S"], [-2]) === 1500);
  for (const [txt, msg] of [["S +", "end"], ["foo(S)", "unknown function"], ["Z * 2", "unknown name"],
                            ["max(S)", "takes 2"], ["(S", "')'"], ["S S", "unexpected"]]) {
    let m = "";
    try { R.compiler(txt, ["S"]); } catch (e) { m = e.message; }
    verifier("parser rejects '" + txt + "'", m.includes(msg), m || "no error");
  }
}

console.log((echecs ? echecs + " FAILED" : "all passed") + " (" + total + " checks)");
process.exit(echecs ? 1 : 0);
