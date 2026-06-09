/* Headless runtime check: mock DOM + ECharts, execute app.js on real data. */
const fs = require("fs"), vm = require("vm"), path = require("path");
const dir = __dirname;
const html = fs.readFileSync(path.join(dir, "index.html"), "utf8");
const dataLine = html.split("\n").find(l => l.startsWith("const MODEL="));
if (!dataLine) { console.error("FAIL: data line not found in index.html"); process.exit(1); }

// ids that index.html actually defines
const ids = new Set();
for (const m of html.matchAll(/id="([^"]+)"/g)) ids.add(m[1]);

const requested = new Set();
const innerHTML = {};
let setOptionCalls = 0, errors = [];

function fakeEl(id) {
  return {
    _id: id,
    set innerHTML(v) { innerHTML[id] = v; },
    get innerHTML() { return innerHTML[id] || ""; },
    style: {}, clientWidth: 820, clientHeight: 320,
    addEventListener() {}, getAttribute() { return null; }, setAttribute() {},
    appendChild() {}, getContext() { return {}; },
  };
}
const document = {
  getElementById(id) {
    requested.add(id);
    if (!ids.has(id)) { errors.push("missing id in HTML: #" + id); return null; }
    return fakeEl(id);
  },
};
function Chart() {}
Chart.prototype.setOption = function (o) {
  setOptionCalls++;
  // touch series formatters/data to surface runtime throws
  try {
    JSON.stringify(o, (k, v) => (typeof v === "function" ? "fn" : v));
    (o.series || []).forEach(s => { void (s.data && s.data.length); });
  } catch (e) { errors.push("setOption serialize: " + e.message); }
};
Chart.prototype.resize = function () {};
const echarts = {
  init() { return new Chart(); },
  graphic: { LinearGradient: function () { return { __grad: true }; } },
};
const win = { addEventListener() {}, devicePixelRatio: 1 };

const sandbox = { document, echarts, window: win, console,
  setTimeout, JSON, Math, Object, Array, Number, String };
sandbox.global = sandbox; sandbox.window = Object.assign(win, sandbox);
vm.createContext(sandbox);

try {
  vm.runInContext(dataLine, sandbox, { filename: "data.js" });          // MODEL/MACRO/PAL/SEGC
  vm.runInContext(fs.readFileSync(path.join(dir, "app.js"), "utf8"), sandbox, { filename: "app.js" });
} catch (e) { errors.push("RUNTIME: " + e.stack.split("\n").slice(0, 3).join(" | ")); }

// assertions: every container that must be populated is non-empty
const mustFill = ["macroKpis", "demoRows", "srcRows", "modelKpis", "driverNotes",
  "liftRows", "segCards", "roiKpis", "roiSteps", "shapLocalNote", "fairAge", "fairInc"];
mustFill.forEach(id => { if (!(innerHTML[id] && innerHTML[id].length > 20)) errors.push("empty container: #" + id); });
if (setOptionCalls < 11) errors.push("expected >=11 charts, got " + setOptionCalls);

// spot-check no "undefined"/"NaN" leaked into rendered HTML
mustFill.forEach(id => {
  const h = innerHTML[id] || "";
  if (/undefined|NaN/.test(h)) errors.push("bad token in #" + id + ": " + (h.match(/.{0,15}(undefined|NaN).{0,15}/) || [])[0]);
});

if (errors.length) { console.error("CHECK FAILED:\n - " + errors.join("\n - ")); process.exit(1); }
console.log("CHECK PASSED · charts=" + setOptionCalls + " · containers filled=" + mustFill.length +
  " · segCards bytes=" + (innerHTML.segCards || "").length);
