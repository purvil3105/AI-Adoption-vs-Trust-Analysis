"""Assemble a static, deployable website in site/ (GitHub Pages, Netlify, Vercel, any static host).

site/
  index.html            landing page (headline numbers are read from reports/tables/, never hard-coded)
  dashboard.html        interactive dashboard (copy of dashboard/ai_trust_dashboard.html)
  memo.html, memo.pdf   insight memo
  figures/*.png         static charts
  data/*.csv            small aggregate tables (no respondent-level data)

Only aggregates are published, so the site is ODbL-compliant and small (~10 MB).
Set REPO_URL (or GITHUB_REPOSITORY, set automatically in GitHub Actions) to show a "View code" link.
Usage:  python -m src.build_site
"""
import html
import os
import shutil

import pandas as pd

from src.config import DASHBOARD, FIGURES, ROOT, TABLES

SITE = ROOT / "site"
REPORTS = ROOT / "reports"

GALLERY = [
    ("fig01_adoption_vs_trust_trend", "Adoption up, trust down",
     "Professional developers; trust measured among current AI users, the same population every year."),
    ("fig02_official_vs_comparable_trust", "Why the base matters",
     "The official trend mixes different populations each year; the comparable base shows a steady decline."),
    ("fig03_distrust_by_experience", "Distrust rises with experience",
     "And it rose in every experience band between 2023 and 2025."),
    ("fig09_frustrations_2025", "'Almost right' vs 'debugging takes longer'",
     "The near-universal frustration does not separate trusters from distrusters; debugging cost does."),
    ("fig12b_forest_2025", "What goes with distrust (2025 regression)",
     "Odds ratios from logistic regression with demographic controls and robust standard errors."),
    ("fig15_reweighted_trend", "Robust to reweighting",
     "2024 and 2025 raked to the 2023 respondent mix; the trend survives."),
]

PUBLISHED_TABLES = ["desc_headline_trend", "desc_segments", "desc_task_trust", "desc_frustrations_2025",
                    "desc_use_frequency_2025", "model_coefficients", "model_fit", "robustness_models",
                    "robustness_reweighted_trend", "benchmark_check"]


def metrics() -> dict:
    h = pd.read_csv(TABLES / "desc_headline_trend.csv")
    get = lambda m, y: float(h[(h.metric == m) & (h.survey_year == y)].share.iloc[0])  # noqa: E731
    coef = pd.read_csv(TABLES / "model_coefficients.csv")
    term = lambda model, label: coef[(coef.model == model) & (coef.label == label)].iloc[0]  # noqa: E731
    fr = pd.read_csv(TABLES / "desc_frustrations_2025.csv").set_index("frustration")
    fq = pd.read_csv(TABLES / "desc_use_frequency_2025.csv").set_index("segment")
    bench = pd.read_csv(TABLES / "benchmark_check.csv")
    n_resp = int(pd.read_csv(TABLES / "desc_official_vs_comparable.csv").pipe(lambda d: d[
        (d.outcome == "trusts_ai") & d.definition.str.startswith("Comparable")]).n.sum())
    return {
        "adopt23": get("Adoption (uses AI)", 2023), "adopt25": get("Adoption (uses AI)", 2025),
        "trust23": get("Trust (AI users)", 2023), "trust25": get("Trust (AI users)", 2025),
        "dist23": get("Distrust (AI users)", 2023), "dist25": get("Distrust (AI users)", 2025),
        "or_year": float(term("M1 pooled", "Year: 2025 (vs 2023)").odds_ratio),
        "or_exp": float(term("M1 pooled", "Experience: 30+ yrs (vs 0-4 yrs)").odds_ratio),
        "or_almost": float(term("M2c", "Frustration: 'almost right, but not quite'").odds_ratio),
        "or_debug": float(term("M2c", "Frustration: debugging AI code takes longer").odds_ratio),
        "ame_debug": float(term("M2c", "Frustration: debugging AI code takes longer").ame_pp),
        "almost_prev": float(fr.loc["almost_right", "prevalence"]),
        "dist_daily": float(fq.loc["Daily", "share"]), "dist_monthly": float(fq.loc["Monthly or less", "share"]),
        "bench_pass": int((bench.status == "PASS").sum()), "bench_n": len(bench),
        "bench_max": float(bench.diff_pp.abs().max()), "n_users": n_resp,
    }


def pct(v: float) -> str:
    return f"{v * 100:.0f}%"


