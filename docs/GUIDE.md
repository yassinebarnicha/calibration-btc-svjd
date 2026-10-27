# User guide — Bitcoin option calibration

Back to the [README](../README.md) · theory in the [report](../REPORT.pdf).

## Using the application

1. **Day**: the list of every available day. Each row gives the date, then what exists for that day: "3 calibrations"
   (embedded calibrated sets), "2 settings" (your saved settings, "one final" if any) and "downloaded" for a day fetched
   with *Today*.
   **Today's snapshot, written directly to `jours/`**:

   ```
   python sources/aujourdhui.py
   ```

   downloads the current Deribit chain (public API, no key), writes it to `jours/<date>.js` (path relative to the
   folder, nothing to choose), keeps the raw CSV in `instantanes/` and rebuilds the page. A day already present at the
   same date is replaced by the more recent snapshot.
   The page's **↻ Today** button does the same download without Python: the day is kept in the browser (it comes back
   at the next launch, marked "downloaded"), but a browser may not write to a folder on its own: it writes
   `jours/<date>.js` only if the site folder has been chosen once in *Settings*.
2. **Model** (*Model* tab): a variance block (Black-Scholes, Heston, double Heston, Heston with variance jumps) and a
   jump law (none, Merton, bi-lognormal, Kou, CGMY, Variance Gamma, NIG). The **ⓘ Dynamics** button shows on hover (and
   pins on click) the full dynamics of the active model, typeset in LaTeX: equations of the future and of the variance,
   jump law, compensator, characteristic function, constraints and role of each parameter. Hovering an entry of the lists
   gives its dynamics in one line. **Apply** switches to the chosen model; without a change, **Re-apply** restarts from
   the model's starting values.
3. **Starting point** (*Parameters and optimiser* tab): the list holds only the sets **of the active model**; changing
   the model changes the list. Order:
   - *My saved settings*;
   - *Calibrations of the day*, from the best IV RMSE to the worst, named "engine · method · n mat. · loss · RMSE" (for
     example "COS · DE + local · 6 mat. · price · 1/vega² equal · 38.6 bps");
   - *Generic start* (if it belongs to this model); *Model start* (always present).
   **Load this starting point** loads the entry shown, even if it is the only one; with the box ticked, its maturities,
   filters, pricer, loss and bounds are restored too.
4. **Parameters**: sliders and input fields, a lock per parameter (frozen during the optimisation), bounds. A jump
   intensity set to 0 sets its size (μJ, σJ) to 0 and freezes it; it returns to its previous value when λ becomes positive
   again.
5. **Loss, pricer, stacked days** (several days calibrated together, some parameters free per day).
6. **Greeks** (*Greeks* tab, in the central area): for each selected option of a maturity, market / model IV and price,
   then Δ, Γ 1 % (change of Δ for +1 % of F), Vega (per vol point) and Θ (per day), twice: **Black-76** (closed forms, at
   the market IV or at the model IV) and **active model** (central finite differences on its COS or PROJ pricer: F ±0.1 %,
   instantaneous vol σ₀ ±0.1 %, maturity ±1 day). Bates has no closed form for its Greeks, nor for its price: they go
   through the characteristic function. Check: with the Black-Scholes model, the finite differences recover Black-76 to
   the decimals shown (Θ within 0.1 %). One chart per Greek (Δ, Γ, Vega, Θ by strike, model against Black-76) and a CSV
   export. The gap model Δ − Black-76 Δ is the smile effect on the hedge.
7. **Vol surface** (*Vol surface* tab, computed only when opened): the implied volatility surface of the active model in
   3-D (log-moneyness k = ln(K/F), maturity, vol), priced on a grid of 25, 41 or 61 strikes per maturity and inverted with
   Black-76, with the market IVs on top. Two modes:
   - **Calibrated only**: the selected maturities, the calibrated options (●) and the surface over their range;
   - **All the day's points + model extrapolation**: every option of the day on every maturity (○ those not used in the
     calibration, mark IV) and the surface extended to that whole area; hovering a point gives the model IV exactly at
     that point (extrapolated outside the calibrated data).
   The surface is always priced with PROJ: its grid follows the requested strikes, while the truncation interval of COS
   narrows with the maturity (at 4 h to expiry and in wide wings, COS differed from PROJ by up to 2.6·10⁵ $); where the
   model price is almost zero, the vol is undefined and the surface has a hole. Drag to rotate, wheel to zoom,
   double-click for the default view. During an optimisation the surface is recomputed only once per second. Drawn
   without any external library.
