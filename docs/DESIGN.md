# Barnicha / Volatility Lab — design

## Direction

A quantitative research workbench in the dark "midnight glass" theme shared with the portfolio
(https://yassinebarnicha.github.io/): a deep navy background, glass panels, numbered vertical navigation, compact
controls and charts first. The identity rests on the calibration work and the project's data.

## Rules to keep

- Background `#080b12`, panels as a light glass gradient over `#111827`, ink `#eef3ff`, secondary ink `#a8b4ca`.
- Accent: a blue–violet gradient (`#93baff` → `#b2a4ff`) for the primary actions and the selected tab; orange
  `#f3ae78` for the model curve; white for the market points; violet `#b49dff` for the starting point.
- Rounded shapes: pill buttons and tabs, 16–18 px radius for panels, 10 px for input fields.
- System fonts only (Arial / Helvetica for text, the system monospace for numbers): nothing is downloaded.
- The colour ramp of the volatility surface keeps its scientific role (low vol dark, high vol light blue).
- Vertical navigation on a computer; on a phone, two "☰" menus (tabs, panel of the tab) and one smile per row.
- Below 1180 px, the settings come before the charts and their height is bounded.
- Formulas are typeset in LaTeX and rendered once at build time with KaTeX (`katex/`), never in the browser.
- The explanatory scientific texts and the existing data are kept.

## Maintenance

The visual direction is changed in `sources/design.css`. `python sources/build.py` embeds it in `index.html` with no
network request for the CSS. The historical structural rules stay in `sources/template_full.html`. The pricing engine,
the optimisers and the data files are not affected by the theme.

## Checks

The build, the script syntax, the HTML identifiers and the integrity of the data files are checked; the page was tested
in headless Chrome (every tab, desktop and phone widths, no JavaScript error, no horizontal overflow), and the screenshots
of the README come from that test.