def page(m: dict, repo_url: str | None) -> str:
    code_btn = (f'<a class="btn ghost" href="{html.escape(repo_url)}" target="_blank" rel="noopener">View code on GitHub</a>'
                if repo_url else "")
    gallery = "\n".join(
        f'<figure class="card"><a href="figures/{f}.png" target="_blank" rel="noopener">'
        f'<img src="figures/{f}.png" alt="{html.escape(t)}" loading="lazy"></a>'
        f'<figcaption><b>{html.escape(t)}</b><span>{html.escape(c)}</span></figcaption></figure>'
        for f, t, c in GALLERY if (FIGURES / f"{f}.png").exists())
    steps = ["Download", "Harmonise", "Validate", "DuckDB SQL", "Descriptives", "Regression", "Robustness",
             "Dashboard", "Memo"]
    flow = "".join(f'<li><span>{i + 1}</span>{s}</li>' for i, s in enumerate(steps))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Adoption vs Trust</title>
<meta name="description" content="End-to-end product analytics case study: developers use AI more every year but trust it less. Stack Overflow Developer Survey 2023-2025.">
<meta property="og:title" content="Developer AI Adoption vs Trust Analytics">
<meta property="og:description" content="AI adoption among professional developers rose from {pct(m['adopt23'])} to {pct(m['adopt25'])}; distrust among users rose from {pct(m['dist23'])} to {pct(m['dist25'])}.">
<meta property="og:image" content="figures/fig01_adoption_vs_trust_trend.png">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' fill='%232a78d6'/><path d='M7 22l6-7 5 4 7-9' stroke='white' stroke-width='3' fill='none' stroke-linecap='round' stroke-linejoin='round'/></svg>">
<style>
:root {{
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --border: rgba(11,11,11,0.10);
  --adoption: #2a78d6; --trust: #1baf7a; --distrust: #eb6834; --accent-ink: #ffffff;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --border: rgba(255,255,255,0.10);
    --adoption: #3987e5; --trust: #199e70; --distrust: #d95926;
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
  --grid: #2c2c2a; --border: rgba(255,255,255,0.10);
  --adoption: #3987e5; --trust: #199e70; --distrust: #d95926;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--page); color: var(--ink); font: 15px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }}
.wrap {{ max-width: 1100px; margin: 0 auto; padding: 40px 16px 56px; }}
.eyebrow {{ color: var(--adoption); font-weight: 600; font-size: 13px; letter-spacing: .04em; text-transform: uppercase; margin: 0 0 8px; }}
h1 {{ font-size: clamp(28px, 5vw, 42px); line-height: 1.12; margin: 0 0 12px; letter-spacing: -0.01em; text-wrap: balance; }}
.lede {{ font-size: 17px; color: var(--ink-2); max-width: 720px; margin: 0 0 20px; }}
.tags {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 22px; padding: 0; list-style: none; }}
.tags li {{ border: 1px solid var(--border); border-radius: 999px; padding: 2px 10px; font-size: 12.5px; color: var(--ink-2); background: var(--surface); }}
.actions {{ display: flex; flex-wrap: wrap; gap: 10px; }}
.btn {{ display: inline-block; padding: 10px 16px; border-radius: 10px; font-weight: 600; text-decoration: none;
  background: var(--adoption); color: var(--accent-ink); border: 1px solid transparent; }}
.btn.ghost {{ background: var(--surface); color: var(--ink); border-color: var(--border); }}
.btn:hover {{ filter: brightness(1.08); }}
section {{ margin-top: 44px; }}
h2 {{ font-size: 21px; margin: 0 0 14px; }}
.kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr)); gap: 12px; }}
.card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 16px 18px; margin: 0; min-width: 0; }}
.kpi .label {{ font-size: 13px; color: var(--ink-2); }}
.kpi .value {{ font-size: 32px; font-weight: 650; font-variant-numeric: tabular-nums; }}
.kpi .delta {{ font-size: 13px; color: var(--ink-2); }}
.sw {{ display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; }}
ol.findings {{ margin: 0; padding: 0; list-style: none; display: grid; gap: 10px; counter-reset: f; }}
ol.findings li {{ counter-increment: f; position: relative; padding-left: 44px; }}
ol.findings li::before {{ content: counter(f); position: absolute; left: 16px; top: 16px; font-weight: 700; color: var(--adoption); }}
ol.findings b {{ display: block; margin-bottom: 2px; }}
ol.findings span {{ color: var(--ink-2); }}
.gallery {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 330px), 1fr)); gap: 14px; }}
.gallery img {{ width: 100%; height: auto; border-radius: 8px; border: 1px solid var(--grid); background: #fcfcfb; display: block; }}
figcaption {{ margin-top: 8px; font-size: 13.5px; }}
figcaption span {{ display: block; color: var(--ink-2); }}
ol.flow {{ list-style: none; padding: 0; margin: 0 0 14px; display: flex; flex-wrap: wrap; gap: 8px; }}
ol.flow li {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 6px 10px; font-size: 13.5px; }}
ol.flow li span {{ color: var(--adoption); font-weight: 700; margin-right: 6px; }}
.two {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr)); gap: 14px; }}
.two ul {{ margin: 6px 0 0; padding-left: 18px; color: var(--ink-2); }}
.two li {{ margin-bottom: 4px; }}
.two h3 {{ margin: 0; font-size: 16px; }}
footer {{ margin-top: 48px; color: var(--muted); font-size: 13px; border-top: 1px solid var(--grid); padding-top: 16px; }}
footer a {{ color: inherit; }}
</style>
</head>
<body>
<main class="wrap">
  <p class="eyebrow">Product analytics case study</p>
  <h1>Developers use AI more every year, but trust it less. Who trusts it, and why?</h1>
  <p class="lede">An end-to-end analysis of 203,812 responses to the Stack Overflow Developer Survey 2023&ndash;2025:
    cross-year harmonisation, a DuckDB SQL layer, logistic regression with controls, bias and robustness checks,
    an interactive dashboard and an insight memo with product recommendations.</p>
  <ul class="tags"><li>Python</li><li>pandas</li><li>DuckDB SQL</li><li>statsmodels</li><li>Logistic regression</li>
    <li>Survey weighting</li><li>Plotly</li><li>Power BI</li></ul>
  <div class="actions">
    <a class="btn" href="dashboard.html">Open interactive dashboard</a>
    <a class="btn ghost" href="memo.html">Read the insight memo</a>
    <a class="btn ghost" href="memo.pdf">Memo (PDF)</a>
    {code_btn}
  </div>

  <section aria-label="Headline numbers">
    <h2>Headline numbers</h2>
    <div class="kpis">
      <div class="card kpi"><div class="label"><span class="sw" style="background:var(--adoption)"></span>Professional developers using AI</div>
        <div class="value">{pct(m['adopt25'])}</div><div class="delta">2025, up from {pct(m['adopt23'])} in 2023</div></div>
      <div class="card kpi"><div class="label"><span class="sw" style="background:var(--trust)"></span>AI users who trust AI accuracy</div>
        <div class="value">{pct(m['trust25'])}</div><div class="delta">2025, down from {pct(m['trust23'])} in 2023</div></div>
      <div class="card kpi"><div class="label"><span class="sw" style="background:var(--distrust)"></span>AI users who distrust AI accuracy</div>
        <div class="value">{pct(m['dist25'])}</div><div class="delta">2025, up from {pct(m['dist23'])} in 2023</div></div>
      <div class="card kpi"><div class="label"><span class="sw" style="background:var(--distrust)"></span>"Debugging AI code takes longer"</div>
        <div class="value">+{m['ame_debug']:.0f} pp</div><div class="delta">higher chance of distrust, all else equal (OR {m['or_debug']:.2f})</div></div>
    </div>
  </section>

  <section>
    <h2>Key findings</h2>
    <ol class="findings">
      <li class="card"><b>The trust decline is real, not just a different crowd.</b>
        <span>With experience, role, company size, country and age held constant, the odds of distrust are
        {m['or_year']:.2f}&times; higher in 2025 than in 2023. Reweighting each year to the 2023 respondent mix does not change the picture.</span></li>
      <li class="card"><b>Experience is the strongest personal predictor.</b>
        <span>Developers with 30+ years of coding have about {m['or_exp']:.1f}&times; the odds of distrust of those with 0&ndash;4 years.
        How they use AI explains only about a quarter of that gap.</span></li>
      <li class="card"><b>Occasional users are the most sceptical.</b>
        <span>In 2025, {pct(m['dist_monthly'])} of monthly-or-less users distrust AI, against {pct(m['dist_daily'])} of daily users.
        Moving users to habitual use is the biggest trust lever in the data.</span></li>
      <li class="card"><b>"Almost right, but not quite" is not the differentiator.</b>
        <span>{pct(m['almost_prev'])} of professional AI users report it, but it shows no association with distrust once other factors
        are controlled (OR {m['or_almost']:.2f}). "Debugging AI code takes longer" is what tracks distrust.</span></li>
      <li class="card"><b>Company size doesn't matter once controls are added.</b>
        <span>Role and country do: embedded and infra roles and Western Europe distrust most; India least.</span></li>
    </ol>
  </section>

  <section>
    <h2>Selected charts</h2>
    <div class="gallery">
{gallery}
    </div>
  </section>

  <section>
    <h2>How it was built</h2>
    <ol class="flow">{flow}</ol>
    <div class="two">
      <div class="card"><h3>Analytical rigour</h3><ul>
        <li>Every question mapped across three years with a documented comparability tier (crosswalk + value maps); the pipeline stops on any unmapped label.</li>
        <li>Caught a swapped trust/benefit column in the 2023 file by profiling values against the official schema.</li>
        <li>Rebuilt a like-for-like trust base after finding the official year-on-year figures compare different populations.</li>
        <li>Reproduces Stack Overflow's published tables: {m['bench_pass']}/{m['bench_n']} percentages within &plusmn;1 pp (largest gap {m['bench_max']:.2f} pp).</li>
      </ul></div>
      <div class="card"><h3>Product recommendations</h3><ul>
        <li>Optimise for the cost of fixing AI output (tests, diffs, citations, revert), not only first-answer accuracy.</li>
        <li>Design for sceptical senior users: explicit uncertainty and checkable explanations.</li>
        <li>Turn occasional users into habitual users with early, verifiable wins.</li>
        <li>Track debugging and rework time as a leading indicator of eroding trust.</li>
      </ul></div>
    </div>
  </section>

  <footer>
    Data: <a href="https://survey.stackoverflow.co/" target="_blank" rel="noopener">Stack Overflow Developer Survey</a> 2023&ndash;2025,
    Open Database License (ODbL). Only derived aggregates are published here
    (<a href="data/">aggregate tables</a>). All results are associations from a self-selected sample, not causal effects.
  </footer>