8. **Price your own options** (*Pricer* tab): with the active model and its current parameters, with PROJ (accurate even
   for very short maturities and far strikes).
   - *By hand*: type, K, F, maturity (days), r and, optionally, a market price → model price and IV, market IV and gap,
     Δ, Γ, Vega, Θ of the model and of Black-76.
   - *CSV file*: one row per option, required columns `type` (call/put, C/P), `K`, `F` and the maturity as `T` (years)
     **or** `jours` (days) **or** `echeance` (YYYY-MM-DD, 08:00 UTC expiry, counted from `valorisation` if that column
     exists, otherwise from the day's snapshot); optional `r`, `prix_marche` (market price); any other column is copied.
     Separator `,` or `;` (decimal comma accepted with `;`). The file comes back (`<name>_price.csv`) with `iv_marche,
     prix_modele, iv_modele, ecart_iv_bps, ecart_prix, delta/gamma/vega/theta` of the model and of Black-76, `vol_b76,
     modele, pricer, erreur`; an invalid row keeps its data and receives its message in `erreur`. *Template CSV* button:
     an example file to fill in. (Column names keep the original format so that existing files still work.)
9. **Exotic options by Monte Carlo** (*Pricer* tab, computed only on click, can be stopped):
   - *Parameters*: the current ones (sliders, optimisation result) or any saved setting or calibration of the day of the
     active model;
   - *Products*: Asian, barrier, digital, American (Longstaff-Schwartz), lookback, European; or **composite**: observed
     value (final F, average, max, min) × payoff (call, put, digital) × up to two barriers (up/down, in/out) × exercise
     (European, American); or a **free formula** (variables `FT, MOY, MAX, MIN, F0, K, B, B2, Q, T`, functions
     `max, min, abs, exp, log, sqrt`, comparisons worth 1 or 0);
   - *Simulation*: CIR factors by QE (Andersen 2008), Merton, bi-lognormal, Kou, Variance Gamma and NIG jumps (CGMY has
     no simple exact simulation: not offered); discrete monitoring at each step;
   - *American*: regression on 1, x, x², x³ and the Black-76 European value of the remaining option, which also serves as
     a floor for the continuation (without it, the regression noise caused wrong exercises); checked: premium ≈ 0 for
     r = 0, positive for r > 0;
   - *Control*: the European with strike K is simulated on the same paths and compared with its Fourier price (gap in
     standard errors; |gap| > 3 σ signals a discretisation bias); it also serves as a control variate. Checked on
     Black-Scholes, Heston + Merton, double Heston + bi-lognormal, Heston with variance jumps + Kou, Heston + VG,
     Heston + NIG (gaps from −1.1 to +1.9 σ).
10. **GEX — gamma exposure** (*GEX* tab, computed when opened): per option, sign × open interest (BTC) × Γ × F² × 1 % =
    the dollar delta to buy back or sell for a +1 % move of the future. Selected or all maturities; Black-76 gamma at the
    mark IV or the model's; "market makers" convention (+ calls, − puts) or raw gamma. Tiles: total GEX, flip level (zero
    gamma), call wall, put wall, calls/puts and open interest; charts: net GEX by strike and total GEX against the level of
    the future (−20 % to +20 %). The open interest comes from the Deribit snapshots (column `oi` of the days; missing on
    the two reconstructed days).
