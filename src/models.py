"""Phase 8 - what is associated with distrust? Logistic regression with controls.

Outcome: distrusts_ai = 1 if 'Somewhat' or 'Highly' distrust the accuracy of AI output (else 0, neutral included).
Sample: professional developers who currently use AI and answered the trust question.
SEs are heteroskedasticity-robust (HC1). Results are associations, not causal effects.

Models
  M1   pooled 2023-2025: year + experience + role + company size + country + age
  M1b  M1 + the 8 task types offered in all three years (respondents who answered the task question)
  M2a  2025: demographics (+ IC / manager)                                     } same sample
  M2b  M2a + AI use frequency + AI agents + 13 task types                       } for all three
  M2c  M2b + 2025 frustrations ('almost right', 'debugging slower', ...)        } steps
Usage:  python -m src.models
"""
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

from src import viz
from src.config import RESPONDENTS_PARQUET, TABLES

REF = {"survey_year": 2023, "exp_bucket": "0-4 yrs", "role_family": "Full-stack dev", "org_size": "4 100-999",
       "country_group": "United States", "age_group": "25-34", "ic_or_pm": "Individual contributor",
       "ai_use_frequency": "Daily", "ai_agents": "No agents"}
CATS = ["exp_bucket", "role_family", "org_size", "country_group", "age_group"]
TASKS_ALL_YEARS = ["writing_code", "debugging", "documenting_code", "learning_codebase", "testing_code",
                   "project_planning", "code_review", "deployment"]
TASKS_2025 = TASKS_ALL_YEARS + ["search_answers", "content_generation", "predictive_analytics",
                                "learning_new_tech", "maintaining_docs"]
FRUSTRATIONS = ["almost_right", "debugging_slower", "less_confident", "hard_to_understand", "no_problems"]


def c(var: str) -> str:
    ref = REF[var]
    ref = ref if isinstance(ref, int) else f"'{ref}'"
    return f"C({var}, Treatment({ref}))"


DEMOGRAPHICS = " + ".join(c(v) for v in CATS)


def prepare() -> pd.DataFrame:
    df = pd.read_parquet(RESPONDENTS_PARQUET)
    d = df[(df.is_professional == 1) & (df.in_trust_base_users == 1)].copy()
    for col in CATS + ["ic_or_pm"]:
        d[col] = d[col].astype("object").fillna("Missing")
    d = d[d.role_family != "Student"]   # 'Student' as a DevType among professional developers is too ambiguous
    return d


def fit(formula: str, data: pd.DataFrame, name: str):
    res = smf.logit(formula, data=data).fit(disp=0, maxiter=300, cov_type="HC1")
    me = res.get_margeff(at="overall", dummy=True).summary_frame()
    ci = res.conf_int()
    tab = pd.DataFrame({
        "term": res.params.index, "coef": res.params.values, "odds_ratio": np.exp(res.params.values),
        "or_low": np.exp(ci[0].values), "or_high": np.exp(ci[1].values), "p_value": res.pvalues.values,
    }).set_index("term")
    tab["ame_pp"] = me["dy/dx"] * 100
    tab["ame_low_pp"] = me["Conf. Int. Low"] * 100
    tab["ame_high_pp"] = me["Cont. Int. Hi."] * 100
    tab = tab.reset_index()
    tab.insert(0, "model", name)
    tab["label"] = tab.term.map(pretty)
    fit_stats = dict(model=name, n=int(res.nobs), events=int(data.loc[res.model.data.row_labels, "distrusts_ai"].sum()),
                     pseudo_r2=res.prsquared, aic=res.aic, n_params=len(res.params),
                     dropped_rows=len(data) - int(res.nobs))
    return res, tab, fit_stats


