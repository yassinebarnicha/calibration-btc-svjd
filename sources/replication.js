/* Static replication of a payoff f(S_T) with listed BTC options (Carr & Madan 1998).

   Expansion around the future F of the maturity (Deribit options are European, settled on the index, which
   meets the future at expiry):
     f(S) = f(F) + f'(F) (S - F) + sum over puts K < F of w_K (K - S)+ + sum over calls K > F of w_K (S - K)+
   The f'(F) futures cost nothing; today's value of the portfolio is  exp(-rT) f(F) + sum_K w_K P_K.

   Two ways to get the weights on the listed strikes:
     'gamma'   w_K = f''(K) dK, dK = quadrature widths on all the selected strikes (midpoints inside, full
               intervals at the ends) -- the method of TooManyOptions (Serranegra), reproduced exactly;
     'interp'  w_K = change of slope of f at K between neighbouring strikes: the portfolio is the piecewise-linear
               interpolation of f through the strikes, EXACT at every strike, also for payoffs with kinks
               (where f'' is a Dirac mass); outside the strike range it continues with the tangent of f.
   Pure functions, no DOM: tested under Node (tests/test_replication.js) and inlined in the page by build.py. */
(function (root) {
  "use strict";

  // ---------------- payoff expressions (no eval: a small recursive-descent parser) ----------------
  const FONCTIONS = {
    max: [2, Math.max], min: [2, Math.min], abs: [1, Math.abs], exp: [1, Math.exp], sqrt: [1, Math.sqrt],
    log: [1, Math.log], ln: [1, Math.log], pow: [2, Math.pow], sign: [1, Math.sign],
  };
  const CONSTANTES = { pi: Math.PI, e: Math.E };

  function compiler(texte, variables) {
    const vars = variables || ["S"];
    const src = String(texte);
    let i = 0;
    const erreur = msg => { throw new Error(msg + " (position " + (i + 1) + ")"); };
    const blancs = () => { while (i < src.length && /\s/.test(src[i])) i++; };
    const voir = () => { blancs(); return src[i]; };
    function primaire() {
      const c = voir();
      if (c === "(") { i++; const e = expr(); if (voir() !== ")") erreur("')' expected"); i++; return e; }
      if (c === "-") { i++; const e = puissance(); return x => -e(x); }
      if (c === "+") { i++; return puissance(); }
      const nb = /^(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?/.exec(src.slice(i));
      if (nb) { i += nb[0].length; const v = parseFloat(nb[0]); return () => v; }
      const id = /^[A-Za-z_]\w*/.exec(src.slice(i));
      if (id) {
        i += id[0].length;
        const nom = id[0];
        if (voir() === "(") {
          const f = FONCTIONS[nom.toLowerCase()];
          if (!f) erreur("unknown function " + nom);
          i++;
          const args = [expr()];
          while (voir() === ",") { i++; args.push(expr()); }
          if (voir() !== ")") erreur("')' expected");
          i++;
          if (args.length !== f[0]) erreur(nom + " takes " + f[0] + " argument" + (f[0] > 1 ? "s" : ""));
          return x => f[1](...args.map(a => a(x)));
        }
        const k = vars.indexOf(nom);
        if (k >= 0) return x => x[k];
        if (nom.toLowerCase() in CONSTANTES) { const v = CONSTANTES[nom.toLowerCase()]; return () => v; }
        erreur("unknown name " + nom + " (allowed: " + vars.join(", ") + ")");
      }
      erreur(c === undefined ? "unexpected end" : "unexpected '" + c + "'");
    }
    function puissance() {
      const b = primaire();
      if (voir() === "^") { i++; const e = puissance(); return x => Math.pow(b(x), e(x)); }   // right-associative
      return b;
    }
    function terme() {
      let g = puissance();
      for (;;) {
        const c = voir();
        if (c === "*") { i++; const a = g, d = puissance(); g = x => a(x) * d(x); }
        else if (c === "/") { i++; const a = g, d = puissance(); g = x => a(x) / d(x); }
        else return g;
      }
    }
    function expr() {
      let g = terme();
      for (;;) {
        const c = voir();
        if (c === "+") { i++; const a = g, d = terme(); g = x => a(x) + d(x); }
        else if (c === "-") { i++; const a = g, d = terme(); g = x => a(x) - d(x); }
        else return g;
      }
    }
    const f = expr();
    if (voir() !== undefined) erreur("unexpected '" + voir() + "'");
    return f;
  }

  // ---------------- numerical derivatives ----------------
  function derivee(f, S) {
    const h = 1e-4 * Math.max(Math.abs(S), 1e-8);
    return (f(S + h) - f(S - h)) / (2 * h);
  }
  function derivee2(f, S) {
    const h = 1e-3 * Math.max(Math.abs(S), 1e-8);
    return (f(S + h) - 2 * f(S) + f(S - h)) / (h * h);
  }

  // ---------------- strikes ----------------
  /* widths used by TooManyOptions: first = K1 - K0, last = Kn - Kn-1, inside = (K(i+1) - K(i-1)) / 2 */
  function largeursQuadrature(K) {
    const n = K.length;
    if (n < 2) return K.map(() => 0);
    return K.map((k, i) => i === 0 ? K[1] - K[0] : i === n - 1 ? K[n - 1] - K[n - 2] : (K[i + 1] - K[i - 1]) / 2);
  }

  /* listed options -> out-of-the-money puts (K < F) and calls (K > F) that pass the liquidity filters.
     options: [{K, c, oi, bid, ask, mark}] of ONE maturity; filtres: {oiMin, deuxCotes, kMin, kMax} */
  function selectionner(options, F, filtres) {
    const f = filtres || {};
    const garde = o => isFinite(o.K) && o.K > 0 && (o.mark > 0 || o.bid > 0 || o.ask > 0)
      && (!(f.oiMin > 0) || (o.oi || 0) >= f.oiMin)
      && (!f.deuxCotes || (o.bid > 0 && o.ask > 0))
      && (!(f.kMin > 0) || o.K >= f.kMin) && (!(f.kMax > 0) || o.K <= f.kMax);
    const puts = options.filter(o => !o.c && o.K < F && garde(o)).sort((a, b) => a.K - b.K);
    const calls = options.filter(o => o.c && o.K > F && garde(o)).sort((a, b) => a.K - b.K);
    return { puts, calls };
  }

  // ---------------- weights ----------------
  /* f: payoff function of S; F: expansion point (the future); puts / calls: sorted strike arrays (puts < F < calls).
     Returns {cash, futures, puts: [{K, w}], calls: [{K, w}]} such that the expiry payoff of the portfolio is
     cash + futures (S - F) + sum w (K - S)+ + sum w (S - K)+. */
  function poids(f, F, putsK, callsK, methode) {
    const K = putsK.concat(callsK);
    const n = K.length;
    if (methode === "gamma") {
      const larg = largeursQuadrature(K);
      const w = K.map((k, i) => derivee2(f, k) * larg[i]);
      return { cash: f(F), futures: derivee(f, F),
               puts: putsK.map((k, i) => ({ K: k, w: w[i] })),
               calls: callsK.map((k, i) => ({ K: k, w: w[putsK.length + i] })) };
    }
    if (n < 2 || !putsK.length || !callsK.length) {
      throw new Error("the interpolation method needs at least one put strike below F and one call strike above F");
    }
    // slopes of the interpolant between consecutive strikes; beyond the extreme strikes, the slope of f OUTSIDE
    // the range (one-sided differences: a centred one would average the two slopes of a kink at an end strike)
    const pente = [];
    for (let j = 0; j + 1 < n; j++) pente.push((f(K[j + 1]) - f(K[j])) / (K[j + 1] - K[j]));
    const hg = 1e-4 * K[0], hd = 1e-4 * K[n - 1];
    const gauche = (f(K[0]) - f(K[0] - hg)) / hg, droite = (f(K[n - 1] + hd) - f(K[n - 1])) / hd;
    const p = [gauche].concat(pente, [droite]);                 // p[j] = slope left of K[j], p[j+1] right of it
    const w = K.map((k, j) => p[j + 1] - p[j]);
    const c = putsK.length - 1;                                 // central segment: last put -> first call
    const s0 = pente[c];
    return { cash: f(K[c]) + s0 * (F - K[c]), futures: s0,
             puts: putsK.map((k, i) => ({ K: k, w: w[i] })),
             calls: callsK.map((k, i) => ({ K: k, w: w[putsK.length + i] })) };
  }

  /* expiry payoff of the portfolio at S (number or array) */
  function valeurEcheance(port, F, S) {
    const un = s => port.cash + port.futures * (s - F)
      + port.puts.reduce((a, o) => a + o.w * Math.max(o.K - s, 0), 0)
      + port.calls.reduce((a, o) => a + o.w * Math.max(s - o.K, 0), 0);
    return Array.isArray(S) ? S.map(un) : un(S);
  }

  /* today's value: discount * cash + sum w * price(K, isCall); the futures leg costs nothing */
  function valeurAujourdhui(port, actualisation, prix) {
    let v = actualisation * port.cash;
    port.puts.forEach(o => { v += o.w * prix(o.K, false); });
    port.calls.forEach(o => { v += o.w * prix(o.K, true); });
    return v;
  }

  /* executable cost: buy at the ask, sell at the bid (weights < 0 are sales) */
  function coutExecutable(port, actualisation, cote) {
    let v = actualisation * port.cash, manquants = 0;
    const un = (o, c) => {
      const q = cote(o.K, c);
      let px = o.w >= 0 ? q.ask : q.bid;
      if (!(px > 0)) { px = q.mark; manquants++; }
      v += o.w * px;
    };
    port.puts.forEach(o => un(o, false));
    port.calls.forEach(o => un(o, true));
    return { valeur: v, manquants };
  }

  /* strikes of a dense grid in log-moneyness around F, split into puts (K < F) and calls (K > F) */
  function grilleDense(F, largeur, n) {
    const puts = [], calls = [];
    for (let i = 0; i < n; i++) {
      const x = -largeur + 2 * largeur * (i + 0.5) / n;
      const K = F * Math.exp(x);
      (K < F ? puts : calls).push(K);
    }
    return { puts, calls };
  }

  const api = { compiler, derivee, derivee2, largeursQuadrature, selectionner, poids, valeurEcheance,
                valeurAujourdhui, coutExecutable, grilleDense };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Replication = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
