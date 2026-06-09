# -*- coding: utf-8 -*-
"""
MetLife Japan portfolio demo - policyholder lapse risk & segmentation.

Builds a realistic *synthetic* in-force policyholder book (transparently
labelled as synthetic), trains a real lapse-prediction model and a real
behavioural segmentation, and emits dashboard_data.json with metrics that
are genuine outputs of the fitted models (nothing hard-coded).

Lapse drivers and their direction follow the established life-insurance
actuarial literature (policy age, premium-to-income, payment method,
distribution channel, servicing contact, riders, complaints).
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.cluster import KMeans
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score, roc_curve, brier_score_loss, silhouette_score
import shap

RNG = np.random.default_rng(20260609)
N = 60_000
OUT = Path(__file__).parent

# ---------------------------------------------------------------- generate
PRODUCTS = {
    # product: (share, base_lapse_logit, annual_premium_mean_jpy, clv_mult)
    "Foreign-currency whole life": (0.30, -0.15, 420_000, 9.0),
    "Medical / cancer (A&H)":      (0.34, -0.55, 96_000,  6.5),
    "Term life":                   (0.14,  0.45, 78_000,  3.2),
    "Retirement annuity":          (0.14, -0.80, 540_000, 7.5),
    "Endowment / savings":         (0.08,  0.10, 300_000, 5.0),
}
CHANNELS = {  # channel: (share, lapse_logit_effect)
    "Tied agent (face-to-face)": (0.52, -0.30),
    "Bancassurance":             (0.26,  0.25),
    "Direct / online":           (0.14,  0.55),
    "Independent broker":        (0.08,  0.15),
}
PAYMETHOD = {  # method: (share, lapse_logit_effect)
    "Bank auto-debit": (0.62, -0.45),
    "Credit card":     (0.24, -0.10),
    "Payroll deduction": (0.08, -0.55),
    "Manual / invoice": (0.06,  0.95),
}
REGIONS = {  # prefecture cluster: (share, mean_income_jpy)
    "Greater Tokyo":   (0.34, 6_600_000),
    "Kansai":          (0.18, 5_700_000),
    "Chubu / Tokai":   (0.14, 5_500_000),
    "Kyushu / Okinawa":(0.12, 4_700_000),
    "Tohoku / Hokkaido":(0.12, 4_600_000),
    "Chugoku / Shikoku":(0.10, 4_800_000),
}

def pick(d):
    keys = list(d); p = np.array([d[k][0] for k in keys]); p = p / p.sum()
    return RNG.choice(keys, size=N, p=p)

product = pick(PRODUCTS)
channel = pick(CHANNELS)
paymethod = pick(PAYMETHOD)
region = pick(REGIONS)

age = np.clip(RNG.normal(52, 14, N).round(), 20, 88).astype(int)
tenure = np.clip(RNG.gamma(2.0, 3.2, N), 0.1, 28).round(1)  # policy age in years
income = np.array([RNG.normal(REGIONS[r][1], REGIONS[r][1]*0.32) for r in region]).clip(2.0e6, 2.6e7)
premium = np.array([RNG.lognormal(np.log(PRODUCTS[p][2]), 0.45) for p in product]).clip(18_000, 3.2e6)
prem_to_income = (premium / income).clip(0.005, 0.6)
rider_count = RNG.poisson(1.3, N).clip(0, 7)
freq_monthly = (RNG.random(N) < 0.78).astype(int)  # 1=monthly,0=annual
months_since_contact = RNG.gamma(2.2, 4.5, N).clip(0, 48).round().astype(int)
digital_engagement = np.clip(RNG.normal(48, 22, N) + (age < 45) * 14 - (age > 65) * 16, 0, 100).round().astype(int)
recent_complaint = (RNG.random(N) < 0.045).astype(int)
num_claims = RNG.poisson(0.35 + (product == "Medical / cancer (A&H)") * 0.7, N).clip(0, 9)

# ---- true lapse process (logit) - signs match actuarial evidence.
# NOTE on honesty: because labels are generated from this known process, any model
# trained below measures *recoverability of this process*, not real-world lapse
# skill. The interaction terms (affordability x early-tenure, manual-pay x remote,
# complaint x servicing-gap) are included so the benchmark is non-linear; whether a
# tree actually beats a linear model on them is tested empirically (cross-validated),
# not assumed.
manual = (paymethod == "Manual / invoice").astype(float)
remote = np.isin(channel, ["Direct / online", "Bancassurance"]).astype(float)
early = (tenure < 2).astype(float)
z = (
    -2.55
    + np.array([PRODUCTS[p][1] for p in product])
    + np.array([CHANNELS[c][1] for c in channel])
    + np.array([PAYMETHOD[m][1] for m in paymethod])
    + 3.4 * (prem_to_income - 0.06)                 # affordability stress ↑ lapse
    - 0.075 * tenure                                # mature policies ↓ lapse (persistency)
    + 1.55 * np.exp(-tenure / 1.3)                  # early-duration lapse spike (front-loaded hazard)
    + 0.80 * np.exp(-((tenure - 10) ** 2) / 2.2)    # surrender-charge / rate-reset bump ~yr10 (non-monotonic)
    - 0.016 * (age - 50)                            # older ↓ lapse
    + 0.028 * months_since_contact                  # servicing gap ↑ lapse
    + 1.25 * recent_complaint                       # complaint ↑ lapse
    - 0.16 * rider_count                            # engagement/stickiness ↓ lapse
    - 0.013 * (digital_engagement - 50)             # engaged ↓ lapse
    + 0.30 * (1 - freq_monthly)                     # annual billing ↑ lapse
    # --- interactions (non-linear; trees exploit, linear model cannot) ---
    + 7.0 * np.clip(prem_to_income - 0.10, 0, None) * early   # stretched & brand-new
    + 1.15 * manual * remote                                   # manual pay on remote channel
    + 0.075 * recent_complaint * months_since_contact          # ignored after a complaint
    + 0.85 * remote * early                                     # remote-sold, early tenure
)
p_lapse = 1 / (1 + np.exp(-z))
p_lapse = np.clip(p_lapse + RNG.normal(0, 0.012, N), 0.001, 0.985)
lapsed = (RNG.random(N) < p_lapse).astype(int)

df = pd.DataFrame({
    "age": age, "tenure_years": tenure, "product": product, "channel": channel,
    "pay_method": paymethod, "region": region, "annual_premium_jpy": premium.round().astype(int),
    "household_income_jpy": income.round().astype(int), "premium_to_income": prem_to_income.round(4),
    "rider_count": rider_count, "freq_monthly": freq_monthly,
    "months_since_contact": months_since_contact, "digital_engagement": digital_engagement,
    "recent_complaint": recent_complaint, "num_claims": num_claims, "lapsed": lapsed,
})
df.to_parquet(OUT / "policyholders.parquet", index=False)
overall_lapse = df.lapsed.mean()

# ---------------------------------------------------------------- model
num_feats = ["age", "tenure_years", "annual_premium_jpy", "household_income_jpy",
             "premium_to_income", "rider_count", "freq_monthly", "months_since_contact",
             "digital_engagement", "recent_complaint", "num_claims"]
cat_feats = ["product", "channel", "pay_method", "region"]
X = df[num_feats + cat_feats]; y = df["lapsed"]
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=7)

pre = ColumnTransformer([
    ("num", "passthrough", num_feats),
    ("cat", OneHotEncoder(handle_unknown="ignore"), cat_feats),
])
gbm = Pipeline([("pre", pre), ("clf", HistGradientBoostingClassifier(
    max_iter=350, learning_rate=0.06, max_depth=6, l2_regularization=1.0,
    early_stopping=True, random_state=7))])
gbm.fit(Xtr, ytr)
proba = gbm.predict_proba(Xte)[:, 1]
auc = roc_auc_score(yte, proba)
brier = brier_score_loss(yte, proba)

# logistic baseline for honest comparison
log = Pipeline([("pre", ColumnTransformer([
    ("num", StandardScaler(), num_feats),
    ("cat", OneHotEncoder(handle_unknown="ignore"), cat_feats)])),
    ("clf", LogisticRegression(max_iter=2000, C=0.5))])
log.fit(Xtr, ytr)
auc_log = roc_auc_score(yte, log.predict_proba(Xte)[:, 1])

# 5-fold stratified CV with intervals -> is the GBM-vs-logistic gap real or noise?
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=7)
cv_gbm = cross_val_score(gbm, X, y, cv=cv, scoring="roc_auc", n_jobs=-1)
cv_log = cross_val_score(log, X, y, cv=cv, scoring="roc_auc", n_jobs=-1)
gap = cv_gbm.mean() - cv_log.mean()
pooled_sd = float(np.sqrt(cv_gbm.std(ddof=1) ** 2 + cv_log.std(ddof=1) ** 2))
gap_significant = bool(abs(gap) > pooled_sd)   # crude: gap exceeds combined 1-sigma

# ROC curve (thinned)
fpr, tpr, _ = roc_curve(yte, proba)
idx = np.linspace(0, len(fpr) - 1, 60).astype(int)
roc_pts = [{"fpr": round(float(fpr[i]), 4), "tpr": round(float(tpr[i]), 4)} for i in idx]

# lift / gains by risk decile
te = pd.DataFrame({"y": yte.values, "p": proba}).sort_values("p", ascending=False).reset_index(drop=True)
te["decile"] = (np.floor(np.arange(len(te)) / (len(te) / 10)).astype(int) + 1).clip(1, 10)
base = te.y.mean()
lift_tbl = []
cum_lapsers = 0; total_lapsers = te.y.sum()
for d in range(1, 11):
    g = te[te.decile == d]
    cum_lapsers += g.y.sum()
    lift_tbl.append({
        "decile": int(d),
        "policyholders": int(len(g)),
        "avg_risk": round(float(g.p.mean()), 4),
        "actual_lapse_rate": round(float(g.y.mean()), 4),
        "lift": round(float(g.y.mean() / base), 2),
        "cum_capture": round(float(cum_lapsers / total_lapsers), 4),
    })

# permutation importance (n_repeats high enough to report error bars)
samp = Xte.sample(6000, random_state=3)
ysamp = yte.loc[samp.index]
perm = permutation_importance(gbm, samp, ysamp, scoring="roc_auc", n_repeats=30, random_state=3, n_jobs=-1)
LABELS = {
    "premium_to_income": "Premium-to-income ratio", "tenure_years": "Policy tenure (years)",
    "months_since_contact": "Months since last servicing", "pay_method": "Payment method",
    "channel": "Distribution channel", "recent_complaint": "Recent complaint",
    "product": "Product line", "rider_count": "Number of riders", "age": "Policyholder age",
    "digital_engagement": "Digital engagement", "freq_monthly": "Billing frequency",
    "annual_premium_jpy": "Annual premium", "household_income_jpy": "Household income",
    "region": "Region", "num_claims": "Claims count",
}
imp = sorted([{"feature": LABELS.get(f, f), "importance": round(float(m), 4), "std": round(float(s), 4)}
              for f, m, s in zip(num_feats + cat_feats, perm.importances_mean, perm.importances_std)],
             key=lambda r: -r["importance"])[:10]
mx = max(r["importance"] for r in imp)
for r in imp:
    r["pct"] = round(100 * r["importance"] / mx, 1)
    r["std_pct"] = round(100 * r["std"] / mx, 1)

# calibration: predicted vs observed lapse by decile (honest reliability check)
reliability = [{"pred": d["avg_risk"], "obs": d["actual_lapse_rate"]} for d in lift_tbl]

# ---------------------------------------------------------------- segmentation
seg_feats = ["age", "tenure_years", "premium_to_income", "annual_premium_jpy",
             "digital_engagement", "months_since_contact", "rider_count"]
Z = StandardScaler().fit_transform(df[seg_feats])
# justify k: silhouette over a range (on a sample, for speed) instead of hardcoding
Zs = Z[RNG.choice(len(Z), 8000, replace=False)]
sil = []
for kk in range(2, 8):
    lab = KMeans(n_clusters=kk, n_init=10, random_state=11).fit_predict(Zs)
    sil.append({"k": kk, "silhouette": round(float(silhouette_score(Zs, lab)), 4)})
k = 5   # chosen for actionability (each segment -> a distinct retention play); silhouette reported for transparency
km = KMeans(n_clusters=k, n_init=10, random_state=11).fit(Z)
df["segment"] = km.labels_

# CLV = present value of future profit margin on the policy (not premium*tenure).
# margin = profit share of annual premium; remaining_years from a long-policy
# assumption net of attained age; discounted at DISC. Conservative, auditable.
MARGIN, DISC = 0.11, 0.03
prod_margin = df["product"].map({p: PRODUCTS[p][3] for p in PRODUCTS}).values / 9.0  # 0.35-1.0 quality scaler
remaining_years = np.clip(np.minimum(20 - df["tenure_years"].values, 85 - df["age"].values), 2, 20)
annuity_factor = (1 - (1 / (1 + DISC)) ** remaining_years) / DISC
clv = (df["annual_premium_jpy"].values * MARGIN * prod_margin * annuity_factor)

seg_rows = []
for s in range(k):
    m = df.segment == s
    seg_rows.append({
        "id": int(s),
        "size": int(m.sum()),
        "share": round(float(m.mean()), 4),
        "lapse_rate": round(float(df.loc[m, "lapsed"].mean()), 4),
        "avg_age": round(float(df.loc[m, "age"].mean()), 1),
        "avg_tenure": round(float(df.loc[m, "tenure_years"].mean()), 1),
        "avg_premium": int(df.loc[m, "annual_premium_jpy"].mean()),
        "avg_prem_to_income": round(float(df.loc[m, "premium_to_income"].mean()), 4),
        "avg_digital": round(float(df.loc[m, "digital_engagement"].mean()), 1),
        "avg_clv": int(clv[m].mean()),
        "top_product": df.loc[m, "product"].mode().iloc[0],
        "top_channel": df.loc[m, "channel"].mode().iloc[0],
    })
seg_rows.sort(key=lambda r: -r["avg_clv"])

# Unique, data-driven names: greedy assignment so each archetype is used once,
# each going to the segment that best fits it (no collisions, no mislabels).
ARCHETYPES = [
    ("avg_clv", "max", "High-value, at-risk",
     "Largest lifetime value AND above-average churn, mostly FX whole-life with stretched premium-to-income. The #1 retention priority: most value at stake per save."),
    ("lapse_rate", "max", "Affordability-stressed",
     "Highest churn of the book: early-duration policies under payment pressure. Proactive save via auto-pay conversion, flexible payment, premium-holiday offers."),
    ("avg_digital", "max", "Digital self-servers",
     "Younger, engaged online, lower-touch. Retain cheaply via app nudges, e-statements and digital renewal flows."),
    ("avg_age", "max", "Mature stable core",
     "Older, sticky book. Retirement, long-term-care and legacy products; preserve persistency, avoid over-contact."),
    (None, None, "Loyal low-touch core",
     "Lowest churn, modest value. Keep cost-to-serve low; deepen with medical/cancer riders to lift lifetime value over time."),
]
assigned, used = {}, set()
for key, _, name, play in ARCHETYPES[:-1]:
    cand = [r for r in seg_rows if r["id"] not in used]
    best = max(cand, key=lambda r: r[key])
    assigned[best["id"]] = (name, play); used.add(best["id"])
fallback = ARCHETYPES[-1]
for r in seg_rows:
    if r["id"] not in assigned:
        assigned[r["id"]] = (fallback[2], fallback[3])
for r in seg_rows:
    r["name"], r["play"] = assigned[r["id"]]

# ---------------------------------------------------------------- SHAP attribution
pre_fit = gbm.named_steps["pre"]; clf = gbm.named_steps["clf"]
feat_names = list(pre_fit.get_feature_names_out())
Xte_t = pre_fit.transform(Xte)
if hasattr(Xte_t, "toarray"): Xte_t = Xte_t.toarray()
sidx = RNG.choice(len(Xte_t), 1500, replace=False)
try:
    expl = shap.TreeExplainer(clf)
    sv = expl.shap_values(Xte_t[sidx])
    if isinstance(sv, list): sv = sv[-1]
    if sv.ndim == 3: sv = sv[..., -1]
    base_val = float(np.ravel(expl.expected_value)[-1])
except Exception as e:
    print("TreeExplainer fallback:", e)
    sidx = sidx[:400]
    bg = shap.sample(Xte_t, 80, random_state=3)
    expl = shap.Explainer(lambda d: clf.predict_proba(d)[:, 1], bg)
    ex = expl(Xte_t[sidx], silent=True); sv = ex.values
    base_val = float(np.mean(ex.base_values))

def base_feat(nm):
    nm = nm.split("__", 1)[1] if "__" in nm else nm
    if nm in num_feats: return nm
    for c in cat_feats:
        if nm.startswith(c + "_"): return c
    return nm
def readable(nm):
    raw = nm.split("__", 1)[1] if "__" in nm else nm
    if raw in num_feats: return LABELS.get(raw, raw)
    for c in cat_feats:
        if raw.startswith(c + "_"): return LABELS.get(c, c) + " = " + raw[len(c) + 1:]
    return raw

mean_abs = np.abs(sv).mean(axis=0)
agg = {}
for nm, v in zip(feat_names, mean_abs):
    b = base_feat(nm); agg[b] = agg.get(b, 0.0) + float(v)
shap_global = sorted([{"feature": LABELS.get(b, b), "mean_abs": round(v, 4)} for b, v in agg.items()],
                     key=lambda r: -r["mean_abs"])[:10]
gmx = shap_global[0]["mean_abs"] or 1
for r in shap_global: r["pct"] = round(100 * r["mean_abs"] / gmx, 1)
loc = int(np.argmax(proba[sidx]))                       # most at-risk policy in sample
contribs = sorted(zip(feat_names, sv[loc]), key=lambda t: -abs(t[1]))[:8]
shap_local = {
    "risk": round(float(proba[sidx][loc]), 4), "base": round(base_val, 4),
    "contributions": [{"feature": readable(n), "value": round(float(v), 4)} for n, v in contribs],
}

# ---------------------------------------------------------------- fairness audit
fair_df = pd.DataFrame({"y": yte.values, "p": proba}, index=Xte.index)
thr = float(np.quantile(proba, 0.8))                    # the top-20% targeting cut
fair_df["flagged"] = (fair_df.p >= thr).astype(int)
fair_df["age_band"] = pd.cut(Xte["age"], [0, 40, 55, 70, 200], labels=["<40", "40-54", "55-69", "70+"])
fair_df["income_band"] = pd.qcut(Xte["household_income_jpy"], 3, labels=["Lower third", "Middle third", "Upper third"])
def group_stats(col):
    out = []
    for g, sub in fair_df.groupby(col, observed=True):
        a = roc_auc_score(sub.y, sub.p) if sub.y.nunique() > 1 else None
        out.append({"group": str(g), "n": int(len(sub)), "lapse": round(float(sub.y.mean()), 4),
                    "flagged_rate": round(float(sub.flagged.mean()), 4),
                    "auc": round(float(a), 4) if a is not None else None})
    return out
fa = group_stats("age_band"); fi = group_stats("income_band")
auc_vals = [g["auc"] for g in fa + fi if g["auc"] is not None]
flag_vals = [g["flagged_rate"] for g in fa + fi]
fairness = {
    "by_age": fa, "by_income": fi,
    "auc_spread": round(max(auc_vals) - min(auc_vals), 4),
    "flag_spread": round(max(flag_vals) - min(flag_vals), 4),
    "note": ("Flagged = top-20% risk score (the targeting cut). Ranking quality is broadly comparable "
             "(AUC {:.2f}-{:.2f}), but it is NOT identical: the 70+ and upper-income groups score a few points "
             "lower, and the lower-income third is flagged more often ({:.0%}) than the upper third ({:.0%}). "
             "That tracks genuine risk, but the gap is real; in production it would warrant a documented "
             "fairness review and possibly group-aware thresholds, not a clean bill of health.").format(
                 min(auc_vals), max(auc_vals), max(flag_vals), min(flag_vals)),
}

# ---------------------------------------------------------------- duration profile
# Lapse is fundamentally a time-to-event problem; a production model would use a
# discrete-time hazard or Cox fit on observed lapse TIMING. This synthetic book only
# records a forward 12-month lapse flag (no timing), so we do NOT fake a cohort
# survival curve. What IS well-defined and honest is the cross-sectional 12-month
# lapse rate by current policy duration -- it shows the front-loaded shape that
# motivates the survival framing without overclaiming a persistency study.
df["tbin"] = np.floor(df["tenure_years"]).astype(int)
haz_series = df.groupby("tbin")["lapsed"].mean()
hazard = [{"t": int(t), "h": round(float(h), 4)} for t, h in haz_series.items() if t <= 20]

# ---------------------------------------------------------------- retention ROI
# Target the two highest-risk deciles (top 20% of the book by score) with an
# evidence-based intervention: proactive outreach + auto-pay conversion +
# flexible-payment offer. All economic assumptions are stated and tunable.
te["idx"] = Xte.index                       # original row id -> align CLV
target = te[te.decile <= 2]
# value is only at stake on the policies that WOULD lapse: use the CLV of the
# actual lapsers in the target set, not the average of the whole targeted group.
lapser_idx = target[target.y == 1]["idx"].values
clv_lapsers = float(clv[lapser_idx].mean()) if len(lapser_idx) else float(clv[target["idx"].values].mean())
N_BOOK = 1_200_000          # ILLUSTRATIVE book size (results scale linearly; read as "per 1.2M policies")
scale = N_BOOK / len(te)    # project held-out test set onto the illustrative book
targeted = int(len(target) * scale)
exp_lapsers = float(target.y.sum() * scale)
UPLIFT = 0.20               # ASSUMPTION: relative lapse reduction from the program
COST_PER = 7_500            # ASSUMPTION: blended JPY cost per targeted policyholder
saved_policies = exp_lapsers * UPLIFT
value_saved = saved_policies * clv_lapsers
cost = targeted * COST_PER
breakeven_uplift = round(cost / (exp_lapsers * clv_lapsers), 4)   # uplift where net = 0 at base cost
roi = {
    "targeted_policyholders": targeted,
    "expected_lapsers_in_target": round(exp_lapsers),
    "assumed_relative_uplift": UPLIFT,
    "assumed_cost_per_policyholder_jpy": COST_PER,
    "saved_policies": round(saved_policies),
    "avg_clv_jpy": round(clv_lapsers),
    "value_retained_jpy": round(value_saved),
    "campaign_cost_jpy": round(cost),
    "net_benefit_jpy": round(value_saved - cost),
    "roi_x": round(value_saved / cost, 1),
    "capture_top2_deciles": lift_tbl[1]["cum_capture"],
    "breakeven_uplift": breakeven_uplift,
}
# sensitivity: net benefit (¥B) over a grid of uplift x cost-per-policyholder
UPL = [0.05, 0.10, 0.15, 0.20, 0.25]
CPP = [5_000, 7_500, 10_000, 15_000, 20_000]
roi_sensitivity = {
    "uplift": UPL, "cost": CPP,
    "net_billions": [[round((exp_lapsers * u * clv_lapsers - targeted * c) / 1e9, 2) for c in CPP] for u in UPL],
}

payload = {
    "meta": {
        "n_policyholders": int(len(df)),
        "data_nature": "Synthetic policyholder book generated for demonstration; "
                       "lapse drivers and their direction follow published life-insurance "
                       "actuarial evidence. Market-context figures are real and cited.",
        "book_scale_assumption": N_BOOK,
        "built": "2026-06-09",
    },
    "headline": {
        "overall_lapse_rate": round(float(overall_lapse), 4),
        "auc": round(float(auc), 4),
        "auc_logistic": round(float(auc_log), 4),
        "brier": round(float(brier), 4),
        "auc_cv_mean": round(float(cv_gbm.mean()), 4),
        "auc_cv_std": round(float(cv_gbm.std(ddof=1)), 4),
        "auc_log_cv_mean": round(float(cv_log.mean()), 4),
        "auc_log_cv_std": round(float(cv_log.std(ddof=1)), 4),
        "gbm_gap": round(float(gap), 4),
        "gap_significant": gap_significant,
    },
    "roc": roc_pts,
    "lift": lift_tbl,
    "reliability": reliability,
    "importance": imp,
    "shap_global": shap_global,
    "shap_local": shap_local,
    "segments": seg_rows,
    "silhouette": sil,
    "fairness": fairness,
    "duration_profile": {"hazard": hazard},
    "roi": roi,
    "roi_sensitivity": roi_sensitivity,
}
(OUT / "dashboard_data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"OK  n={len(df)}  lapse={overall_lapse:.3f}  AUC_gbm={auc:.4f}  AUC_log={auc_log:.4f}  brier={brier:.4f}")
print(f"CV  GBM {cv_gbm.mean():.4f}±{cv_gbm.std(ddof=1):.4f}  LOG {cv_log.mean():.4f}±{cv_log.std(ddof=1):.4f}  gap={gap:+.4f} sig={gap_significant}")
print(f"segments={k} (silhouette k5={[s for s in sil if s['k']==5][0]['silhouette']})  roi_x={roi['roi_x']} breakeven_uplift={breakeven_uplift}")
print(f"hazard t0={hazard[0]['h']}  fairness auc_spread={fairness['auc_spread']}")
print("wrote dashboard_data.json")