11. **Replication — static replication of a payoff** (*Replication* tab; engine in `sources/replication.js`, tests in
    `tests/test_replication.js`): a payoff f(S_T) at the chosen maturity is rebuilt as f(F) + f'(F)(S_T − F) plus
    out-of-the-money puts below the future F and calls above it (Carr & Madan). Presets: straddle, call (check: one
    option), call spread, log contract (variance swap), quadratic, power, or a free formula of S, F, K, K2, T (parsed,
    never evaluated as code). Weights: *exact at the listed strikes* (change of slope of f between strikes: the
    portfolio equals f at every listed strike, kinks included) or *f''(K)·ΔK* (the quadrature of TooManyOptions, for
    smooth payoffs only). Filters: minimum open interest, two-sided quotes. Tiles: cost at the mark or mid, executable
    cost (buy at the ask, sell at the bid), the same payoff with dense strikes under the interpolated smile and under
    the model, the listed replica under the model, maximum error at expiry; for the log contract, the model-free
    implied volatility. Charts: target and replica at expiry, error, weights by strike; table of the legs.
12. **Optimiser** (Feller enforced or not, within the slider bounds, locked parameters fixed):

   | Method | Nature | When to choose it |
   |---|---|---|
   | Classic Nelder–Mead (default) | local, coefficients 1, 2, ½, ½ | refining from a good starting point |
   | Adaptive Nelder–Mead (Gao & Han 2012) | local, coefficients depending on the dimension n | many free parameters: usually goes lower, stops later |
   | Differential evolution (Storn & Price 1997) | global, Latin-hypercube population | no good starting point; fixed seed → reproducible result |
   | DE then Nelder–Mead (classic or adaptive) | global then local | the Python calibration chain (Nelder–Mead instead of SLSQP); the local step can change pricer |

   Settings: tolerance, max evaluations, initial step (Nelder–Mead); best1bin/rand1bin strategy, popsize, generations,
   mutation, recombination, tol, atol, seed, injection of the current point (DE), with two presets "scipy defaults" and
   "Production settings" (those of the original Python calibration chain). They are saved with the setting.

## On a phone

- At the top, a fixed bar: "☰" (left) opens the **tabs** panel, the RMSE in the middle, "☰ Settings" (right) opens the
  **tab's settings** panel (sliders, starting point, pricer…).
- In the centre, the smiles, **one maturity per row**; at the bottom, always visible, **"Optimise"** with its progress and
  status.
- A panel closes with "✕ Close", by choosing a tab, or by touching the dark veil.
- The page is slightly zoomed out (85 %); on a computer, it is at 80 %.

## Speed and fluidity

- **Fastest default settings**: COS pricer (N = 512, L = 24) and the Bates model (Heston + lognormal jumps, 8
  parameters). PROJ and the other models remain available; a chosen setting is remembered by the browser.
- **Pricer**: everything that does not depend on the frequency (jump compensators, Γ(−Y) of CGMY, k_J) is computed once
  per maturity, the characteristic function creates no intermediate array, COS computes only the useful real part, and
  the FFT of PROJ reads its twiddle factors from a table. Unchanged prices (maximum gap 6·10⁻¹¹ $ over 17,192 prices,
  28 model compositions, COS and PROJ).
- **Optimiser**: computed in 12 ms slices (the page keeps its 60 frames per second); the display is refreshed about
  every 100 ms and reuses the evaluation the optimiser has just made instead of redoing it; the smiles are drawn before
  the other writes of the page; the Greeks tab is recomputed only once per second during an optimisation (and at the end).
- **COS pricer**: the complex modulus is computed without `Math.hypot` (slow) and the series stops where its remainder
  is bounded below 10⁻¹⁰ $: long maturities need only a fraction of the N terms.
- **Mathematics**: formulas are rendered by KaTeX at build time, not in the browser.
- **Measurements** (Chrome, Bates, 6 maturities, 222 options, COS N = 512):

  | Block | Time |
  |---|---|
  | a full evaluation (prices, IVs, loss, metrics) | ≈ 1.3 ms |
  | of which the characteristic function | ≈ 0.7 ms |
  | of which the inversion of the implied volatilities | ≈ 0.15 ms |
  | Nelder–Mead | ≈ 650 evaluations per second |
  | a screen refresh (smiles, metrics, sliders) | ≈ 3.5 ms |

  PROJ (N = 2048) costs about 3 times more; a model with two jump components (11 parameters) also needs more iterations.

## Saving and exporting

