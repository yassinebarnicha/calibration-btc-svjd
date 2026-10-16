// Build-time LaTeX rendering (called by sources/maths.py, never loaded by a page).
// stdin : JSON [[tex, display], ...]   stdout : JSON [html, ...]
// KaTeX 0.19.0 (MIT licence, see sources/katex/LICENSE) is vendored in sources/katex/.
"use strict";
const katex = require("./katex/katex.min.js");
let entree = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", d => (entree += d));
process.stdin.on("end", () => {
  const sortie = JSON.parse(entree).map(([tex, display]) =>
    katex.renderToString(tex, {displayMode: !!display, throwOnError: true, output: "html", strict: "ignore"}));
  process.stdout.write(JSON.stringify(sortie));
});
