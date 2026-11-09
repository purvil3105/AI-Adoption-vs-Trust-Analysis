"""Phase 7 - descriptive analysis: adoption vs trust by year and segment, with 95% Wilson CIs.

Scope: professional developers. Adoption base = answered the AI-use question.
Trust base = current AI users who answered the trust question (comparable across years).
Usage:  python -m src.descriptives
"""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MultipleLocator
import pandas as pd

from src import viz
from src.config import MIN_N, RESPONDENTS_PARQUET, TABLES
from src.stats_utils import share_table

BASE_NOTE = ("Base: professional developers. Adoption = share answering 'Yes' to 'Do you currently use AI tools?'. "
             "Trust/distrust = share of current AI users. Source: Stack Overflow Developer Survey 2023-2025 (ODbL).")

DIMENSIONS = {
    "exp_bucket": ("Experience (years coding, incl. education)", ["0-4 yrs", "5-9 yrs", "10-19 yrs", "20-29 yrs", "30+ yrs"]),
    "org_size": ("Company size", None),
    "role_family": ("Role", None),
    "country_group": ("Country (top 15 + Other)", None),
    "age_group": ("Age", ["18-24", "25-34", "35-44", "45-54", "55+"]),
}


def load() -> pd.DataFrame:
    df = pd.read_parquet(RESPONDENTS_PARQUET)
    return df[df.is_professional == 1].copy()


def users(df: pd.DataFrame) -> pd.DataFrame:
    return df[df.in_trust_base_users == 1]


# ------------------------------------------------------------------ tables
def headline_table(df: pd.DataFrame) -> pd.DataFrame:
    a = share_table(df, ["survey_year"], "uses_ai").assign(metric="Adoption (uses AI)")
    t = share_table(users(df), ["survey_year"], "trusts_ai").assign(metric="Trust (AI users)")
    d = share_table(users(df), ["survey_year"], "distrusts_ai").assign(metric="Distrust (AI users)")
    return pd.concat([a, t, d], ignore_index=True)