def pretty(term: str) -> str:
    if term == "Intercept":
        return "Intercept"
    m = re.match(r"C\((\w+), Treatment\((.+?)\)\)\[T\.(.+)\]", term)
    if m:
        var, ref, lvl = m.groups()
        names = {"survey_year": "Year", "exp_bucket": "Experience", "role_family": "Role", "org_size": "Company size",
                 "country_group": "Country", "age_group": "Age", "ic_or_pm": "Position",
                 "ai_use_frequency": "AI use frequency", "ai_agents": "AI agents"}
        lvl = re.sub(r"^\d ", "", lvl)
        ref = re.sub(r"^\d ", "", ref.strip("'"))
        return f"{names.get(var, var)}: {lvl} (vs {ref})"
    if term.startswith("task_"):
        return "Uses AI for: " + term.removeprefix("task_").replace("_", " ")
    if term.startswith("frus_"):
        return "Frustration: " + {"almost_right": "'almost right, but not quite'",
                                  "debugging_slower": "debugging AI code takes longer",
                                  "less_confident": "less confident in own problem-solving",
                                  "hard_to_understand": "hard to understand the code",
                                  "no_problems": "no problems encountered"}.get(term[5:], term[5:])
    return term


def block(label: str) -> str:
    for k in ("Year", "Experience", "Role", "Company size", "Country", "Age", "Position", "AI use frequency",
              "AI agents", "Uses AI for", "Frustration"):
        if label.startswith(k):
            return k
    return "Other"


# ------------------------------------------------------------------ figures
def forest(tab: pd.DataFrame, name: str, title: str, sub: str, blocks: list[str]) -> None:
    t = tab[tab.label.map(block).isin(blocks) & ~tab.label.str.contains("Missing")].copy()
    t["block"] = t.label.map(block)
    t["block"] = pd.Categorical(t.block, blocks, ordered=True)
    t = t.sort_values(["block", "odds_ratio"], ascending=[False, True])
    y = np.arange(len(t))
    fig, ax = plt.subplots(figsize=(9, 0.28 * len(t) + 1.8))
    sig = t.p_value < 0.05
    colors = np.where(t.odds_ratio > 1, viz.DISTRUST, viz.ADOPTION)
    ax.hlines(y, t.or_low, t.or_high, color=np.where(sig, colors, viz.NEUTRAL_GRAY), linewidth=1.6)
    ax.scatter(t.odds_ratio, y, color=np.where(sig, colors, viz.NEUTRAL_GRAY), s=34, zorder=3,
               edgecolor=viz.SURFACE, linewidth=1)
    ax.axvline(1, color=viz.AXIS, linewidth=1)
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(FixedLocator([0.25, 0.5, 1, 2, 4]))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xlim(min(0.2, t.or_low.min() * 0.9), max(4.5, t.or_high.max() * 1.1))
    ax.set_yticks(y)
    ax.set_yticklabels(t.label.str.replace(r" \(vs .*\)$", "", regex=True), fontsize=8)
    ax.set_ylim(-0.7, len(t) - 0.3)
    ax.grid(axis="y", visible=False)
    # block separators
    for b in t.block.unique():
        idx = np.where(t.block.values == b)[0]
        ax.axhline(idx.max() + 0.5, color=viz.GRID, linewidth=0.8)
    ax.set_xlabel("Odds ratio for distrusting AI (log scale) - right of 1 = more distrust, left = less")
    ax.set_title(title)
    viz.subtitle(ax, sub)
    fig.tight_layout()
    strip_num = re.compile(r"^\d ")
    refs = ", ".join(f"{k.replace('_', ' ')} = {strip_num.sub('', str(v))}" for k, v in REF.items())
    viz.footnote(fig, f"Reference levels: {refs}. Grey = not significant at 5%. Robust (HC1) 95% CIs. "
                      "Associations only. Source: Stack Overflow Developer Survey (ODbL).")
    viz.save(fig, name)