- **Save this setting**: the setting (model, parameters, day, maturities, filters, pricer, loss, bounds, results) goes to
  the browser **and to disk**. On the first save, choose the site folder (the browser remembers it):

  ```
  resultats/<day>/<variance>-<jumps>/NN_<name>/   reglage.json, params.json, results.csv, df_used.csv, smile_grid.csv, smiles.png
  resultats/<day>/final/                           the setting marked "final" for the day
  resultats/jeux_enregistres.json                  all your settings, in the common format of the sets
  ```
- **Export parameter sets (JSON)**: every set of a model, over all days, filtered by origin (historical calibrations, my
  settings), number of maturities (from … to …), loss, period, maximum IV RMSE, and "all" or "the best per day". The
  number of sets kept is shown before the export.

**Common format of the sets** ("calibration-a-la-main/jeux", version 1), shared with the calibration scripts:
`id, jour, instantane, modele {variance, sauts}, parametres, calibration {origine, moteur, methode, source},
donnees {echeances, filtres}, pricer, perte {mesure, ponderation}, resultats {rmse_iv_bps, rmse_prix_usd, n_options}`.
Model keys: variance `const`, `heston`, `heston2`, `hestonJ`; jumps `aucun`, `logn`, `biln`, `kou`, `cgmy`, `vg`, `nig`.
(Keys are French and kept as they are: they identify data already saved.)

## Contents

```
├── README.md, REPORT.pdf, requirements.txt, vercel.json, .vercelignore, .nojekyll
├── .github/workflows/maj_quotidienne.yml   Deribit snapshot every morning (GitHub Actions)
├── docs/                         GUIDE.md, DESIGN.md, screenshots, report/ (LaTeX source of REPORT.pdf and its data)
└── (site root)
    ├── index.html                the page (assembled by sources/build.py)
    ├── katex/                    KaTeX stylesheet and fonts used by the formulas (MIT licence)
    ├── futures.js                286 future maturities (listed and implied forwards)
    ├── jeux.js                   index of every embedded calibrated set (for the export)
    ├── jours/<date>.js           one file per day: full chain, default book flagged, calibrated sets of the day
    │                             (T to the hour up to the 08:00 UTC expiry, r = log(F/X)/T)
    └── sources/
        ├── template_full.html    the page (models, dynamics, menus, saving, export)
        ├── design.css            the theme
        ├── pricer.js             characteristic functions, COS, PROJ, Black-76
        ├── maths.py, katex_rendu.js, katex/, maths_cache.json   build-time LaTeX rendering
        ├── calibrations.json     the 529 embedded calibrated sets, in the common format
        ├── jeux.py               common format: attachment to the days, display name
        ├── ajouter_jours.py      adds days from Deribit snapshots
        ├── ajouter_calibrations.py  stores calibrated sets in the days
        ├── aujourdhui.py         current Deribit snapshot -> ../jours/<date>.js, then build
        ├── build.py              assembles index.html and jeux.js
        ├── telecharger_futures.py  Deribit futures history -> futures.js
        ├── donnees_deribit/      preparation of the snapshots
        └── pricers_fourier/      Black-76 and implied volatility
```

## Updating the data

Python 3.10 or more recent, numpy, scipy, pandas, requests. From `sources/`:

| I want to… | Command |
|---|---|
| add the days missing from a snapshot folder | `python ajouter_jours.py <folder>` then `python build.py` |
| add or replace specific days | `python ajouter_jours.py <folder> 2026-10-13 2026-10-14` |
| store calibrated sets (JSON in the common format) | `python ajouter_calibrations.py jeux.json --ajouter` then `python build.py` |
| rebuild everything from calibrations.json | `python ajouter_calibrations.py` then `python build.py` |
| update the futures | `python telecharger_futures.py` then `python build.py` |
| add the current snapshot to jours/ | `python aujourdhui.py` (rebuilds the page) |
| open the page on another day | `python build.py --jour 2026-08-26` |
| rebuild the report | in `docs/report/`: `pdflatex report.tex` twice, then move `report.pdf` to `../../REPORT.pdf` |

