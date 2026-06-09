/* Japanese life-insurance lapse demo, render layer (ECharts + DOM). */
(function () {
  "use strict";
  var FONT = "Inter, system-ui, sans-serif";
  var fmt = function (n) { return Math.round(n).toLocaleString("en-US"); };
  var jpy = function (n) {
    if (Math.abs(n) >= 1e9) return "¥" + (n / 1e9).toFixed(2) + "B";
    if (Math.abs(n) >= 1e6) return "¥" + (n / 1e6).toFixed(1) + "M";
    if (Math.abs(n) >= 1e3) return "¥" + (n / 1e3).toFixed(0) + "K";
    return "¥" + fmt(n);
  };
  var pct = function (x, d) { return (x * 100).toFixed(d == null ? 1 : d) + "%"; };
  var axBase = {
    axisLine: { lineStyle: { color: PAL.border } },
    axisTick: { show: false },
    axisLabel: { color: PAL.muted, fontFamily: FONT, fontSize: 11 },
    nameTextStyle: { color: PAL.text2, fontFamily: FONT, fontSize: 11 },
    splitLine: { lineStyle: { color: PAL.grid } },
  };
  var tipStyle = {
    backgroundColor: "#23272f", borderWidth: 0, padding: [8, 12],
    textStyle: { color: "#f4f5f7", fontFamily: FONT, fontSize: 12 },
    extraCssText: "border-radius:5px;box-shadow:0 2px 8px rgba(0,0,0,.12);",
  };
  var charts = [];
  function mk(id) { var c = echarts.init(document.getElementById(id), null, { renderer: "svg" }); charts.push(c); return c; }
  function kpiTile(label, value, sub) {
    return '<div class="bi-kpi"><span class="bi-kpi-label">' + label +
      '</span><span class="bi-kpi-value">' + value +
      '</span>' + (sub ? '<span class="bi-kpi-sub">' + sub + '</span>' : '') + '</div>';
  }
  var H = MODEL.headline, R = MODEL.roi, L = MODEL.lift;

  /* ---- 1. macro ---- */
  document.getElementById("macroKpis").innerHTML =
    MACRO.kpis.map(function (k) { return kpiTile(k.label, k.value, k.sub); }).join("");
  document.getElementById("demoRows").innerHTML = MACRO.demographics.map(function (d) {
    return '<tr><td>' + d[0] + '</td><td class="num"><b>' + d[1] +
      '</b></td><td class="muted" style="font-size:var(--text-xs)">' + d[2] + '</td></tr>';
  }).join("");
  document.getElementById("srcRows").innerHTML =
    MACRO.sources.map(function (s) { return "<li>" + s + "</li>"; }).join("");

  mk("cPolicies").setOption({
    grid: { left: 44, right: 16, top: 18, bottom: 24 },
    tooltip: Object.assign({ trigger: "axis", valueFormatter: function (v) { return v + "M"; } }, tipStyle),
    xAxis: Object.assign({ type: "category", data: MACRO.policies_series.map(function (p) { return p.year; }) }, axBase),
    yAxis: Object.assign({ type: "value", min: 184, max: 196, name: "Millions", scale: true }, axBase),
    series: [{
      type: "line", smooth: true, symbol: "circle", symbolSize: 6,
      data: MACRO.policies_series.map(function (p) { return p.v; }),
      lineStyle: { color: PAL.accent, width: 2.5 }, itemStyle: { color: PAL.accent },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: "rgba(59,111,212,.18)" }, { offset: 1, color: "rgba(59,111,212,.01)" }]) },
    }],
  });

  /* ---- 2. model headline ---- */
  document.getElementById("modelKpis").innerHTML = [
    kpiTile("Model AUC (5-fold CV)", H.auc_cv_mean.toFixed(3), "±" + H.auc_cv_std.toFixed(3) + " · logistic " + H.auc_log_cv_mean.toFixed(3) + " (+" + H.gbm_gap.toFixed(3) + ", negligible)"),
    kpiTile("Base lapse rate", pct(H.overall_lapse_rate, 1), "12-month, synthetic (market ~5.9%)"),
    kpiTile("Top-decile lift", L[0].lift + "×", "vs random targeting"),
    kpiTile("Captured in top 20%", pct(R.capture_top2_deciles, 0), "of all lapses, by score"),
  ].join("");

  // importance with ±1σ error bars
  var impRev = MODEL.importance.slice().reverse();
  mk("cImp").setOption({
    grid: { left: 8, right: 30, top: 10, bottom: 24, containLabel: true },
    tooltip: Object.assign({ trigger: "axis", axisPointer: { type: "shadow" },
      formatter: function (ps) { var p = ps[0]; var r = impRev[p.dataIndex];
        return r.feature + "<br>importance " + r.pct + " ±" + r.std_pct; } }, tipStyle),
    xAxis: Object.assign({ type: "value", name: "Relative importance", max: 110 }, axBase),
    yAxis: Object.assign({ type: "category", data: impRev.map(function (r) { return r.feature; }) }, axBase,
      { axisLabel: { color: PAL.text2, fontFamily: FONT, fontSize: 11 } }),
    series: [
      { type: "bar", data: impRev.map(function (r) { return r.pct; }), barWidth: "58%",
        itemStyle: { color: PAL.accent, borderRadius: [0, 3, 3, 0] } },
      { type: "custom", data: impRev.map(function (r, i) { return [i, r.pct, r.std_pct]; }),
        renderItem: function (params, api) {
          var i = api.value(0), v = api.value(1), e = api.value(2);
          var hi = api.coord([v + e, i]), lo = api.coord([v - e, i]), y = hi[1];
          var st = { stroke: PAL.text2, lineWidth: 1 };
          return { type: "group", children: [
            { type: "line", shape: { x1: lo[0], y1: y, x2: hi[0], y2: y }, style: st },
            { type: "line", shape: { x1: hi[0], y1: y - 4, x2: hi[0], y2: y + 4 }, style: st },
            { type: "line", shape: { x1: lo[0], y1: y - 4, x2: lo[0], y2: y + 4 }, style: st },
          ] };
        } },
    ],
  });

  var NOTES = {
    "Policy tenure (years)": "Front-loaded hazard: risk peaks in years 1-3, then policies self-select into committed holders.",
    "Payment method": "Manual/invoice billing lapses far more than bank auto-debit; converting to auto-pay is the cheapest save.",
    "Distribution channel": "Remote and bancassurance business persists worse than advised tied-agent policies that get ongoing service.",
    "Recent complaint": "A recent complaint is a near-term leading indicator of termination, and a window to intervene.",
    "Premium-to-income ratio": "Affordability stress: when premium is large vs income, the policy is first to be cut after a shock.",
    "Months since last servicing": "A long servicing gap raises lapse; silence is risk.",
    "Digital engagement": "App-active holders churn less; disengagement is an early-warning signal.",
    "Policyholder age": "Younger holders lapse more: less wealth, more job and life transitions.",
    "Product line": "Term lapses more than whole life; cash value and riders add stickiness.",
    "Number of riders": "More riders raise perceived value and switching cost, lowering lapse.",
    "Billing frequency": "Monthly payers re-decide affordability twelve times a year vs an annual commitment.",
    "Annual premium": "Larger premiums carry more affordability risk but also more value to protect.",
    "Household income": "Higher income cushions premium shocks, lowering lapse.",
    "Claims count": "Recent claims interactions shift retention either way depending on the experience.",
    "Region": "Regional income and channel mix create modest geographic differences in persistency.",
  };
  document.getElementById("driverNotes").innerHTML = MODEL.importance.slice(0, 6).map(function (r) {
    return "<li><b>" + r.feature + "</b>: " + (NOTES[r.feature] || "") + "</li>";
  }).join("");

  // SHAP global
  var sg = MODEL.shap_global.slice().reverse();
  mk("cShapG").setOption({
    grid: { left: 8, right: 28, top: 10, bottom: 24, containLabel: true },
    tooltip: Object.assign({ trigger: "axis", axisPointer: { type: "shadow" },
      valueFormatter: function (v) { return v + " (rel.)"; } }, tipStyle),
    xAxis: Object.assign({ type: "value", name: "Mean |SHAP|", max: 110 }, axBase),
    yAxis: Object.assign({ type: "category", data: sg.map(function (r) { return r.feature; }) }, axBase,
      { axisLabel: { color: PAL.text2, fontFamily: FONT, fontSize: 11 } }),
    series: [{ type: "bar", data: sg.map(function (r) { return r.pct; }), barWidth: "58%",
      itemStyle: { color: PAL.accent, borderRadius: [0, 3, 3, 0] } }],
  });

  // SHAP local (diverging)
  var sl = MODEL.shap_local, cs = sl.contributions.slice().reverse();
  mk("cShapL").setOption({
    grid: { left: 8, right: 24, top: 10, bottom: 24, containLabel: true },
    tooltip: Object.assign({ trigger: "axis", axisPointer: { type: "shadow" },
      valueFormatter: function (v) { return (v >= 0 ? "+" : "") + v.toFixed(2); } }, tipStyle),
    xAxis: Object.assign({ type: "value", name: "← lowers risk    raises risk →" }, axBase),
    yAxis: Object.assign({ type: "category", data: cs.map(function (c) { return c.feature; }) }, axBase,
      { axisLabel: { color: PAL.text2, fontFamily: FONT, fontSize: 10.5 } }),
    series: [{ type: "bar", data: cs.map(function (c) {
      return { value: c.value, itemStyle: { color: c.value >= 0 ? PAL.neg : PAL.pos } }; }), barWidth: "60%" }],
  });
  document.getElementById("shapLocalNote").innerHTML =
    "This policyholder scores <b>" + pct(sl.risk, 0) + "</b> lapse risk. The bars show what moved them there: each " +
    "attribute pushes risk up (red) or down (green) from the average customer. The reason an agent would act on.";

  /* ---- 3. performance ---- */
  mk("cRoc").setOption({
    grid: { left: 48, right: 18, top: 16, bottom: 40 },
    tooltip: Object.assign({ trigger: "axis" }, tipStyle),
    xAxis: Object.assign({ type: "value", min: 0, max: 1, name: "False positive rate", nameLocation: "middle", nameGap: 26 }, axBase),
    yAxis: Object.assign({ type: "value", min: 0, max: 1, name: "True positive rate" }, axBase),
    series: [
      { type: "line", showSymbol: false, smooth: true, data: MODEL.roc.map(function (p) { return [p.fpr, p.tpr]; }),
        lineStyle: { color: PAL.accent, width: 2.5 }, areaStyle: { color: "rgba(59,111,212,.08)" } },
      { type: "line", showSymbol: false, data: [[0, 0], [1, 1]], lineStyle: { color: PAL.muted, width: 1, type: "dashed" } },
    ],
  });

  // calibration: predicted vs observed by decile
  var rel = MODEL.reliability.map(function (r) { return [r.pred * 100, r.obs * 100]; });
  var relMax = Math.ceil(Math.max.apply(null, rel.map(function (p) { return Math.max(p[0], p[1]); })) / 5) * 5;
  mk("cCal").setOption({
    grid: { left: 48, right: 18, top: 16, bottom: 40 },
    tooltip: Object.assign({ trigger: "item", formatter: function (p) {
      return "Predicted " + p.value[0].toFixed(1) + "%<br>Observed " + p.value[1].toFixed(1) + "%"; } }, tipStyle),
    xAxis: Object.assign({ type: "value", min: 0, max: relMax, name: "Predicted lapse (%)", nameLocation: "middle", nameGap: 26 }, axBase),
    yAxis: Object.assign({ type: "value", min: 0, max: relMax, name: "Observed lapse (%)" }, axBase),
    series: [
      { type: "line", showSymbol: false, data: [[0, 0], [relMax, relMax]], lineStyle: { color: PAL.muted, width: 1, type: "dashed" } },
      { type: "scatter", data: rel, symbolSize: 9, itemStyle: { color: PAL.pos, opacity: .85 } },
    ],
  });

  var gains = [[0, 0]];
  L.forEach(function (d, i) { gains.push([(i + 1) * 10, d.cum_capture * 100]); });
  mk("cGains").setOption({
    grid: { left: 48, right: 18, top: 16, bottom: 40 },
    tooltip: Object.assign({ trigger: "axis", valueFormatter: function (v) { return v.toFixed(0) + "%"; } }, tipStyle),
    xAxis: Object.assign({ type: "value", min: 0, max: 100, name: "Book contacted (%, by risk)", nameLocation: "middle", nameGap: 26 }, axBase),
    yAxis: Object.assign({ type: "value", min: 0, max: 100, name: "Lapses captured (%)" }, axBase),
    series: [
      { type: "line", smooth: true, symbol: "circle", symbolSize: 5, data: gains,
        lineStyle: { color: PAL.pos, width: 2.5 }, itemStyle: { color: PAL.pos }, areaStyle: { color: "rgba(46,158,107,.08)" },
        markArea: { silent: true, itemStyle: { color: "rgba(59,111,212,.06)" }, data: [[{ xAxis: 0 }, { xAxis: 20 }]] } },
      { type: "line", showSymbol: false, data: [[0, 0], [100, 100]], lineStyle: { color: PAL.muted, width: 1, type: "dashed" } },
    ],
  });

  // cross-sectional 12-month lapse rate by current policy duration (no faked cohort survival)
  var HZ = MODEL.duration_profile.hazard;
  mk("cSurv").setOption({
    grid: { left: 48, right: 18, top: 16, bottom: 40 },
    tooltip: Object.assign({ trigger: "axis", valueFormatter: function (v) { return v.toFixed(1) + "%"; } }, tipStyle),
    xAxis: Object.assign({ type: "value", min: 0, max: 20, name: "Policy duration (years)", nameLocation: "middle", nameGap: 26 }, axBase),
    yAxis: Object.assign({ type: "value", min: 0, name: "12-month lapse rate (%)" }, axBase),
    series: [{
      type: "bar", data: HZ.map(function (h) { return [h.t, h.h * 100]; }),
      itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: "rgba(209,90,77,.75)" }, { offset: 1, color: "rgba(209,90,77,.35)" }]) },
      barWidth: "60%",
      markLine: { silent: true, symbol: "none", lineStyle: { color: PAL.muted, type: "dashed", width: 1 },
        label: { position: "insideEndTop", color: PAL.muted, fontSize: 10 },
        data: [{ xAxis: 1, label: { formatter: "13m" } }, { xAxis: 2, label: { formatter: "25m" } }] },
    }],
  });

  document.getElementById("liftRows").innerHTML = L.map(function (d) {
    var hot = d.decile <= 2;
    return '<tr' + (hot ? ' style="background:var(--accent-soft)"' : '') + '><td>' +
      (hot ? '<b>' + d.decile + '</b>' : d.decile) + '</td><td class="num">' + fmt(d.policyholders) +
      '</td><td class="num">' + pct(d.avg_risk) + '</td><td class="num">' + pct(d.actual_lapse_rate) +
      '</td><td class="num">' + d.lift.toFixed(2) + '×</td><td class="num">' + pct(d.cum_capture, 0) + '</td></tr>';
  }).join("");

  /* ---- 4. segmentation ---- */
  var S = MODEL.segments;
  var maxN = Math.max.apply(null, S.map(function (s) { return s.size; }));
  var base = H.overall_lapse_rate * 100;
  // scale axes to the data (with padding) so bubbles fill the panel, not the bottom-left corner
  var segLapse = S.map(function (s) { return s.lapse_rate * 100; });
  var segClv = S.map(function (s) { return s.avg_clv; });
  var xLo = Math.max(0, Math.floor(Math.min.apply(null, segLapse) - 1.5));
  var xHi = Math.ceil(Math.max.apply(null, segLapse) + 1.5);
  var yPad = (Math.max.apply(null, segClv) - Math.min.apply(null, segClv)) * 0.22 || 50000;
  var yLo = Math.max(0, Math.floor((Math.min.apply(null, segClv) - yPad) / 50000) * 50000);
  var yHi = Math.ceil((Math.max.apply(null, segClv) + yPad) / 50000) * 50000;
  mk("cSeg").setOption({
    grid: { left: 78, right: 32, top: 28, bottom: 48 },
    tooltip: Object.assign({ trigger: "item", formatter: function (p) {
      var s = p.data.seg;
      return '<b>' + s.name + '</b><br>Size: ' + fmt(s.size) + ' (' + pct(s.share, 0) + ')<br>Lapse rate: ' +
        pct(s.lapse_rate) + '<br>Avg CLV: ' + jpy(s.avg_clv) + '<br>Avg age: ' + s.avg_age + ' · top: ' + s.top_product; } }, tipStyle),
    xAxis: Object.assign({ type: "value", name: "Lapse rate (%)", nameLocation: "middle", nameGap: 26, min: xLo, max: xHi }, axBase),
    yAxis: Object.assign({ type: "value", name: "Avg lifetime value (¥)", min: yLo, max: yHi,
      axisLabel: { color: PAL.muted, fontFamily: FONT, fontSize: 11, formatter: function (v) { return jpy(v); } } }, axBase),
    series: [{
      type: "scatter",
      data: S.map(function (s, i) { return { value: [s.lapse_rate * 100, s.avg_clv], seg: s,
        symbolSize: 18 + 52 * (s.size / maxN), itemStyle: { color: SEGC[i % SEGC.length], opacity: .82 } }; }),
      label: { show: true, formatter: function (p) { return p.data.seg.name; }, position: "top",
        color: PAL.text2, fontFamily: FONT, fontSize: 10.5, fontWeight: 500 },
      markLine: { silent: true, symbol: "none", lineStyle: { color: PAL.muted, type: "dashed", width: 1 },
        data: [{ xAxis: base, label: { formatter: "book avg " + base.toFixed(1) + "%", color: PAL.muted, fontSize: 10 } }] },
    }],
  });
  document.getElementById("segCards").innerHTML = S.map(function (s, i) {
    var risk = s.lapse_rate > base / 100 ? "neg" : "pos";
    return '<div class="bi-card seg-card"><h3><span class="dot" style="background:' + SEGC[i % SEGC.length] +
      '"></span>' + s.name + '<span class="bi-badge ' + risk + '" style="margin-left:auto">' + pct(s.lapse_rate) + ' lapse</span></h3>' +
      '<div class="seg-stat"><span class="k">Size</span><span class="bi-num">' + fmt(s.size) + ' · ' + pct(s.share, 0) + '</span></div>' +
      '<div class="seg-stat"><span class="k">Avg lifetime value</span><span class="bi-num">' + jpy(s.avg_clv) + '</span></div>' +
      '<div class="seg-stat"><span class="k">Profile</span><span class="bi-num">age ' + s.avg_age + ' · ' + s.top_product + '</span></div>' +
      '<p class="note" style="margin-top:var(--space-2);color:var(--text-2)">' + s.play + '</p></div>';
  }).join("");

  /* ---- 5. ROI ---- */
  mk("cRoi").setOption({
    grid: { left: 112, right: 70, top: 8, bottom: 16 },
    tooltip: Object.assign({ trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: function (v) { return jpy(v); } }, tipStyle),
    xAxis: Object.assign({ type: "value" }, axBase, { axisLabel: { show: false }, splitLine: { show: false } }),
    yAxis: Object.assign({ type: "category", data: ["Campaign cost", "Net benefit", "Value retained"] }, axBase,
      { axisLabel: { color: PAL.text2, fontFamily: FONT, fontSize: 11 } }),
    series: [{ type: "bar", barWidth: "52%", data: [
        { value: R.campaign_cost_jpy, itemStyle: { color: PAL.neg, borderRadius: [0, 3, 3, 0] } },
        { value: R.net_benefit_jpy, itemStyle: { color: PAL.warn, borderRadius: [0, 3, 3, 0] } },
        { value: R.value_retained_jpy, itemStyle: { color: PAL.pos, borderRadius: [0, 3, 3, 0] } } ],
      label: { show: true, position: "right", color: PAL.text2, fontFamily: FONT, fontSize: 11, formatter: function (p) { return jpy(p.value); } } }],
  });
  document.getElementById("roiKpis").innerHTML = [
    kpiTile("Targeted", fmt(R.targeted_policyholders), "top 2 risk deciles"),
    kpiTile("Policies saved", fmt(R.saved_policies), "vs no action"),
    kpiTile("Value retained", jpy(R.value_retained_jpy), "PV of margin, lapsers"),
    kpiTile("Return", R.roi_x + "×", "net " + jpy(R.net_benefit_jpy)),
  ].join("");
  document.getElementById("roiSteps").innerHTML = [
    "Score the full in-force book; rank by 12-month lapse risk.",
    "Target the top 2 deciles: " + fmt(R.targeted_policyholders) + " policyholders holding " + pct(R.capture_top2_deciles, 0) + " of expected lapses.",
    "Intervene (outreach, auto-pay conversion, flexible payment) at ¥" + fmt(R.assumed_cost_per_policyholder_jpy) + " each.",
    "Assume a " + pct(R.assumed_relative_uplift, 0) + " relative cut in lapse → " + fmt(R.saved_policies) + " policies saved.",
    "Value retained = saved policies × ¥" + fmt(R.avg_clv_jpy) + " avg lifetime value (of lapsers) = " + jpy(R.value_retained_jpy) + ".",
  ].map(function (t) { return "<li>" + t + "</li>"; }).join("");

  // sensitivity heatmap
  var SS = MODEL.roi_sensitivity, cells = [];
  SS.net_billions.forEach(function (row, i) { row.forEach(function (v, j) { cells.push([j, i, v]); }); });
  var amax = Math.max.apply(null, cells.map(function (c) { return Math.abs(c[2]); }));
  mk("cSens").setOption({
    grid: { left: 56, right: 12, top: 12, bottom: 52 },
    tooltip: Object.assign({ position: "top", formatter: function (p) {
      return "lapse reduction " + pct(SS.uplift[p.value[1]], 0) + " · cost ¥" + fmt(SS.cost[p.value[0]]) + "<br>net <b>¥" + p.value[2] + "B</b>"; } }, tipStyle),
    xAxis: Object.assign({ type: "category", data: SS.cost.map(function (c) { return "¥" + (c / 1000) + "k"; }),
      name: "Cost per policyholder (¥)", nameLocation: "middle", nameGap: 28 }, axBase, { splitArea: { show: true } }),
    yAxis: Object.assign({ type: "category", data: SS.uplift.map(function (u) { return pct(u, 0); }), name: "Lapse reduction (%)" }, axBase, { splitArea: { show: true } }),
    visualMap: { min: -amax, max: amax, calculable: false, show: false, inRange: { color: [PAL.neg, "#eef0f4", PAL.pos] } },
    series: [{ type: "heatmap", data: cells,
      label: { show: true, fontFamily: FONT, fontSize: 11, formatter: function (p) { return p.value[2]; },
        color: PAL.text }, itemStyle: { borderColor: "#fff", borderWidth: 2 } }],
  });

  /* ---- 6. fairness ---- */
  function fairRows(arr) {
    return arr.map(function (g) {
      return '<tr><td>' + g.group + '</td><td class="num">' + fmt(g.n) + '</td><td class="num">' + pct(g.lapse) +
        '</td><td class="num">' + pct(g.flagged_rate) + '</td><td class="num">' + (g.auc == null ? "n/a" : g.auc.toFixed(3)) + '</td></tr>';
    }).join("");
  }
  document.getElementById("fairAge").innerHTML = fairRows(MODEL.fairness.by_age);
  document.getElementById("fairInc").innerHTML = fairRows(MODEL.fairness.by_income);
  document.getElementById("fairNote").textContent = MODEL.fairness.note;

  window.addEventListener("resize", function () { charts.forEach(function (c) { c.resize(); }); });
})();