def fig_stepwise(tabs: dict[str, pd.DataFrame]) -> None:
    rows = []
    for m, t in tabs.items():
        e = t[t.label.str.startswith("Experience:") & ~t.label.str.contains("Missing")]
        for _, r in e.iterrows():
            rows.append(dict(model=m, level=r.label.split(":")[1].split("(")[0].strip(), ame=r.ame_pp,
                             lo=r.ame_low_pp, hi=r.ame_high_pp))
    s = pd.DataFrame(rows)
    levels = ["5-9 yrs", "10-19 yrs", "20-29 yrs", "30+ yrs"]
    models = list(tabs)
    labels = {"M2a": "Demographics only", "M2b": "+ use frequency, agents, task types", "M2c": "+ frustrations"}
    shades = ["#86b6ef", "#2a78d6", "#104281"]
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    x = np.arange(len(levels))
    w = 0.26
    for i, m in enumerate(models):
        v = s[s.model == m].set_index("level").reindex(levels)
        ax.bar(x + (i - 1) * (w + 0.01), v.ame, width=w, color=shades[i], label=labels[m])
        ax.errorbar(x + (i - 1) * (w + 0.01), v.ame, yerr=[v.ame - v.lo, v.hi - v.ame], fmt="none",
                    ecolor=viz.INK_2, elinewidth=0.8)
        for xi, val, hi in zip(x + (i - 1) * (w + 0.01), v.ame, v.hi):
            ax.text(xi, hi + 0.6, f"{val:+.0f}", ha="center", fontsize=8, color=viz.INK_2)
    ax.axhline(0, color=viz.AXIS, linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{l}\n(vs 0-4 yrs)" for l in levels], fontsize=9)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Change in probability of distrust (pp)")
    viz.legend_above(ax, ncol=3)
    ax.set_title("Experience still predicts distrust after controlling for how AI is used")
    viz.subtitle(ax, "Average marginal effect of experience on distrust, 2025, three nested models on the same sample",
                 legend_row=True)
    fig.tight_layout()
    viz.footnote(fig, "Professional developers who use AI (2025). Bars = robust 95% CIs. If use patterns and frustrations "
                      "explained the experience gap, the bars would shrink toward 0 from left to right.")
    viz.save(fig, "fig13_experience_effect_stepwise")


def main() -> dict:
    viz.setup()
    d = prepare()
    out_tabs, stats = [], []

    m1_formula = f"distrusts_ai ~ {c('survey_year')} + {DEMOGRAPHICS}"
    _, t1, s1 = fit(m1_formula, d, "M1 pooled")
    d1b = d[d.answered_ai_tasks == 1]
    _, t1b, s1b = fit(m1_formula + " + " + " + ".join(f"task_{t}" for t in TASKS_ALL_YEARS), d1b, "M1b pooled + tasks")

    d25 = d[(d.survey_year == 2025) & (d.answered_ai_tasks == 1) & (d.answered_frustration == 1)
            & d.ai_agents.notna() & d.ai_use_frequency.notna()].copy()
    f2a = f"distrusts_ai ~ {DEMOGRAPHICS} + {c('ic_or_pm')}"
    f2b = f2a + f" + {c('ai_use_frequency')} + {c('ai_agents')} + " + " + ".join(f"task_{t}" for t in TASKS_2025)
    f2c = f2b + " + " + " + ".join(f"frus_{f}" for f in FRUSTRATIONS)
    tabs25 = {}
    for name, f in (("M2a", f2a), ("M2b", f2b), ("M2c", f2c)):
        _, t, s = fit(f, d25, name)
        tabs25[name] = t
        out_tabs.append(t)
        stats.append(s)
    out_tabs = [t1, t1b] + out_tabs
    stats = [s1, s1b] + stats

    all_tab = pd.concat(out_tabs, ignore_index=True)
    all_tab.to_csv(TABLES / "model_coefficients.csv", index=False)
    fit_df = pd.DataFrame(stats)
    fit_df.to_csv(TABLES / "model_fit.csv", index=False)

    forest(t1, "fig12a_forest_pooled", "Who distrusts AI? Pooled 2023-2025 model",
           "Odds ratios from logistic regression; professional developers who use AI; all variables entered together",
           ["Year", "Experience", "Role", "Company size", "Age", "Country"])
    forest(tabs25["M2c"], "fig12b_forest_2025", "What goes with distrust in 2025: usage and frustrations, net of demographics",
           "Odds ratios, model M2c (demographic controls included but not shown)",
           ["Experience", "AI use frequency", "AI agents", "Uses AI for", "Frustration"])
    fig_stepwise(tabs25)

    print(fit_df.round(3).to_string())
    key = all_tab[all_tab.label.str.contains("Year:|30\\+ yrs|Frustration|AI use frequency|AI agents", regex=True)]
    print(key[["model", "label", "odds_ratio", "or_low", "or_high", "p_value", "ame_pp"]].round(3).to_string())
    return dict(coefficients=all_tab, fit=fit_df)


if __name__ == "__main__":
    main()