A new model is added in `sources/pricer.js` (exponent of the characteristic function), then in the template
(`VARIANCES` or `SAUTS`, and its entry in `DYNAMIQUES`, with its dynamics in LaTeX through `tex("…")`); `python build.py`
rebuilds the page. A new formula needs Node.js once (it is rendered by KaTeX and cached in `sources/maths_cache.json`);
afterwards, and in the daily GitHub Action, Python alone is enough.

## Scripts

### `ajouter_jours.py`

Adds days to the page: ../jours/<date>.js from Deribit snapshots, then python build.py.

| Argument | Values | Default | Role |
|---|---|---|---|
| `dossier` | text | — | folder of the btc_options_snapshot_*.csv snapshots |
| `dates` | text … | — | YYYY-MM-DD (default: the days missing from the page) |
| `--jeux` | text | — | calibrations.json or historique.csv of the daily chain (default: calibrations.json) |

### `ajouter_calibrations.py`

Stores calibrated parameter sets in the days of the page (../jours/<day>.js), then python build.py.

| Argument | Values | Default | Role |
|---|---|---|---|
| `fichier` | text | `calibrations.json` | file of calibrated sets |
| `--jours` | text … | — | YYYY-MM-DD or YYYY-MM-DD_HHMMSS (default: every day of the page) |
| `--ajouter` | flag | — | keep the calibrations already present in the days |

### `aujourdhui.py`

Downloads the current Deribit snapshot, writes it directly to ../jours/<date>.js, then rebuilds the page.

| Argument | Values | Default | Role |
|---|---|---|---|
| `--devise` | text | `BTC` | currency of the Deribit options |
| `--instantanes` | text | `../instantanes` | folder where the raw CSV of the snapshot is kept |
| `--jeux` | text | — | calibrations.json or historique.csv for the starting points of the day |
| `--sans-build` | flag | — | do not rebuild index.html (python build.py will) |

### `build.py`

Builds ../index.html: the page, the pricer and one day embedded; renders the LaTeX formulas.

| Argument | Values | Default | Role |
|---|---|---|---|
| `--jour` | text | — | day embedded in index.html, YYYY-MM-DD or YYYY-MM-DD_HHMMSS (default: the most recent) |

### `telecharger_futures.py`

Full daily history of every Deribit future -> futures.js.

| Argument | Values | Default | Role |
|---|---|---|---|
| `--cache` | text | `cache_futures` | cache folder of the raw answers |
| `--tout-retelecharger` | flag | — | also downloads again the expired maturities already cached |
| `--pause` | real | `0.12` | seconds between two requests |

## Publishing (GitHub Pages)

1. Create a **public** repository on GitHub.
2. From this folder (or with GitHub Desktop: *Add local repository → create a repository → Publish repository*, unticking
   *Keep this code private*):

   ```
   git init
   git add .
   git commit -m "Bitcoin option calibration"
   git branch -M main
   git remote add origin https://github.com/yassinebarnicha/calibration-btc-svjd.git
   git push -u origin main
   ```
3. On GitHub: **Settings → Pages → Build and deployment → Deploy from a branch → `main` / `(root)`**. The site is online
   a few minutes later at `https://yassinebarnicha.github.io/calibration-btc-svjd/`, served by a global network. Nothing
   to pay, no server to manage: the page and its data are static files, all the computing happens in the visitor's
   browser.

The `.nojekyll` file asks GitHub to serve the files as they are. The site can also be deployed on Vercel:
`vercel.json` declares it as a static site with no build step, and `.vercelignore` keeps the Python scripts out of the
deployment.

## Automatic data updates

`.github/workflows/maj_quotidienne.yml` runs every day at 08:20 UTC (just after the Deribit expiry):
`pip install -r requirements.txt`, then `python sources/aujourdhui.py` (snapshot of the Deribit chain → new
`jours/<date>.js`, `index.html` and `jeux.js` rebuilt), then a commit; GitHub Pages republishes the page automatically.
It can also be run by hand: **Actions → Daily update → Run workflow**. The raw CSV of the snapshot is not versioned
(`.gitignore`): the repository grows by about 120 KB per day. If Deribit ever refused requests from GitHub's machines, the
job would fail (visible in the Actions tab) without breaking anything: the site keeps the days already published.
