# -*- coding: utf-8 -*-
"""Render the self-contained index.html for the Japanese life-insurance lapse demo.

Editorial / essay layout: a single readable column, charts as figures inside
the narrative, consistent type scale, minimal box chrome. Embeds (a) the real,
cited market-context figures and (b) the model output from dashboard_data.json,
inline, so the file opens from disk with no server. Charts use ECharts (CDN).
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
CSS = (Path(r"C:/Users/biconsulting/OneDrive - Monte Cablevideo S.A/Design_System/bi-design-system.css")
       ).read_text(encoding="utf-8")
MODEL = json.loads((HERE / "dashboard_data.json").read_text(encoding="utf-8"))

# --- real, cited market context (from LIAJ Fact Book 2024 / JILI / OECD / MIC) ---
MACRO = {
    "kpis": [
        {"label": "Industry premium income", "value": "¥37.52T", "sub": "FY2023, +8.8% y/y (LIAJ)"},
        {"label": "Individual policies in force", "value": "194.9M", "sub": "16th straight year up (LIAJ)"},
        {"label": "Household coverage", "value": "89.2%", "sub": "2+ person households (JILI 2024)"},
        {"label": "Lapse & surrender ratio", "value": "5.9%", "sub": "of in-force benefits, FY2023 (LIAJ)"},
        {"label": "Population aged 65+", "value": "29.3%", "sub": "Sept 2024, world's highest (MIC)"},
    ],
    "policies_series": [
        {"year": "FY19", "v": 187.48}, {"year": "FY20", "v": 190.24}, {"year": "FY21", "v": 193.01},
        {"year": "FY22", "v": 194.58}, {"year": "FY23", "v": 194.94},
    ],
    "demographics": [
        ("Total fertility rate", "1.20", "Record low, 2023 (MHLW)"),
        ("Population trend", "13 yrs down", "123.4M, from 128.5M peak (MIC)"),
        ("65+ share by 2040", "34.8%", "Projected (OECD, 2024)"),
        ("Avg household death benefit", "¥19.36M", "Down from ¥20.27M in 2021 (JILI)"),
    ],
    "sources": [
        "Life Insurance Association of Japan (LIAJ). Life Insurance Fact Book 2024 (FY2023)",
        "Japan Institute of Life Insurance (JILI). Nationwide Survey 2024",
        "Statistics Bureau of Japan / MIC. Population estimates, Sept 2024",
        "OECD. Addressing Demographic Headwinds in Japan (2024)",
        "LIMRA / SOA. U.S. Individual Life Persistency studies (lapse-curve benchmarks)",
    ],
}

PALETTE = {
    "accent": "#3b6fd4", "accentSoft": "#e8eefb", "pos": "#2e9e6b", "warn": "#caa23a",
    "neg": "#d15a4d", "text": "#2a2e37", "text2": "#565c69", "muted": "#8b919d",
    "border": "#e4e7ed", "surface": "#fbfcfd", "grid": "#eceff3",
}
SEG_COLORS = ["#3b6fd4", "#d15a4d", "#2e9e6b", "#7a5ccb", "#caa23a"]

DATA_JS = "const MODEL=%s;const MACRO=%s;const PAL=%s;const SEGC=%s;" % (
    json.dumps(MODEL, ensure_ascii=False), json.dumps(MACRO, ensure_ascii=False),
    json.dumps(PALETTE), json.dumps(SEG_COLORS),
)

# numbers reused in prose
H = MODEL["headline"]; R = MODEL["roi"]
auc = f"{H['auc']:.3f}"; lapse_pct = f"{H['overall_lapse_rate']*100:.1f}%"
d1_lift = MODEL["lift"][0]["lift"]; cap2 = f"{R['capture_top2_deciles']*100:.0f}%"
roi_x = R["roi_x"]; net_b = f"¥{R['net_benefit_jpy']/1e9:.2f}B"
cv_gbm = f"{H['auc_cv_mean']:.3f} ± {H['auc_cv_std']:.3f}"
cv_log = f"{H['auc_log_cv_mean']:.3f} ± {H['auc_log_cv_std']:.3f}"
gap_v = f"{H['gbm_gap']:.3f}"; gap_p = f"{H['gbm_gap_p']:.2f}"
haz0 = f"{MODEL['duration_profile']['hazard'][0]['h']*100:.0f}%"
be_uplift = f"{R['breakeven_uplift']*100:.0f}%"
sil5 = next(s["silhouette"] for s in MODEL["silhouette"] if s["k"] == 5)
cost_each = f"¥{R['assumed_cost_per_policyholder_jpy']:,}"
brier = f"{H['brier']:.3f}"
n_ph = f"{MODEL['meta']['n_policyholders']:,}"

HTML = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Predicting and preventing policy lapse · Japanese life market</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
{CSS}
/* =============== editorial layer (overrides the BI card chrome) =============== */
body {{ background:#fff; }}
/* ONE column: text and every figure/table share the exact same width, centered on the page.
   No "text cut short while charts run wide" mismatch. */
.article {{ max-width: 780px; margin: 0 auto; padding: var(--space-12) var(--space-8) var(--space-16); }}

/* type scale: one body size, one small (caption) size, deliberate headings */
.article p {{ font-size: .9375rem; line-height: 1.65; color: var(--text); margin: 0 0 1rem; }}
.article h1 {{ font-size: 1.75rem; line-height: 1.18; font-weight: 700; letter-spacing: -.015em;
  color: var(--text); margin: 0 0 .85rem; }}
.article .lead {{ font-size: 1.02rem; line-height: 1.58; color: var(--text-2); margin: 0 0 1.3rem; font-weight: 400; }}
.eyebrow {{ font-size: .72rem; letter-spacing: .09em; text-transform: uppercase; color: var(--muted);
  font-weight: 600; margin: 0 0 .9rem; }}

.sec {{ margin-top: 3rem; padding-top: 1.6rem; border-top: 1px solid var(--border); }}
.sec > h2 {{ font-size: 1.22rem; font-weight: 600; letter-spacing: -.01em; color: var(--text); margin: 0 0 .3rem; }}
.sec > h2 .n {{ color: var(--accent); font-variant-numeric: tabular-nums; margin-right: .55ch; font-weight: 700; }}
.sec-meta {{ font-size: .8rem; color: var(--muted); margin: 0 0 1.3rem; }}

/* figures: no box, just chart + caption */
figure.fig {{ margin: 1.5rem 0; }}
figure.fig .cap-h {{ font-size: .875rem; font-weight: 600; color: var(--text); margin: 0 0 .15rem; }}
figure.fig figcaption {{ font-size: .8rem; color: var(--muted); line-height: 1.5; margin-top: .5rem; }}
.chart {{ width: 100%; }}
.fig-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.6rem 1.8rem; margin: 1.7rem 0; align-items: start; }}
.fig-2 figure.fig {{ margin: 0; }}
.split {{ display: grid; grid-template-columns: 1.2fr 1fr; gap: 2rem; align-items: start; margin: 1.7rem 0; }}
@media (max-width: 720px) {{ .fig-2, .split {{ grid-template-columns: 1fr; }} }}

/* stat band: borderless KPI strip, hairline top/bottom (no individual boxes) */
.bi-kpi-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(116px, 1fr)); gap: 1.4rem 1rem;
  margin: 1.7rem 0; padding: 1.2rem .2rem; background: none !important; border: none !important;
  border-top: 1px solid var(--border) !important; border-bottom: 1px solid var(--border) !important; border-radius: 0 !important; }}
.bi-kpi {{ background: none !important; border: none !important; box-shadow: none !important; padding: 0 !important;
  display: flex; flex-direction: column; gap: 3px; }}
#roiKpis {{ grid-template-columns: repeat(2, 1fr) !important; }}  /* half-width figure: clean 2x2, no orphan */
.bi-kpi-label {{ font-size: .74rem; color: var(--muted); font-weight: 500; }}
.bi-kpi-value {{ font-size: 1.32rem; font-weight: 700; color: var(--text); line-height: 1.1; letter-spacing: -.01em; }}
.bi-kpi-sub {{ font-size: .72rem; color: var(--muted); line-height: 1.4; }}

/* honesty note: quiet, ruled, not a coloured chip */
.honesty {{ border-left: 2px solid var(--accent); padding: .1rem 0 .1rem 1.1rem; margin: 1.5rem 0;
  color: var(--text-2); font-size: .98rem; line-height: 1.6; }}
.honesty b {{ color: var(--text); }}

/* lists read at body weight, not tiny grey */
.article ul.flow {{ margin: .5rem 0 1rem; padding-left: 1.2em; }}
.article ul.flow li {{ font-size: .9375rem; line-height: 1.55; color: var(--text); margin: .4rem 0; }}
.article ul.flow li b {{ font-weight: 600; }}

/* tables: keep, give them a caption + breathing room */
.tbl-cap {{ font-size: .875rem; font-weight: 600; color: var(--text); margin: 1.5rem 0 .5rem; }}
.bi-table {{ font-size: .86rem; }}
.sec > table.bi-table {{ max-width: 100%; }}
#fairAge, #fairInc {{ width: 100%; }}
#fairAge td:first-child, #fairInc td:first-child {{ white-space: nowrap; }}

/* segments: 5 full-width rows, hairline-separated; the 3 stats sit inline in 3 columns (uses the width, no collision) */
.seg-grid {{ display: flex; flex-direction: column; margin-top: 1.5rem; }}
.seg-card.bi-card {{ display: grid; grid-template-columns: repeat(3, 1fr); column-gap: 1.6rem; row-gap: .5rem;
  background: none; border: none; border-top: 1px solid var(--border); border-radius: 0; box-shadow: none; padding: 1.1rem 0; }}
.seg-card.bi-card:first-child {{ border-top: none; padding-top: .2rem; }}
.seg-card > h3 {{ grid-column: 1 / -1; font-size: .9rem; font-weight: 600; gap: .5rem; margin: 0; }}
.seg-card > .seg-stat {{ display: flex; justify-content: space-between; gap: .6rem; font-size: .8rem; }}
.seg-card .seg-stat .k {{ color: var(--muted); }}
.seg-card > .note {{ grid-column: 1 / -1; font-size: .84rem !important; line-height: 1.5;
  color: var(--text-2) !important; margin: .15rem 0 0; }}
@media (max-width: 560px) {{ .seg-card.bi-card {{ grid-template-columns: 1fr; }} }}
.dot {{ width: 9px; height: 9px; border-radius: 2px; display: inline-block; flex: 0 0 auto; }}

/* author / publish footer */
.author {{ margin-top: 3.6rem; padding-top: 1.5rem; border-top: 1px solid var(--border); }}
.author .name {{ font-size: 1.08rem; font-weight: 600; color: var(--text); margin: 0 0 .2rem; }}
.author .role {{ font-size: .92rem; color: var(--text-2); margin: 0 0 .7rem; }}
.author .links {{ font-size: .92rem; color: var(--text-2); }}
.author .links a {{ color: var(--accent); text-decoration: none; font-weight: 500; }}
.author .links a:hover {{ text-decoration: underline; }}
.author .stack {{ font-size: .82rem; color: var(--muted); margin: 1rem 0 0; }}
.src {{ font-size: .85rem; color: var(--muted); line-height: 1.55; padding-left: 1.1em; margin: .4rem 0 0; }}
.src li {{ margin: 3px 0; }}
.note {{ font-size: .85rem; color: var(--muted); line-height: 1.55; }}
</style>
</head>
<body>
<div class="bi-tip" id="tip"></div>
<article class="article">

  <header>
    <p class="eyebrow">Lapse modelling · a worked case study</p>
    <h1>Predicting and preventing policy lapse in the Japanese life market</h1>
    <p class="lead">A <b>lapse</b> is when a policyholder stops paying and the policy ends, taking its future premiums
      and value with it. Japan's life market has <b>stopped growing</b>: nine in ten households already have cover and
      the population is shrinking, so an insurer's value increasingly comes from <b>keeping the policies it already
      holds</b> rather than selling new ones. This case study works that problem end to end: score every in-force policy
      by its chance of lapsing in the next year, explain <b>what is driving</b> that risk, group customers into segments
      a retention team can act on, and estimate <b>what a save campaign is worth</b>.</p>
    <p>It was built end to end in Python (scikit-learn), and every chart is a live output of the model, not a mock-up. I
      have flagged plainly where the evidence is strong and where it is not.</p>
    <p class="honesty">One caveat up front, because it changes how to read every number below. The market figures are
      real and cited. The policyholder records are <b>synthetic</b>: {n_ph} policies I generated, since real insurer data
      is confidential. I built the generator so each lapse driver points the way the actuarial literature says it should,
      so the patterns are realistic. The trade-off: the model's accuracy reflects how well it recovers a pattern <i>I</i>
      designed, so on a real book I would expect it to be lower. What carries over is the <b>method and the pipeline</b>,
      not the headline accuracy.</p>
  </header>

  <!-- 1. MARKET ------------------------------------------------------------>
  <section class="sec">
    <h2><span class="n">1</span>Why retention is the lever</h2>
    <p class="sec-meta">Japan life insurance, FY2023</p>
    <p>The Japanese life market is large and mature. Industry premium income reached <b>¥37.52 trillion</b> in FY2023,
      and the number of individual policies in force has risen for sixteen straight years. But that growth is shallow:
      <b>89% of households already hold cover</b>, the population has been shrinking for over a decade, and the birth
      rate is at a record low. When the pool of new customers is this thin, the economics shift. Each year roughly
      <b>5.9% of in-force benefits lapse or surrender</b>, and every policy that walks out the door takes future premium
      and embedded value with it. <b>Keeping the book is no longer a back-office concern; it is the main way the business
      grows.</b></p>
    <div class="bi-kpi-row" id="macroKpis"></div>
    <div class="split">
      <figure class="fig">
        <div class="cap-h">Individual policies in force (millions)</div>
        <div class="chart" id="cPolicies" style="height:240px"></div>
        <figcaption>Sixteen years of slow growth that is now flattening. Source: LIAJ Fact Book 2024.</figcaption>
      </figure>
      <figure class="fig">
        <div class="cap-h">The demographic backdrop</div>
        <table class="bi-table" style="margin-top:.4rem"><tbody id="demoRows"></tbody></table>
        <figcaption>An ageing, depopulating market pushes demand from death benefit toward medical, cancer and annuity
          cover, and makes the existing book disproportionately valuable.</figcaption>
      </figure>
    </div>
    <p>The book here is a typical Japanese in-force mix: whole-life, term and annuity policies sold through agents and
      bancassurance. These are <b>exactly the products where affordability- and rate-driven lapse bites hardest</b>,
      which is what makes a retention model worth building. The question becomes concrete: <b>which policies are about to
      leave, and why?</b></p>
  </section>

  <!-- 2. MODEL -------------------------------------------------------------->
  <section class="sec">
    <h2><span class="n">2</span>A model for who lapses, and why</h2>
    <p class="sec-meta">Gradient boosting vs a logistic challenger · {n_ph} policyholders</p>
    <p>I framed lapse as a yes/no prediction: for each policy, the probability it ends within the next twelve months. I
      trained a gradient-boosted tree model and, on purpose, a plain logistic regression next to it as an
      easy-to-explain benchmark. I scored both with <b>5-fold cross-validation</b>: train on 80% of the data, test on the
      held-out 20%, rotate five times and average, so the result is not a fluke of one split.</p>
    <p>I measured them with <b>AUC</b>, the standard ranking score: the chance the model gives a random lapser a higher
      risk than a random stayer (0.5 is a coin flip, 1.0 is perfect). The boosted model scored <b>{cv_gbm}</b> and the
      logistic <b>{cv_log}</b>. Comparing the two on the same folds (a paired test), the boosted model's <b>+{gap_v}</b>
      edge is statistically real (p = {gap_p}) but <b>practically negligible</b>: half a thousandth of AUC. So unless
      that sliver of ranking power is worth it, I would ship the <b>simpler, more transparent logistic model</b>, the
      kind a regulator is comfortable with. Knowing the difference between "significant" and "meaningful" is the point.</p>
    <p class="honesty"><b>How to read this 0.79.</b> Because the data is synthetic, the score measures how well the
      pipeline recovers a pattern I built in, not real-world lapse skill, and the same caveat applies to the drivers,
      SHAP, segments and ROI below: they show the method working on a known signal, not validated facts about real
      lapse. On a real book the code runs unchanged; the numbers would be lower. The point is the approach.</p>
    <div class="bi-kpi-row" id="modelKpis"></div>
    <figure class="fig">
      <div class="cap-h">What drives lapse</div>
      <div class="chart" id="cImp" style="height:340px"></div>
      <figcaption>Permutation importance: how much accuracy drops when each feature is scrambled. A bigger drop means
        the model leaned on it more. Bars average 30 repeats; the lines are ±1 standard deviation.</figcaption>
    </figure>
    <p>The top drivers match the actuarial literature. Some (tenure, channel, product) are structural and you cannot
      change them, but the most useful ones, <b>payment method, servicing gaps and recent complaints</b>, are
      <b>levers a retention team can actually pull</b>, not fixed traits like age:</p>
    <ul class="flow" id="driverNotes"></ul>
    <p>Permutation importance ranks features for the model as a whole. <b>SHAP</b> goes one step further and explains a
      <b>single policy</b>: how each of its attributes pushed that customer's risk above or below the average. Same cast
      of important features, now as a per-customer reason an agent can act on.</p>
    <div class="fig-2">
      <figure class="fig">
        <div class="cap-h">SHAP: global attribution</div>
        <div class="chart" id="cShapG" style="height:300px"></div>
        <figcaption>Mean absolute SHAP value per feature. It agrees with permutation importance on which features
          matter; the order differs because the two ask different questions (permutation: how much accuracy is lost;
          SHAP: average size of contribution, which can favour many-valued features like channel).</figcaption>
      </figure>
      <figure class="fig">
        <div class="cap-h">SHAP: one policyholder explained</div>
        <div class="chart" id="cShapL" style="height:300px"></div>
        <figcaption id="shapLocalNote"></figcaption>
      </figure>
    </div>
  </section>

  <!-- 3. PERFORMANCE -------------------------------------------------------->
  <section class="sec">
    <h2><span class="n">3</span>Does it rank, and is it calibrated?</h2>
    <p class="sec-meta">Held-out test set</p>
    <p>A retention model has to do two different jobs. It has to <b>rank</b> policies so that outreach goes to the ones
      most likely to leave, and its probabilities have to be <b>calibrated</b> so that "12% risk" really means about
      twelve in a hundred. Ranking pays for the campaign; calibration is what lets you trust the business case later.</p>
    <div class="fig-2">
      <figure class="fig">
        <div class="cap-h">ROC curve</div>
        <div class="chart" id="cRoc" style="height:300px"></div>
        <figcaption>The ROC curve traces how many real lapsers you catch (vertical) against the false alarms you accept
          (horizontal) as you loosen the threshold. The further above the diagonal, the better the ranking. Test AUC
          {auc} (boosted) vs {H['auc_logistic']:.3f} (logistic); the cross-validated number above is the one to trust.</figcaption>
      </figure>
      <figure class="fig">
        <div class="cap-h">Calibration</div>
        <div class="chart" id="cCal" style="height:300px"></div>
        <figcaption>Each dot is a group of policies: the risk the model predicted (horizontal) vs how many actually
          lapsed (vertical). On the diagonal means the predicted percentages are true percentages. (Brier {brier}; a
          guess-the-base-rate model would score about 0.068, so this is a real but modest gain.) This is what lets the
          scores feed a money calculation, not just a ranking.</figcaption>
      </figure>
    </div>
    <p>Because the scores rank well, <b>risk is concentrated</b>. Contacting the riskiest <b>20%</b> of the book reaches
      <b>{cap2} of all the lapses</b> that are going to happen, with a top-decile lift of <b>{d1_lift}×</b> over
      contacting people at random. That concentration is what makes targeted outreach economic instead of spraying the
      whole book.</p>
    <div class="fig-2">
      <figure class="fig">
        <div class="cap-h">Gains: lapses captured by depth of outreach</div>
        <div class="chart" id="cGains" style="height:280px"></div>
        <figcaption>Cumulative share of lapses reached as you contact more of the book in risk order. The shaded band is
          the top 20%.</figcaption>
      </figure>
      <figure class="fig">
        <div class="cap-h">Lapse rate by policy duration</div>
        <div class="chart" id="cSurv" style="height:280px"></div>
        <figcaption>Lapse is really a question of <i>when</i>, not just whether, which in production you would model as
          a survival (hazard) curve. This dataset only flags lapse over the next 12 months, so instead of faking a
          survival curve I show the honest version: the 12-month lapse rate by how long the policy has been held. It is
          highest early ({haz0} in year one) and falls as policies settle, the front-loaded pattern behind the 13- and
          25-month marks (the two points at which insurers conventionally check early persistency).</figcaption>
      </figure>
    </div>
    <p class="tbl-cap">Risk decile detail</p>
    <table class="bi-table">
      <thead><tr><th>Decile</th><th class="num">Policyholders</th><th class="num">Avg. predicted risk</th>
      <th class="num">Actual lapse rate</th><th class="num">Lift vs base</th><th class="num">Cum. lapses captured</th></tr></thead>
      <tbody id="liftRows"></tbody>
    </table>
  </section>

  <!-- 4. SEGMENTATION ------------------------------------------------------->
  <section class="sec">
    <h2><span class="n">4</span>Who are they? Segmenting the book</h2>
    <p class="sec-meta">k-means · 5 behavioural segments</p>
    <p>Ranking tells you <i>who</i> to call first. Segmentation tells you <i>what to say</i>. I used <b>k-means</b>, which
      groups customers so that each group is as internally similar as possible, on value and behaviour, and picked
      <b>five groups</b> so each gets one clear retention play. I am not claiming these are sharp natural clusters: the
      silhouette score (a 0-to-1 measure of how cleanly separated the groups are) is only {sil5:.2f}, so they overlap.
      Treat them as <b>management lenses, not hard boxes</b>. The one pattern that matters holds regardless: the
      highest-value group also churns above average, so the most valuable customers are the least safe.</p>
    <figure class="fig">
      <div class="cap-h">Value vs risk</div>
      <div class="chart" id="cSeg" style="height:460px"></div>
      <figcaption>Bubble size is segment size; the dashed line is the book-average lapse rate. The upper-right
        quadrant is the strategic problem: the highest-value segment also churns above average, so lifetime value is
        most exposed exactly where retention is weakest.</figcaption>
    </figure>
    <div class="seg-grid" id="segCards"></div>
  </section>

  <!-- 5. BUSINESS CASE ------------------------------------------------------>
  <section class="sec">
    <h2><span class="n">5</span>What is it worth?</h2>
    <p class="sec-meta">Targeted retention programme · illustrative book of ~1.2M policies</p>
    <p>A model only earns its keep if acting on it <b>beats the cost</b>. The logic: target the riskiest 20% (240,000
      policies, which hold 64% of expected lapses), spend ¥7,500 each on a save effort (auto-pay conversion, flexible
      terms, a service call), and assume that cuts their lapse rate by <b>20%</b> (an assumption, flagged as one). I
      credit value only on the policies that <b>would actually have lapsed</b>, valued at their <b>lifetime value</b>
      (CLV: roughly the future profit from that policy, discounted to today), so I am not counting the ~80% who were
      never going to leave. That nets ~11,000 policies saved and ¥3.3bn of value retained against ¥1.8bn spent, a
      <b>1.8× return</b> (net ¥1.5bn). The CLV here is illustrative gross margin, not a full embedded-value calculation
      and not netted for the surrender value a lapsing policy might pay, so read the yen as directional.</p>
    <ul class="flow" id="roiSteps"></ul>
    <div class="fig-2">
      <figure class="fig">
        <div class="cap-h">Value retained vs campaign cost (base case)</div>
        <div class="chart" id="cRoi" style="height:230px"></div>
        <div class="bi-kpi-row" id="roiKpis" style="margin-top:1.2rem"></div>
      </figure>
      <figure class="fig">
        <div class="cap-h">Sensitivity: net benefit (¥B)</div>
        <div class="chart" id="cSens" style="height:260px"></div>
        <figcaption>The base case is one cell, not a promise. Net benefit turns negative below a lapse reduction of
          {be_uplift} (break-even, at the base {cost_each} cost per policyholder). Green is positive, red is a loss.</figcaption>
      </figure>
    </div>
    <p>The honest reading is that this programme is <b>worth doing across a wide range of assumptions, but not all of
      them</b>. Presenting the sensitivity grid rather than a single ROI figure is the difference between a number a
      committee can challenge and one it has to take on faith.</p>
  </section>

  <!-- 6. FAIRNESS ----------------------------------------------------------->
  <section class="sec">
    <h2><span class="n">6</span>Does the targeting treat groups fairly?</h2>
    <p class="sec-meta">Selection rate and accuracy by age and income</p>
    <p>A retention flag decides who gets attention and who is left alone, so it is worth checking <b>whether it behaves
      evenly across groups</b> before anyone acts on it. I broke the flag down by age band and household income, comparing
      the actual lapse rate, the rate at which each group is flagged, and the model's accuracy within the group.</p>
    <figure class="fig">
      <div class="cap-h">By age band</div>
      <table class="bi-table" style="margin-top:.4rem"><thead><tr><th>Age</th><th class="num">N</th>
      <th class="num">Actual lapse</th><th class="num">Flagged rate</th><th class="num">AUC</th></tr></thead>
      <tbody id="fairAge"></tbody></table>
    </figure>
    <figure class="fig">
      <div class="cap-h">By household income</div>
      <table class="bi-table" style="margin-top:.4rem"><thead><tr><th>Income</th><th class="num">N</th>
      <th class="num">Actual lapse</th><th class="num">Flagged rate</th><th class="num">AUC</th></tr></thead>
      <tbody id="fairInc"></tbody></table>
    </figure>
    <p class="note" id="fairNote"></p>
  </section>

  <!-- 7. DELIVERY ----------------------------------------------------------->
  <section class="sec">
    <h2><span class="n">7</span>How it would actually ship</h2>
    <p class="sec-meta">Proposed production architecture, not yet built</p>
    <p>Everything above runs on a laptop. Making it useful in production means putting it on a schedule and into the
      hands of the people who talk to customers. To be clear about <b>what is built here versus what is a proposal</b>:
      the SHAP explanations and the fairness check above are <b>implemented</b>; the cloud and MLOps plumbing below is
      how I would productionise it, <b>not something I have stood up</b>.</p>
    <div class="fig-2">
      <figure class="fig">
        <div class="cap-h">Pipeline (proposed)</div>
        <ul class="flow">
          <li>Monthly scoring of the in-force book on a cloud ML platform, with features from policy, billing and servicing systems.</li>
          <li>Per-policy SHAP (built here) surfaced to retention teams so they see <i>why</i> a policy is flagged.</li>
          <li>Scores pushed to Power BI for agents and bancassurance partners; high risk crossed with high value triggers outreach.</li>
          <li>CI/CD and MLOps: versioned data, drift monitoring, predicted-vs-actual lapse calibration tracked every cycle.</li>
        </ul>
      </figure>
      <figure class="fig">
        <div class="cap-h">Limits and honesty</div>
        <ul class="flow">
          <li>Servicing notes, complaints and agent feedback in Japan are in <b>Japanese</b>; real features need JP-language NLP.</li>
          <li>Shock-driven lapses (job loss, illness, divorce) leave no advance signal and cap how much recall is ever possible.</li>
          <li>The logistic GLM stays alongside the boosted model as an interpretable, regulator-friendly challenger.</li>
          <li>The synthetic book validates the pipeline; the model would be re-fit and re-validated on real data before any decision.</li>
        </ul>
      </figure>
    </div>
  </section>

  <!-- METHOD + SOURCES ------------------------------------------------------>
  <section class="sec">
    <h2>Method and sources</h2>
    <p>{n_ph} synthetic policyholders were generated with a logistic lapse process whose coefficients encode the
      published direction of each driver (early-duration hazard, premium-to-income, payment method and frequency,
      channel, riders, complaints, servicing gap, age). Models:
      <span class="bi-mono">HistGradientBoostingClassifier</span> versus a <span class="bi-mono">LogisticRegression</span>
      challenger, compared by 5-fold stratified cross-validation; importances by permutation drop-in-AUC (30 repeats)
      and <span class="bi-mono">SHAP</span>; segmentation via <span class="bi-mono">k-means</span> (silhouette-checked);
      persistency from the empirical discrete-time hazard; lifetime value as the present value of profit margin
      (illustrative, not a decrement-based embedded-value calculation). Fully reproducible from
      <span class="bi-mono">build_model.py</span>.</p>
    <ul class="src" id="srcRows"></ul>
  </section>

  <!-- AUTHOR / PUBLISH ------------------------------------------------------>
  <footer class="author">
    <p class="name">Santiago Martínez</p>
    <p class="role">Data &amp; BI analyst. A self-directed case study on policyholder retention in the Japanese life market.</p>
    <p class="links">Portfolio <a href="https://santimuru.github.io">santimuru.github.io</a> &nbsp;·&nbsp;
      GitHub <a href="https://github.com/santimuru">github.com/santimuru</a></p>
    <p class="stack">Python · scikit-learn · ECharts. Policyholder data synthetic; market context cited above.</p>
  </footer>

</article>
<script>
{DATA_JS}
</script>
<script src="app.js"></script>
</body>
</html>"""

(HERE / "index.html").write_text(HTML, encoding="utf-8")
print("wrote index.html  (%d KB)" % (len((HERE/'index.html').read_text(encoding='utf-8'))//1024))