</main>
</body>
</html>
"""


def data_index(files: list[str]) -> str:
    links = "".join(f'<li><a href="{f}">{f}</a></li>' for f in files)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            'content="width=device-width, initial-scale=1"><title>Aggregate tables</title>'
            '<style>body{font:15px/1.6 system-ui,sans-serif;max-width:720px;margin:40px auto;padding:0 16px;'
            'background:#f9f9f7;color:#0b0b0b}@media (prefers-color-scheme:dark){body{background:#0d0d0d;color:#f0efec}'
            'a{color:#9ec5f4}}</style></head><body><h1>Aggregate tables</h1><p>Derived from the Stack Overflow Developer '
            'Survey 2023-2025 (ODbL). No respondent-level data.</p><ul>' + links +
            '</ul><p><a href="../">&larr; Back</a></p></body></html>')


def main() -> None:
    required = [DASHBOARD / "ai_trust_dashboard.html", REPORTS / "insight_memo.html", TABLES / "desc_headline_trend.csv"]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError(f"run the pipeline first; missing: {missing}")
    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "figures").mkdir(parents=True)
    (SITE / "data").mkdir()

    shutil.copy2(DASHBOARD / "ai_trust_dashboard.html", SITE / "dashboard.html")
    shutil.copy2(REPORTS / "insight_memo.html", SITE / "memo.html")
    if (REPORTS / "insight_memo.pdf").exists():
        shutil.copy2(REPORTS / "insight_memo.pdf", SITE / "memo.pdf")
    for f in FIGURES.glob("*.png"):
        shutil.copy2(f, SITE / "figures" / f.name)
    published = []
    for t in PUBLISHED_TABLES:
        if (TABLES / f"{t}.csv").exists():
            shutil.copy2(TABLES / f"{t}.csv", SITE / "data" / f"{t}.csv")
            published.append(f"{t}.csv")
    (SITE / "data" / "index.html").write_text(data_index(published), encoding="utf-8")

    repo = os.environ.get("REPO_URL") or (
        f"https://github.com/{os.environ['GITHUB_REPOSITORY']}" if os.environ.get("GITHUB_REPOSITORY") else None)
    (SITE / "index.html").write_text(page(metrics(), repo), encoding="utf-8")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")       # serve files as-is on GitHub Pages
    size = sum(p.stat().st_size for p in SITE.rglob("*") if p.is_file()) / 1e6
    print(f"wrote {SITE} ({size:.1f} MB): index.html, dashboard.html, memo.html, "
          f"{len(list((SITE / 'figures').glob('*.png')))} figures, {len(published)} tables")


if __name__ == "__main__":
    main()