def official_vs_comparable(full: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, mask in (("Official tables (base changes each year)", full.in_trust_base_official == 1),
                        ("Comparable: current AI users only", full.in_trust_base_users == 1)):
        for outcome in ("trusts_ai", "distrusts_ai"):
            t = share_table(full, ["survey_year"], outcome, base_mask=mask).assign(definition=label, outcome=outcome)
            rows.append(t)
    return pd.concat(rows, ignore_index=True)


def segment_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for dim, (label, _) in DIMENSIONS.items():
        a = share_table(df, ["survey_year", dim], "uses_ai").rename(columns={dim: "segment"})
        d = share_table(users(df), ["survey_year", dim], "distrusts_ai").rename(columns={dim: "segment"})
        t = share_table(users(df), ["survey_year", dim], "trusts_ai").rename(columns={dim: "segment"})
        m = (a[["survey_year", "segment", "n", "share"]].rename(columns={"n": "n_adoption", "share": "adoption"})
             .merge(d[["survey_year", "segment", "n", "share", "ci_low", "ci_high"]]
                    .rename(columns={"n": "n_trust", "share": "distrust", "ci_low": "distrust_lo", "ci_high": "distrust_hi"}),
                    on=["survey_year", "segment"], how="left")
             .merge(t[["survey_year", "segment", "share"]].rename(columns={"share": "trust"}),
                    on=["survey_year", "segment"], how="left"))
        m.insert(0, "dimension", label)
        m["suppressed"] = m.n_trust.fillna(0) < MIN_N
        rows.append(m)
    return pd.concat(rows, ignore_index=True)


def task_table(df: pd.DataFrame) -> pd.DataFrame:
    u = users(df)
    task_cols = [c for c in df.columns if c.startswith("task_") and c != "task_other"]
    rows = []
    for c in task_cols:
        for y, g in u.groupby("survey_year"):
            g = g[g[c].notna()]
            if g.empty:
                continue
            sel = g[g[c] == 1]
            if len(sel) < MIN_N:
                continue
            rows.append(dict(task=c.removeprefix("task_"), survey_year=y, n_users=len(sel),
                             share_using=len(sel) / len(g), distrust=sel.distrusts_ai.mean(),
                             distrust_not_using=g.loc[g[c] == 0, "distrusts_ai"].mean()))
    return pd.DataFrame(rows)


def frustration_table(df: pd.DataFrame) -> pd.DataFrame:
    u = users(df)
    u = u[(u.survey_year == 2025) & (u.answered_frustration == 1)]
    rows = []
    for c in [c for c in df.columns if c.startswith("frus_")]:
        yes, no = u[u[c] == 1], u[u[c] == 0]
        rows.append(dict(frustration=c.removeprefix("frus_"), prevalence=u[c].mean(), n_yes=len(yes),
                         distrust_if_reported=yes.distrusts_ai.mean(), distrust_if_not=no.distrusts_ai.mean()))
    return pd.DataFrame(rows).sort_values("prevalence", ascending=False)


def frequency_table(df: pd.DataFrame) -> pd.DataFrame:
    d25 = df[(df.survey_year == 2025)]
    # use the official base here so non-users (asked in 2025 only) can be shown for context
    base = d25[d25.in_trust_base_official == 1]
    f = share_table(base, ["ai_use_frequency"], "distrusts_ai").rename(columns={"ai_use_frequency": "segment"})
    f.insert(0, "dimension", "AI use frequency")
    a = share_table(base[base.uses_ai == 1], ["ai_agents"], "distrusts_ai").rename(columns={"ai_agents": "segment"})
    a.insert(0, "dimension", "AI agents (AI users)")
    return pd.concat([f, a], ignore_index=True)


def composition_table(full: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in ("exp_bucket", "country_group", "role_family", "age_group", "org_size"):
        c = (full.groupby("survey_year")[col].value_counts(normalize=True).rename("share").reset_index()
             .rename(columns={col: "segment"}))
        c.insert(0, "dimension", col)
        rows.append(c)
    return pd.concat(rows, ignore_index=True)


# ------------------------------------------------------------------ figures
def fig_headline(h: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.8))
    colors = {"Adoption (uses AI)": viz.ADOPTION, "Trust (AI users)": viz.TRUST, "Distrust (AI users)": viz.DISTRUST}
    ends, starts = [], []
    for metric, g in h.groupby("metric", sort=False):
        c = colors[metric]
        ax.plot(g.survey_year, g.share, color=c, marker="o", markersize=7, markeredgecolor=viz.SURFACE,
                markeredgewidth=2, zorder=3)
        ax.vlines(g.survey_year, g.ci_low, g.ci_high, color=c, linewidth=2, alpha=0.5)
        ends.append((g.iloc[-1].share, f"{metric}  {g.iloc[-1].share:.0%}"))
        starts.append((g.iloc[0].share, f"{g.iloc[0].share:.0%}"))
    # trust and distrust end at almost the same value in 2025 -> keep labels apart
    viz.repel_labels(ax, [2025] * 3, [e[0] for e in ends], [e[1] for e in ends], min_dy=0.05, x_span=1,
                     dx=0.08, fontsize=9, color=viz.INK)
    viz.repel_labels(ax, [2023] * 3, [s[0] for s in starts], [s[1] for s in starts], min_dy=0.04, x_span=1,
                     dx=-0.17, fontsize=9)
    ax.set_xticks([2023, 2024, 2025])
    ax.set_xlim(2022.6, 2025.9)
    viz.pct_axis(ax, lim=(0, 1))
    ax.set_title("Developers use AI more every year, and trust it less")
    viz.subtitle(ax, "Professional developers; trust measured among current AI users (same population every year)")
    fig.tight_layout()
    viz.footnote(fig, BASE_NOTE + " Bars = 95% CI.")
    viz.save(fig, "fig01_adoption_vs_trust_trend")


def fig_official_vs_comparable(t: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
    for ax, (definition, g) in zip(axes, t.groupby("definition", sort=False)):
        for outcome, c, lab in (("trusts_ai", viz.TRUST, "Trust"), ("distrusts_ai", viz.DISTRUST, "Distrust")):
            s = g[g.outcome == outcome]
            ax.plot(s.survey_year, s.share, color=c, marker="o", markersize=7, markeredgecolor=viz.SURFACE,
                    markeredgewidth=2)
            for _, r in s.iterrows():
                ax.annotate(f"{r.share:.1%}", (r.survey_year, r.share), xytext=(0, 9 if outcome == "trusts_ai" else -14),
                            textcoords="offset points", ha="center", fontsize=8.5, color=viz.INK_2)
            ax.annotate(lab, (s.survey_year.iloc[-1], s.share.iloc[-1]), xytext=(12, 0), textcoords="offset points",
                        va="center", fontsize=9, color=viz.INK)
        ax.set_title(definition, fontsize=10.5, pad=8)
        ax.set_xticks([2023, 2024, 2025])
        ax.set_xlim(2022.7, 2025.6)
        viz.pct_axis(ax, lim=(0.1, 0.55))
    fig.suptitle("Why the base matters: the official trust trend mixes different populations",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout()
    viz.footnote(fig, "Official base = everyone who answered the trust question: users + planners (2023), users only (2024), "
                      "everyone incl. non-users (2025). All respondents shown. Source: Stack Overflow Developer Survey (ODbL).")
    viz.save(fig, "fig02_official_vs_comparable_trust")


def fig_dumbbell(seg: pd.DataFrame, dimension: str, order: list | None, name: str, title: str) -> None:
    s = seg[(seg.dimension == dimension) & ~seg.suppressed]
    if order is None:
        order = (s[s.survey_year == 2025].sort_values("distrust").segment.tolist()
                 + [x for x in s.segment.unique() if x not in set(s[s.survey_year == 2025].segment)])
    else:
        order = order[::-1]
    pos = {k: i for i, k in enumerate(order)}
    s = s[s.segment.isin(pos)].assign(y=lambda d: d.segment.map(pos))
    fig, ax = plt.subplots(figsize=(8.2, 0.42 * len(order) + 1.6))
    for seg_name, g in s.groupby("segment"):
        ax.plot([g.distrust.min(), g.distrust.max()], [pos[seg_name]] * 2, color=viz.GRID, linewidth=3, zorder=1)
    for y, g in s.groupby("survey_year"):
        ax.errorbar(g.distrust, g.y, xerr=[g.distrust - g.distrust_lo, g.distrust_hi - g.distrust],
                    fmt="o", color=viz.YEAR_COLORS[y], markersize=8, markeredgecolor=viz.SURFACE, markeredgewidth=1.5,
                    elinewidth=1, capsize=0, label=str(y), zorder=3)
    last = s[s.survey_year == 2025]
    for _, r in last.iterrows():
        ax.annotate(f"{r.distrust:.0%}", (r.distrust_hi, r.y), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=8, color=viz.INK_2)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order)
    ax.grid(axis="y", visible=False)
    viz.pct_axis(ax, axis="x", lim=(0, max(0.6, s.distrust_hi.max() + 0.06)))
    ax.set_xlabel("Share of AI users who distrust AI output accuracy")
    viz.legend_above(ax)
    ax.set_title(title)
    viz.subtitle(ax, "Professional developers who use AI; dots = survey year, lines = 95% CI; label = 2025",
                 legend_row=True)
    fig.tight_layout()
    viz.footnote(fig, f"Segments with fewer than {MIN_N} AI users in a year are hidden. " + BASE_NOTE)
    viz.save(fig, name)


def fig_scatter(seg: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    for ax, dim, ttl in ((axes[0], "Role", "By role"), (axes[1], "Country (top 15 + Other)", "By country")):
        s = seg[(seg.dimension == dim) & (seg.survey_year == 2025) & ~seg.suppressed]
        ax.scatter(s.adoption, s.distrust, s=np.sqrt(s.n_trust) * 6, color=viz.ADOPTION, alpha=0.75,
                   edgecolor=viz.SURFACE, linewidth=2, zorder=3)
        viz.repel_labels(ax, s.adoption.tolist(), s.distrust.tolist(), s.segment.tolist(), min_dy=0.016,
                         x_span=0.06, dx=0.006, fontsize=7.5)
        ax.set_title(ttl, fontsize=10.5, pad=8)
        viz.pct_axis(ax, "x")
        viz.pct_axis(ax, "y")
        ax.xaxis.set_major_locator(MultipleLocator(0.05))
        ax.set_xlabel("Adoption: share using AI tools (2025)")
    axes[0].set_ylabel("Distrust among AI users (2025)")
    fig.suptitle("Adoption is high everywhere; distrust is what separates segments (2025)",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout()
    viz.footnote(fig, "Bubble size = number of AI users. " + BASE_NOTE)
    viz.save(fig, "fig07_adoption_vs_distrust_segments_2025")


def fig_tasks(tasks: pd.DataFrame) -> None:
    t = tasks.copy()
    order = t[t.survey_year == 2025].sort_values("distrust").task.tolist()
    order += [x for x in t.task.unique() if x not in order]
    pos = {k: i for i, k in enumerate(order)}
    fig, ax = plt.subplots(figsize=(8.2, 0.42 * len(order) + 1.6))
    for y, g in t.groupby("survey_year"):
        ax.scatter(g.distrust, g.task.map(pos), color=viz.YEAR_COLORS[y], s=60, edgecolor=viz.SURFACE, linewidth=1.5,
                   label=str(y), zorder=3)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([o.replace("_", " ") for o in order])
    ax.grid(axis="y", visible=False)
    viz.pct_axis(ax, "x", lim=(0, 0.45))
    ax.set_xlabel("Distrust among AI users who use AI for this task")
    viz.legend_above(ax)
    ax.set_title("Type of AI use: people who hand AI riskier work distrust it less")
    viz.subtitle(ax, "Professional developers who use AI. 2025 'currently' = mostly-AI or partially-AI", legend_row=True)
    fig.tight_layout()
    viz.footnote(fig, "Tasks missing in a year were not offered that year (see question_crosswalk.csv). Association only: "
                      "trusting users may adopt AI for more tasks. " + BASE_NOTE)
    viz.save(fig, "fig08_distrust_by_ai_task")


def fig_frustrations(fr: pd.DataFrame) -> None:
    f = fr[~fr.frustration.isin(["other", "not_regular_user"])].sort_values("prevalence")
    labels = {"almost_right": "AI solutions almost right, but not quite", "debugging_slower": "Debugging AI code takes longer",
              "less_confident": "Less confident in my own problem-solving", "hard_to_understand": "Hard to understand how/why code works",
              "no_problems": "No problems encountered"}
    y = np.arange(len(f))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.9), sharey=True, gridspec_kw={"width_ratios": [1, 1.2]})
    a1.barh(y, f.prevalence, color=viz.ADOPTION, height=0.6)
    for yi, v in zip(y, f.prevalence):
        a1.text(v + 0.01, yi, f"{v:.0%}", va="center", fontsize=8.5, color=viz.INK_2)
    a1.set_yticks(y)
    a1.set_yticklabels([labels.get(k, k) for k in f.frustration])
    a1.grid(axis="y", visible=False)
    viz.pct_axis(a1, "x", lim=(0, 0.8))
    a1.set_title("How common (AI users)", fontsize=10.5, pad=8)
    a2.scatter(f.distrust_if_not, y, color=viz.NEUTRAL_GRAY, s=60, label="Did not report it", zorder=3)
    a2.scatter(f.distrust_if_reported, y, color=viz.DISTRUST, s=60, label="Reported it", zorder=3)
    for yi, lo, hi in zip(y, f.distrust_if_not, f.distrust_if_reported):
        a2.plot([lo, hi], [yi, yi], color=viz.GRID, linewidth=3, zorder=1)
        a2.text(max(lo, hi) + 0.015, yi, f"{(hi - lo) * 100:+.0f} pp", va="center", fontsize=8.5, color=viz.INK_2)
    a2.grid(axis="y", visible=False)
    viz.pct_axis(a2, "x", lim=(0, 0.65))
    a2.set_title("Distrust: reported vs did not report", fontsize=10.5, pad=8)
    a2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=8.5)
    fig.suptitle("'Almost right' is nearly universal; 'debugging takes longer' is what tracks distrust (2025)",
                 x=0.01, ha="left", fontsize=12.5, fontweight="bold")
    fig.tight_layout()
    viz.footnote(fig, "Base: professional developers who use AI and answered the 2025 frustration question (multi-select). "
                      "Source: Stack Overflow Developer Survey 2025 (ODbL).")
    viz.save(fig, "fig09_frustrations_2025")


def fig_frequency(fq: pd.DataFrame) -> None:
    order = {"AI use frequency": ["Not using", "Monthly or less", "Weekly", "Daily"],
             "AI agents (AI users)": ["No agents", "Copilot/autocomplete only", "Uses agents"]}
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), gridspec_kw={"width_ratios": [4, 3]})
    for ax, (dim, segs) in zip(axes, order.items()):
        s = fq[fq.dimension == dim].set_index("segment").reindex(segs).dropna(subset=["share"])
        x = np.arange(len(s))
        ax.bar(x, s.share, color=viz.DISTRUST, width=0.6)
        ax.errorbar(x, s.share, yerr=[s.share - s.ci_low, s.ci_high - s.share], fmt="none", ecolor=viz.INK_2, elinewidth=1)
        for xi, v, n in zip(x, s.share, s.n):
            ax.text(xi, v + 0.035, f"{v:.0%}", ha="center", fontsize=9, color=viz.INK)
            ax.text(xi, 0.02, f"n={n:,}", ha="center", fontsize=7.5, color=viz.SURFACE)
        ax.set_xticks(x)
        ax.set_xticklabels(s.index, fontsize=8.5)
        ax.grid(axis="x", visible=False)
        viz.pct_axis(ax, lim=(0, 0.95))
        ax.set_title(dim, fontsize=10.5, pad=8)
    axes[0].set_ylabel("Distrust AI accuracy")
    fig.suptitle("The more often developers use AI, the less they distrust it (2025)", x=0.01, ha="left",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    viz.footnote(fig, "Base: professional developers who answered the 2025 trust question (2025 asked it of non-users too). "
                      "Association only - direction of cause is unknown. Source: Stack Overflow Developer Survey 2025 (ODbL).")
    viz.save(fig, "fig10_distrust_by_use_frequency_2025")


def fig_composition(comp: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    specs = (("exp_bucket", ["0-4 yrs", "5-9 yrs", "10-19 yrs", "20-29 yrs", "30+ yrs"], "Experience (years coding)"),
             ("country_group", ["United States", "Germany", "India", "United Kingdom", "Ukraine", "France", "Canada", "Other"],
              "Country (largest groups)"))
    for ax, (dim, cats, ttl) in zip(axes, specs):
        c = comp[(comp.dimension == dim) & comp.segment.isin(cats)]
        x = np.arange(len(cats))
        w = 0.26
        for i, y in enumerate((2023, 2024, 2025)):
            v = c[c.survey_year == y].set_index("segment").reindex(cats).share
            ax.bar(x + (i - 1) * (w + 0.01), v, width=w, color=viz.YEAR_COLORS[y], label=str(y))
        ax.set_xticks(x)
        ax.set_xticklabels(cats, fontsize=8, rotation=20, ha="right")
        ax.grid(axis="x", visible=False)
        viz.pct_axis(ax)
        ax.set_title(ttl, fontsize=10.5, pad=8)
    axes[1].legend(ncol=3, fontsize=8.5, loc="upper center")
    fig.suptitle("Who answers changes every year: 2025 respondents are more experienced", x=0.01, ha="left",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    viz.footnote(fig, "Share of professional developers in each survey year. Self-selected sample - see Limitations. "
                      "Source: Stack Overflow Developer Survey 2023-2025 (ODbL).")
    viz.save(fig, "fig11_sample_composition")


def main() -> dict:
    viz.setup()
    full = pd.read_parquet(RESPONDENTS_PARQUET)
    df = full[full.is_professional == 1]

    h = headline_table(df)
    ovc = official_vs_comparable(full)
    seg = segment_table(df)
    tasks = task_table(df)
    fr = frustration_table(df)
    fq = frequency_table(df)
    comp = composition_table(df)
    for name, t in (("headline_trend", h), ("official_vs_comparable", ovc), ("segments", seg), ("task_trust", tasks),
                    ("frustrations_2025", fr), ("use_frequency_2025", fq), ("sample_composition", comp)):
        t.to_csv(TABLES / f"desc_{name}.csv", index=False)

    fig_headline(h)
    fig_official_vs_comparable(ovc)
    for dim, (label, order) in DIMENSIONS.items():
        name = {"exp_bucket": "fig03_distrust_by_experience", "role_family": "fig04_distrust_by_role",
                "org_size": "fig05_distrust_by_company_size", "country_group": "fig06_distrust_by_country",
                "age_group": "fig06b_distrust_by_age"}[dim]
        title = {"exp_bucket": "Distrust rises with experience - and rose in every experience band",
                 "role_family": "Distrust by role: embedded, infra and research roles are most sceptical",
                 "org_size": "Distrust by company size: larger companies are slightly more sceptical",
                 "country_group": "Distrust by country: Western Europe high, India low",
                 "age_group": "Distrust by age"}[dim]
        if dim == "org_size":
            order = ["1 Solo / freelancer", "2 Under 20", "3 20-99", "4 100-999", "5 1k-9.9k", "6 10k+"]
        fig_dumbbell(seg, label, order, name, title)
    fig_scatter(seg)
    fig_tasks(tasks)
    fig_frustrations(fr)
    fig_frequency(fq)
    fig_composition(comp)
    print(h.round(3).to_string())
    print(fr.round(3).to_string())
    return dict(headline=h, segments=seg, tasks=tasks, frustrations=fr, frequency=fq)


if __name__ == "__main__":
    main()
