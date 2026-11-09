"""Phase 9 - sampling bias and robustness.

1. Composition check: rake each year's professional respondents to the 2023 mix of country group x experience x
   age x company size, then recompute adoption and trust. If the trend survives, it is not just 'a different crowd'.
2. Robustness models: re-estimate the key associations under alternative samples, outcomes and estimators.
Usage:  python -m src.robustness
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import patsy
import statsmodels.api as sm
import statsmodels.formula.api as smf
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator
from scipy.stats import norm

from src import viz
from src.config import RESPONDENTS_PARQUET, TABLES
from src.models import CATS, DEMOGRAPHICS, FRUSTRATIONS, TASKS_2025, c, fit, prepare, pretty
from src.stats_utils import ordered_logit, rake, share_table

RAKE_VARS = ["country_group", "exp_bucket", "age_group", "org_size"]
KEY_TERMS = {
    "Year: 2025 (vs 2023)": "Trust fell over time (year 2025 vs 2023)",
    "Experience: 30+ yrs (vs 0-4 yrs)": "Experience 30+ yrs vs 0-4 yrs",
    "AI use frequency: Monthly or less (vs Daily)": "Uses AI monthly or less vs daily (2025)",
    "Frustration: debugging AI code takes longer": "'Debugging AI code takes longer' (2025)",
    "Frustration: 'almost right, but not quite'": "'Almost right, but not quite' (2025)",
}


# ------------------------------------------------------------------ 1. composition / raking
def raking_weights(full: pd.DataFrame) -> pd.Series:
    d = full[(full.is_professional == 1)].copy()
    for v in RAKE_VARS:
        d[v] = d[v].astype("object").fillna("Missing")
    base = d[d.survey_year == 2023]
    targets = {v: base[v].value_counts(normalize=True) for v in RAKE_VARS}
    w = pd.Series(1.0, index=d.index)
    for y in (2024, 2025):
        idx = d.survey_year == y
        w.loc[idx] = rake(d.loc[idx], targets).values
    return w


def reweighted_trend(full: pd.DataFrame, w: pd.Series) -> pd.DataFrame:
    d = full.loc[w.index].assign(rake_w=w)
    rows = []
    for label, weight in (("Unweighted", None), ("Reweighted to 2023 respondent mix", "rake_w")):
        a = share_table(d, ["survey_year"], "uses_ai", weight=weight).assign(metric="Adoption")
        t = share_table(d, ["survey_year"], "trusts_ai", base_mask=d.in_trust_base_users == 1, weight=weight).assign(metric="Trust")
        x = share_table(d, ["survey_year"], "distrusts_ai", base_mask=d.in_trust_base_users == 1, weight=weight).assign(metric="Distrust")
        rows.append(pd.concat([a, t, x]).assign(version=label))
    return pd.concat(rows, ignore_index=True)


def fig_reweighted(t: pd.DataFrame) -> None:
    colors = {"Adoption": viz.ADOPTION, "Trust": viz.TRUST, "Distrust": viz.DISTRUST}
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.3), sharey=True)
    for ax, (version, g) in zip(axes, t.groupby("version", sort=False)):
        ends = []
        for metric, s in g.groupby("metric", sort=False):
            ax.plot(s.survey_year, s.share, color=colors[metric], marker="o", markersize=7,
                    markeredgecolor=viz.SURFACE, markeredgewidth=2)
            ax.vlines(s.survey_year, s.ci_low, s.ci_high, color=colors[metric], linewidth=2, alpha=0.5)
            ends.append((s.share.iloc[-1], f"{metric} {s.share.iloc[-1]:.0%}"))
        viz.repel_labels(ax, [2025] * len(ends), [e[0] for e in ends], [e[1] for e in ends], min_dy=0.05,
                         x_span=1, dx=0.1, fontsize=9, color=viz.INK)
        ax.set_title(version, fontsize=10.5, pad=8)
        ax.set_xticks([2023, 2024, 2025])
        ax.set_xlim(2022.8, 2025.9)
        viz.pct_axis(ax, lim=(0, 1))
    fig.suptitle("The trend survives reweighting: it is not just a different crowd answering",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout()
    viz.footnote(fig, "Professional developers. 2024 and 2025 raked to the 2023 mix of country, years coding, age and company size "
                      "(weights trimmed to 0.2-5). Trust/distrust among current AI users. Bars = 95% CI using Kish effective n.")
    viz.save(fig, "fig15_reweighted_trend")


# ------------------------------------------------------------------ 2. robustness models
def key_rows(tab: pd.DataFrame, spec: str, n: int) -> list[dict]:
    rows = []
    for term, nice in KEY_TERMS.items():
        r = tab[tab.label == term]
        if len(r):
            r = r.iloc[0]
            rows.append(dict(spec=spec, key_term=nice, odds_ratio=r.odds_ratio, or_low=r.or_low, or_high=r.or_high,
                             p_value=r.p_value, n=n))
    return rows


def ordinal(formula_rhs: str, data: pd.DataFrame, outcome: str, spec: str) -> list[dict]:
    """Ordered logit on the 5-point scale, coded so that higher = MORE distrust (OR > 1 = more distrust)."""
    y = (6 - data[outcome]).astype(int)
    X = patsy.dmatrix(formula_rhs, data, return_type="dataframe").drop(columns="Intercept")
    res = ordered_logit(y.values, X.values)    # same estimator as statsmodels OrderedModel, analytic gradient
    b, se = res["params"], res["se"]
    tab = pd.DataFrame({"label": [pretty(t) for t in X.columns], "odds_ratio": np.exp(b),
                        "or_low": np.exp(b - 1.959964 * se), "or_high": np.exp(b + 1.959964 * se),
                        "p_value": 2 * norm.sf(np.abs(b / se))})
    return key_rows(tab, spec, res["nobs"])


def weighted_logit(formula: str, data: pd.DataFrame, weights: pd.Series, spec: str) -> list[dict]:
    res = smf.glm(formula, data=data, family=sm.families.Binomial(), var_weights=weights.loc[data.index]).fit(cov_type="HC1")
    ci = res.conf_int()
    tab = pd.DataFrame({"label": [pretty(t) for t in res.params.index], "odds_ratio": np.exp(res.params).values,
                        "or_low": np.exp(ci[0]).values, "or_high": np.exp(ci[1]).values, "p_value": res.pvalues.values})
    return key_rows(tab, spec, int(res.nobs))


def robustness_models(full: pd.DataFrame, w: pd.Series) -> pd.DataFrame:
    rows = []
    d = prepare()
    m1 = f"distrusts_ai ~ {c('survey_year')} + {DEMOGRAPHICS}"
    rhs1 = m1.split("~", 1)[1]

    _, t, s = fit(m1, d, "base")
    rows += key_rows(t, "A. Baseline: pooled logit, professional AI users", s["n"])
    rows += ordinal(rhs1, d, "trust_score", "B. Ordered logit on 5-point trust scale")
    _, t, s = fit(m1.replace("distrusts_ai", "highly_distrusts_ai"), d, "highly")
    rows += key_rows(t, "C. Outcome = 'highly distrust' only", s["n"])
    no_us = d[d.country_group != "United States"]
    _, t, s = fit(m1.replace(c("country_group"), "C(country_group, Treatment('Germany'))"), no_us, "no_us")
    rows += key_rows(t, "D. Excluding the United States", s["n"])
    cc = d[~d[CATS].isin(["Missing"]).any(axis=1)]
    _, t, s = fit(m1, cc, "complete")
    rows += key_rows(t, "E. Complete cases only (no 'Missing' categories)", s["n"])
    pro = d.assign(exp_bucket=d.pro_exp_bucket.astype("object").fillna("Missing"))
    _, t, s = fit(m1, pro, "pro_exp")
    rows += key_rows(t, "F. Professional experience instead of years coding", s["n"])
    wd = d.loc[d.index.intersection(w.index)]
    rows += weighted_logit(m1, wd, w, "G. Weighted to 2023 respondent mix")
    allc = full[(full.in_trust_base_users == 1)].copy()
    for col in CATS + ["ic_or_pm"]:
        allc[col] = allc[col].astype("object").fillna("Missing")
    _, t, s = fit(m1, allc, "all")
    rows += key_rows(t, "H. All respondents who use AI (not only professionals)", s["n"])

    # 2025 models
    d25 = d[(d.survey_year == 2025) & (d.answered_ai_tasks == 1) & (d.answered_frustration == 1)
            & d.ai_agents.notna() & d.ai_use_frequency.notna()]
    base25 = (f"distrusts_ai ~ {DEMOGRAPHICS} + {c('ic_or_pm')} + {c('ai_use_frequency')} + {c('ai_agents')} + "
              + " + ".join(f"task_{x}" for x in TASKS_2025))
    _, t, s = fit(base25 + " + " + " + ".join(f"frus_{f}" for f in FRUSTRATIONS), d25, "m2c")
    rows += key_rows(t, "K. 2025 baseline: model M2c (logit)", s["n"])
    _, t, s = fit(base25 + " + frus_almost_right", d25, "almost_only")
    rows += key_rows(t, "I. 2025: 'almost right' entered alone (no other frustrations)", s["n"])
    _, t, s = fit(f"distrusts_ai ~ {DEMOGRAPHICS} + frus_almost_right", d25, "almost_demog")
    rows += key_rows(t, "J. 2025: 'almost right' + demographics only", s["n"])
    rows += ordinal(base25.split("~", 1)[1] + " + " + " + ".join(f"frus_{f}" for f in FRUSTRATIONS), d25,
                    "trust_score", "L. 2025: model M2c as ordered logit (5-point scale)")
    return pd.DataFrame(rows)


def fig_robustness(r: pd.DataFrame) -> None:
    terms = list(KEY_TERMS.values())
    specs = sorted(r.spec.unique())
    fig, axes = plt.subplots(1, len(terms), figsize=(15, 0.36 * len(specs) + 2.2), sharey=True)
    for ax, term in zip(axes, terms):
        g = r[r.key_term == term].set_index("spec").reindex(specs)
        y = np.arange(len(specs))
        ok = g.odds_ratio.notna()
        sig = (g.p_value < 0.05) & ok
        col = np.where(g.odds_ratio > 1, viz.DISTRUST, viz.ADOPTION)
        col = np.where(sig, col, viz.NEUTRAL_GRAY)
        ax.hlines(y[ok], g.or_low[ok], g.or_high[ok], color=col[ok], linewidth=1.6)
        ax.scatter(g.odds_ratio[ok], y[ok], color=col[ok], s=30, zorder=3)
        for yi, v in zip(y[ok], g.odds_ratio[ok]):
            ax.text(v, yi + 0.3, f"{v:.2f}", ha="center", fontsize=7, color=viz.INK_2)
        ax.axvline(1, color=viz.AXIS, linewidth=1)
        ax.set_xscale("log")
        ax.xaxis.set_major_locator(FixedLocator([0.5, 1, 2, 4]))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        ax.xaxis.set_minor_locator(NullLocator())
        ax.set_xlim(0.4, 6)
        ax.set_title(term, fontsize=9, pad=6, loc="left", wrap=True)
        ax.grid(axis="y", visible=False)
        ax.set_yticks(y)
        ax.set_yticklabels(specs, fontsize=8)
        ax.invert_yaxis()
    axes[0].set_xlabel("Odds ratio for distrust")
    fig.suptitle("Key findings hold across every robustness check", x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout()
    viz.footnote(fig, "Each panel = one association; each row = one specification. Blank = term not in that specification. "
                      "Grey = not significant at 5%. Ordered logit coded so OR > 1 = more distrust.")
    viz.save(fig, "fig14_robustness")


def main() -> dict:
    viz.setup()
    full = pd.read_parquet(RESPONDENTS_PARQUET)
    w = raking_weights(full)
    trend = reweighted_trend(full, w)
    trend.to_csv(TABLES / "robustness_reweighted_trend.csv", index=False)
    fig_reweighted(trend)
    r = robustness_models(full, w)
    r.to_csv(TABLES / "robustness_models.csv", index=False)
    fig_robustness(r)
    print(trend.pivot_table(index=["metric", "survey_year"], columns="version", values="share").round(3).to_string())
    print(w.groupby(full.loc[w.index, "survey_year"]).describe().round(2).to_string())
    print(r.round(3).to_string())
    return dict(trend=trend, models=r)


if __name__ == "__main__":
    main()
