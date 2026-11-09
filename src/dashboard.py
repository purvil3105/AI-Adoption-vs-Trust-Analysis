"""Phase 10 - interactive dashboard as ONE self-contained HTML file (Plotly.js embedded, works offline, free).

Reads the aggregated tables in reports/tables/ (no respondent-level data is embedded).
Output: dashboard/ai_trust_dashboard.html
Usage:  python -m src.dashboard
"""
import json

import pandas as pd
import plotly.offline as po

from src.config import DASHBOARD, MAPPINGS, MIN_N, TABLES


def records(df: pd.DataFrame, cols: list[str] | None = None) -> list[dict]:
    d = df if cols is None else df[cols]
    return json.loads(d.to_json(orient="records", double_precision=4))


def collect() -> dict:
    seg = pd.read_csv(TABLES / "desc_segments.csv")
    seg = seg[~seg.suppressed]
    coef = pd.read_csv(TABLES / "model_coefficients.csv")
    m2c = coef[(coef.model == "M2c") & coef.label.str.match(
        r"^(Experience|AI use frequency|AI agents|Uses AI for|Frustration)") & ~coef.label.str.contains("Missing")]
    m1 = coef[(coef.model == "M1 pooled") & (coef.label != "Intercept") & ~coef.label.str.contains("Missing")]
    step = coef[coef.model.isin(["M2a", "M2b", "M2c"]) & coef.label.str.startswith("Experience:")
                & ~coef.label.str.contains("Missing")]
    rob_path = TABLES / "robustness_models.csv"
    cw = pd.read_csv(MAPPINGS / "question_crosswalk.csv").fillna("")
    bench = pd.read_csv(TABLES / "benchmark_check.csv")
    return {
        "headline": records(pd.read_csv(TABLES / "desc_headline_trend.csv")),
        "official": records(pd.read_csv(TABLES / "desc_official_vs_comparable.csv")),
        "segments": records(seg, ["dimension", "survey_year", "segment", "n_adoption", "adoption", "n_trust",
                                  "distrust", "distrust_lo", "distrust_hi", "trust"]),
        "tasks": records(pd.read_csv(TABLES / "desc_task_trust.csv")),
        "frustrations": records(pd.read_csv(TABLES / "desc_frustrations_2025.csv")),
        "frequency": records(pd.read_csv(TABLES / "desc_use_frequency_2025.csv")),
        "forest2025": records(m2c, ["label", "odds_ratio", "or_low", "or_high", "p_value", "ame_pp"]),
        "forestPooled": records(m1, ["label", "odds_ratio", "or_low", "or_high", "p_value", "ame_pp"]),
        "stepwise": records(step, ["model", "label", "ame_pp", "ame_low_pp", "ame_high_pp"]),
        "fit": records(pd.read_csv(TABLES / "model_fit.csv")),
        "reweighted": records(pd.read_csv(TABLES / "robustness_reweighted_trend.csv")),
        "robustness": records(pd.read_csv(rob_path)) if rob_path.exists() else [],
        "crosswalk": records(cw, ["harmonised_var", "col_2023", "col_2024", "col_2025", "comparability",
                                  "harmonisation_rule"]),
        "benchmark": {"checks": int(len(bench)), "passed": int((bench.status == "PASS").sum()),
                      "max_diff": float(bench.diff_pp.abs().max())},
        "minN": MIN_N,
    }


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Adoption vs Trust</title>
<style>
:root {
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --border: rgba(11,11,11,0.10);
  --adoption: #2a78d6; --trust: #1baf7a; --distrust: #eb6834; --gray: #b9b8b2;
  --y2023: #86b6ef; --y2024: #2a78d6; --y2025: #104281;
  --step1: #86b6ef; --step2: #2a78d6; --step3: #104281;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
    --adoption: #3987e5; --trust: #199e70; --distrust: #d95926; --gray: #6b6a65;
    --y2023: #1c5cab; --y2024: #3987e5; --y2025: #9ec5f4;
    --step1: #1c5cab; --step2: #3987e5; --step3: #9ec5f4;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
  --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
  --adoption: #3987e5; --trust: #199e70; --distrust: #d95926; --gray: #6b6a65;
  --y2023: #1c5cab; --y2024: #3987e5; --y2025: #9ec5f4;
  --step1: #1c5cab; --step2: #3987e5; --step3: #9ec5f4;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink);
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif; font-size: 14px; line-height: 1.45; }
.wrap { max-width: 1200px; margin: 0 auto; padding: 20px 16px 48px; }
header h1 { font-size: 24px; margin: 0 0 4px; }
header p { margin: 0; color: var(--ink-2); }
.topbar { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; flex-wrap: wrap; }
.theme-btn { border: 1px solid var(--border); background: var(--surface); color: var(--ink); border-radius: 8px;
  padding: 6px 10px; cursor: pointer; font: inherit; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin: 18px 0; }
.kpi { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; }
.kpi .label { color: var(--ink-2); font-size: 12.5px; }
.kpi .value { font-size: 30px; font-weight: 650; margin-top: 2px; }
.kpi .delta { font-size: 12.5px; color: var(--ink-2); }
.kpi .swatch { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; vertical-align: 0; }
nav.tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--grid); margin-bottom: 14px; overflow-x: auto; }
nav.tabs button { border: 0; background: none; color: var(--ink-2); font: inherit; padding: 10px 12px; cursor: pointer;
  border-bottom: 2px solid transparent; white-space: nowrap; }
nav.tabs button[aria-selected="true"] { color: var(--ink); border-bottom-color: var(--adoption); font-weight: 600; }
.filters { display: flex; flex-wrap: wrap; gap: 12px; align-items: end; margin: 0 0 14px; }
.filters label { display: flex; flex-direction: column; font-size: 12px; color: var(--ink-2); gap: 4px; }
select { font: inherit; padding: 6px 8px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface); color: var(--ink); }
.grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 520px), 1fr)); gap: 14px; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; min-width: 0; }
.card h2 { font-size: 15px; margin: 0 0 2px; }
.card .sub { color: var(--ink-2); font-size: 12.5px; margin: 0 0 6px; }
.card .note { color: var(--muted); font-size: 11.5px; margin-top: 6px; }
.chart { width: 100%; min-height: 320px; }
details { margin-top: 6px; font-size: 12.5px; }
details summary { cursor: pointer; color: var(--ink-2); }
.tbl { overflow-x: auto; max-height: 340px; overflow-y: auto; }
table { border-collapse: collapse; width: 100%; font-size: 12px; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 4px 8px; border-bottom: 1px solid var(--grid); }
th { position: sticky; top: 0; background: var(--surface); color: var(--ink-2); font-weight: 600; }
.panel[hidden] { display: none; }
.prose { max-width: 820px; }
.prose h3 { margin: 18px 0 6px; font-size: 15px; }
.prose li { margin-bottom: 4px; }
.tag { display: inline-block; padding: 0 6px; border-radius: 6px; border: 1px solid var(--border); font-size: 11.5px; }
footer { color: var(--muted); font-size: 12px; margin-top: 24px; }
</style>
</head>
<body>
<div class="wrap">
  <header class="topbar">
    <div>
      <h1>Developers use AI more every year, but trust it less</h1>
      <p>Stack Overflow Developer Survey 2023-2025 &middot; professional developers &middot; trust measured among current AI users</p>
    </div>
    <button class="theme-btn" id="themeBtn" type="button" aria-label="Toggle colour theme">Theme: auto</button>
  </header>

  <section class="kpis" id="kpis" aria-label="Headline numbers"></section>

  <nav class="tabs" role="tablist">
    <button role="tab" aria-selected="true" data-tab="overview">Overview</button>
    <button role="tab" aria-selected="false" data-tab="who">Who trusts AI</button>
    <button role="tab" aria-selected="false" data-tab="how">How AI is used</button>
    <button role="tab" aria-selected="false" data-tab="why">Why distrust (2025)</button>
    <button role="tab" aria-selected="false" data-tab="method">Method &amp; caveats</button>
  </nav>

  <section class="panel" id="tab-overview">
    <div class="grid2">
      <div class="card"><h2>Adoption up, trust down</h2>
        <p class="sub">Share of professional developers using AI; trust and distrust among current AI users. Bars = 95% CI.</p>
        <div class="chart" id="c-trend"></div><details><summary>Show data table</summary><div class="tbl" id="t-trend"></div></details></div>
      <div class="card"><h2>Why the base matters</h2>
        <p class="sub">Official tables use a different population each year (skip logic). Comparable = current AI users only. All respondents.</p>
        <div class="chart" id="c-official"></div><details><summary>Show data table</summary><div class="tbl" id="t-official"></div></details></div>
    </div>
  </section>

  <section class="panel" id="tab-who" hidden>
    <div class="filters">
      <label>Break down by<select id="f-dim"></select></label>
      <label>Metric<select id="f-metric">
        <option value="distrust">Distrust (AI users)</option><option value="trust">Trust (AI users)</option>
        <option value="adoption">Adoption (uses AI)</option></select></label>
      <label>Year for scatter<select id="f-year"><option>2025</option><option>2024</option><option>2023</option></select></label>
    </div>
    <div class="grid2">
      <div class="card"><h2 id="h-seg">By segment and year</h2><p class="sub">Dots = survey year. Segments with fewer than __MINN__ AI users are hidden.</p>
        <div class="chart" id="c-seg"></div><details><summary>Show data table</summary><div class="tbl" id="t-seg"></div></details></div>
      <div class="card"><h2>Adoption vs distrust</h2><p class="sub">Each bubble is a segment; size = number of AI users.</p>
        <div class="chart" id="c-scatter"></div><details><summary>Show data table</summary><div class="tbl" id="t-scatter"></div></details></div>
    </div>
  </section>

  <section class="panel" id="tab-how" hidden>
    <div class="grid2">
      <div class="card"><h2>Distrust by type of AI use</h2><p class="sub">AI users who currently use AI for each task. Tasks missing in a year were not offered.</p>
        <div class="chart" id="c-tasks"></div><details><summary>Show data table</summary><div class="tbl" id="t-tasks"></div></details>
        <p class="note">Association only: people who already trust AI may hand it more (and riskier) tasks.</p></div>
      <div class="card"><h2>Use frequency and agents (2025)</h2><p class="sub">Distrust by how often AI is used, and by AI-agent use.</p>
        <div class="chart" id="c-freq"></div><details><summary>Show data table</summary><div class="tbl" id="t-freq"></div></details></div>
    </div>
  </section>

  <section class="panel" id="tab-why" hidden>
    <div class="grid2">
      <div class="card"><h2>Frustrations: how common, and how they track distrust</h2>
        <p class="sub">Professional AI users, 2025. Dots: distrust among those who did / did not report each frustration.</p>
        <div class="chart" id="c-frus"></div><details><summary>Show data table</summary><div class="tbl" id="t-frus"></div></details></div>
      <div class="card"><h2>Experience effect across nested models</h2>
        <p class="sub">Average marginal effect on P(distrust) vs 0-4 yrs. Same 2025 sample in all three models.</p>
        <div class="chart" id="c-step"></div><details><summary>Show data table</summary><div class="tbl" id="t-step"></div></details></div>
    </div>
    <div class="card" style="margin-top:14px"><h2>Logistic regression: what is associated with distrust (2025, model M2c)</h2>
      <p class="sub">Odds ratios with robust 95% CIs, log scale. Right of 1 = more distrust. Demographic controls included (not shown). Grey = not significant at 5%.</p>
      <div class="chart" id="c-forest" style="min-height:640px"></div><details><summary>Show data table</summary><div class="tbl" id="t-forest"></div></details></div>
  </section>

  <section class="panel" id="tab-method" hidden>
    <div class="grid2">
      <div class="card"><h2>Does the trend survive reweighting?</h2><p class="sub">2024 and 2025 raked to the 2023 mix of country, experience, age and company size.</p>
        <div class="chart" id="c-rw"></div><details><summary>Show data table</summary><div class="tbl" id="t-rw"></div></details></div>
      <div class="card"><h2>Robustness checks</h2><p class="sub">Odds ratio (95% CI) for each key association under each specification.</p>
        <div class="tbl" id="t-rob" style="max-height:420px"></div></div>
    </div>
    <div class="card prose" style="margin-top:14px">
      <h3>Data</h3>
      <p>Stack Overflow Developer Survey 2023 (89,184 responses), 2024 (65,437) and 2025 (49,191). Licensed under the Open Database License (ODbL).
      Our harmonised numbers reproduce the official results tables: <span id="benchTxt"></span>.</p>
      <h3>Definitions</h3>
      <ul>
        <li><b>Adoption</b> = answered "Yes" to "Do you currently use AI tools in your development process?" (2025's daily / weekly / monthly answers combined).</li>
        <li><b>Trust / distrust</b> = "Highly" or "Somewhat" trust / distrust the accuracy of AI output. "Neither" stays in the denominator.</li>
        <li><b>Comparable trust base</b> = current AI users. The trust question was shown to users + planners (2023), users only (2024) and everyone (2025), so the official year-to-year figures are not like-for-like.</li>
        <li>2023 stores the trust question in column <code>AIBen</code> (and benefits in <code>AIAcc</code>) - the reverse of 2024/2025.</li>
      </ul>
      <h3>Limitations</h3>
      <ul>
        <li>Self-selected sample of (mostly Stack Overflow-engaged) developers - not representative of all developers. Reweighting fixes the observed mix only.</li>
        <li>In 2025, ~31% of respondents did not answer the AI section (it was optional), so 2025 AI figures describe those who reached it.</li>
        <li>Cross-sectional, self-reported data: every result is an association, not a cause.</li>
        <li>Questions only asked in some years (frustrations, agents, frequency) are analysed within that year only.</li>
      </ul>
      <h3>Question crosswalk (comparability tiers)</h3>
      <p><span class="tag">A</span> identical &middot; <span class="tag">B</span> harmonised after documented recoding &middot; <span class="tag">C</span> not comparable across years</p>
      <div class="tbl" id="t-cw" style="max-height:420px"></div>
    </div>
  </section>

  <footer>Source: Stack Overflow Developer Survey 2023-2025, ODbL. Built with Python, DuckDB and Plotly. All figures are survey-sample estimates.</footer>
</div>

<script>__PLOTLY__</script>
<script>
const D = __DATA__;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const pct = v => v == null ? "" : (v * 100).toFixed(1) + "%";
const pct0 = v => v == null ? "" : Math.round(v * 100) + "%";
const YEARS = [2023, 2024, 2025];
const cfg = { displayModeBar: false, responsive: true };

function base(extra = {}) {
  return Object.assign({
    paper_bgcolor: css("--surface"), plot_bgcolor: css("--surface"),
    font: { family: 'system-ui, -apple-system, "Segoe UI", sans-serif', color: css("--ink-2"), size: 12 },
    margin: { l: 56, r: 16, t: 10, b: 44 }, hovermode: "closest",
    hoverlabel: { bgcolor: css("--surface"), bordercolor: css("--axis"), font: { color: css("--ink") } },
    xaxis: { gridcolor: css("--grid"), linecolor: css("--axis"), zeroline: false, tickfont: { color: css("--muted") } },
    yaxis: { gridcolor: css("--grid"), linecolor: css("--axis"), zeroline: false },
    legend: { orientation: "h", y: 1.1, x: 1, xanchor: "right", font: { color: css("--ink") } },
  }, extra);
}
function table(id, rows, cols) {
  const head = "<tr>" + cols.map(c => `<th>${c[0]}</th>`).join("") + "</tr>";
  const body = rows.map(r => "<tr>" + cols.map(c => `<td>${c[2] ? c[2](r[c[1]], r) : (r[c[1]] ?? "")}</td>`).join("") + "</tr>").join("");
  document.getElementById(id).innerHTML = `<table>${head}${body}</table>`;
}
const metricColor = { "Adoption (uses AI)": "--adoption", "Trust (AI users)": "--trust", "Distrust (AI users)": "--distrust" };

// ---------------- KPI tiles
function kpis() {
  const h = D.headline, get = (m, y) => h.find(r => r.metric === m && r.survey_year === y);
  const tiles = [
    ["Adoption (uses AI)", "Use AI tools, 2025", "Adoption (uses AI)"],
    ["Trust (AI users)", "Trust AI accuracy, 2025 (AI users)", "Trust (AI users)"],
    ["Distrust (AI users)", "Distrust AI accuracy, 2025 (AI users)", "Distrust (AI users)"],
  ];
  let html = tiles.map(([m, label, key]) => {
    const a = get(m, 2023), b = get(m, 2025), d = (b.share - a.share) * 100;
    return `<div class="kpi"><div class="label"><span class="swatch" style="background:var(${metricColor[key]})"></span>${label}</div>
      <div class="value">${pct0(b.share)}</div><div class="delta">${d >= 0 ? "+" : ""}${d.toFixed(0)} pp vs 2023 (${pct0(a.share)})</div></div>`;
  }).join("");
  const dbg = D.forest2025.find(r => r.label.startsWith("Frustration: debugging"));
  html += `<div class="kpi"><div class="label"><span class="swatch" style="background:var(--distrust)"></span>"Debugging AI code takes longer"</div>
    <div class="value">+${dbg.ame_pp.toFixed(0)} pp</div><div class="delta">higher chance of distrust, all else equal (2025)</div></div>`;
  document.getElementById("kpis").innerHTML = html;
}

// ---------------- Overview
function trend() {
  const traces = [];
  for (const m of ["Adoption (uses AI)", "Trust (AI users)", "Distrust (AI users)"]) {
    const r = D.headline.filter(x => x.metric === m);
    traces.push({ x: r.map(x => x.survey_year), y: r.map(x => x.share), name: m, mode: "lines+markers+text",
      line: { color: css(metricColor[m]), width: 2.5 }, marker: { size: 9, line: { color: css("--surface"), width: 2 } },
      error_y: { type: "data", symmetric: false, array: r.map(x => x.ci_high - x.share), arrayminus: r.map(x => x.share - x.ci_low),
        color: css(metricColor[m]), thickness: 1.5, width: 0 },
      text: r.map((x, i) => i === r.length - 1 ? pct0(x.share) : ""), textposition: m.startsWith("Trust") ? "top right" : "bottom right",
      textfont: { color: css("--ink") },
      hovertemplate: "%{x}: %{y:.1%}<br>n = %{customdata:,}<extra>" + m + "</extra>", customdata: r.map(x => x.n) });
  }
  Plotly.react("c-trend", traces, base({ yaxis: { tickformat: ".0%", range: [0, 1], gridcolor: css("--grid") },
    xaxis: { tickvals: YEARS, range: [2022.7, 2025.4], gridcolor: css("--grid"), tickfont: { color: css("--muted") } } }), cfg);
  table("t-trend", D.headline, [["Metric", "metric"], ["Year", "survey_year"], ["Share", "share", pct], ["95% CI low", "ci_low", pct],
    ["95% CI high", "ci_high", pct], ["n", "n", v => v.toLocaleString()]]);
}
function official() {
  const defs = [...new Set(D.official.map(r => r.definition))];
  const traces = [];
  defs.forEach((def, i) => {
    for (const [o, c, lab] of [["trusts_ai", "--trust", "Trust"], ["distrusts_ai", "--distrust", "Distrust"]]) {
      const r = D.official.filter(x => x.definition === def && x.outcome === o);
      traces.push({ x: r.map(x => x.survey_year), y: r.map(x => x.share), xaxis: i ? "x2" : "x", yaxis: "y",
        name: lab, showlegend: i === 0, legendgroup: lab, mode: "lines+markers", line: { color: css(c), width: 2.5 },
        marker: { size: 8 }, hovertemplate: def + "<br>%{x}: %{y:.1%}<extra>" + lab + "</extra>" });
    }
  });
  const ax = { tickvals: YEARS, gridcolor: css("--grid"), tickfont: { color: css("--muted") }, range: [2022.7, 2025.3] };
  Plotly.react("c-official", traces, base({
    grid: { rows: 1, columns: 2, pattern: "independent" }, xaxis: { ...ax, domain: [0, 0.47] }, xaxis2: { ...ax, domain: [0.53, 1] },
    yaxis: { tickformat: ".0%", range: [0.1, 0.55], gridcolor: css("--grid") }, margin: { l: 50, r: 10, t: 34, b: 40 },
    legend: { orientation: "h", y: -0.14, x: 0, xanchor: "left", font: { color: css("--ink") } },
    annotations: defs.map((d, i) => ({ text: d.replace(" (base changes each year)", "<br>(base changes yearly)").replace("Comparable: ", "Comparable:<br>"),
      x: i ? 0.53 : 0, xref: "paper", y: 1.12, yref: "paper", showarrow: false, xanchor: "left", align: "left",
      font: { size: 11.5, color: css("--ink") } })) }), cfg);
  table("t-official", D.official, [["Definition", "definition"], ["Outcome", "outcome"], ["Year", "survey_year"], ["Share", "share", pct], ["n", "n", v => v.toLocaleString()]]);
}

// ---------------- Who
const DIMS = [...new Set(D.segments.map(r => r.dimension))];
const ORDERS = {
  "Experience (years coding, incl. education)": ["0-4 yrs", "5-9 yrs", "10-19 yrs", "20-29 yrs", "30+ yrs"],
  "Company size": ["1 Solo / freelancer", "2 Under 20", "3 20-99", "4 100-999", "5 1k-9.9k", "6 10k+"],
  "Age": ["18-24", "25-34", "35-44", "45-54", "55+", "Under 18"],
};
const clean = s => String(s).replace(/^\d /, "");
function who() {
  const dim = document.getElementById("f-dim").value, metric = document.getElementById("f-metric").value;
  const year = +document.getElementById("f-year").value;
  const rows = D.segments.filter(r => r.dimension === dim);
  let order = ORDERS[dim];
  if (!order) order = rows.filter(r => r.survey_year === 2025).sort((a, b) => a.distrust - b.distrust).map(r => r.segment)
      .concat([...new Set(rows.map(r => r.segment))].filter(s => !rows.some(r => r.survey_year === 2025 && r.segment === s)));
  else order = order.slice().reverse();
  order = order.filter(s => rows.some(r => r.segment === s));
  const traces = YEARS.map(y => {
    const r = order.map(s => rows.find(x => x.segment === s && x.survey_year === y)).filter(Boolean);
    const t = { x: r.map(x => x[metric]), y: r.map(x => clean(x.segment)), name: String(y), mode: "markers", type: "scatter",
      marker: { size: 11, color: css("--y" + y), line: { color: css("--surface"), width: 1.5 } },
      customdata: r.map(x => [metric === "adoption" ? x.n_adoption : x.n_trust]),
      hovertemplate: "%{y} · " + y + "<br>%{x:.1%} (n = %{customdata[0]:,})<extra></extra>" };
    if (metric === "distrust") t.error_x = { type: "data", symmetric: false, array: r.map(x => x.distrust_hi - x.distrust),
      arrayminus: r.map(x => x.distrust - x.distrust_lo), color: css("--y" + y), thickness: 1, width: 0 };
    return t;
  });
  const h = Math.max(320, 34 * order.length + 90);
  document.getElementById("c-seg").style.height = h + "px";
  Plotly.react("c-seg", traces, base({ margin: { l: 10, r: 16, t: 10, b: 40 }, height: h,
    xaxis: { tickformat: ".0%", gridcolor: css("--grid"), tickfont: { color: css("--muted") }, rangemode: "tozero" },
    yaxis: { categoryorder: "array", categoryarray: order.map(clean), gridcolor: "rgba(0,0,0,0)", automargin: true } }), cfg);
  document.getElementById("h-seg").textContent = `${document.getElementById("f-metric").selectedOptions[0].text} by ${dim.toLowerCase()}`;
  table("t-seg", rows.slice().sort((a, b) => a.survey_year - b.survey_year), [["Year", "survey_year"], ["Segment", "segment", clean],
    ["Adoption", "adoption", pct], ["Trust", "trust", pct], ["Distrust", "distrust", pct], ["AI users (n)", "n_trust", v => v == null ? "" : v.toLocaleString()]]);

  const s = rows.filter(r => r.survey_year === year && r.distrust != null);
  Plotly.react("c-scatter", [{ x: s.map(r => r.adoption), y: s.map(r => r.distrust), text: s.map(r => clean(r.segment)),
    mode: "markers+text", textposition: "top center", textfont: { size: 10, color: css("--ink-2") },
    marker: { size: s.map(r => Math.sqrt(r.n_trust) / 2.2 + 6), color: css("--adoption"), opacity: 0.75, line: { color: css("--surface"), width: 2 } },
    customdata: s.map(r => r.n_trust), hovertemplate: "<b>%{text}</b><br>Adoption %{x:.1%}<br>Distrust %{y:.1%}<br>AI users: %{customdata:,}<extra></extra>" }],
    base({ showlegend: false, xaxis: { title: { text: `Adoption (${year})` }, tickformat: ".0%", gridcolor: css("--grid"), tickfont: { color: css("--muted") } },
      yaxis: { title: { text: "Distrust among AI users" }, tickformat: ".0%", gridcolor: css("--grid") } }), cfg);
  table("t-scatter", s, [["Segment", "segment", clean], ["Adoption", "adoption", pct], ["Distrust", "distrust", pct], ["AI users (n)", "n_trust", v => v.toLocaleString()]]);
}

// ---------------- How
function how() {
  const t = D.tasks, order = t.filter(r => r.survey_year === 2025).sort((a, b) => a.distrust - b.distrust).map(r => r.task)
    .concat([...new Set(t.map(r => r.task))].filter(x => !t.some(r => r.survey_year === 2025 && r.task === x)));
  const nice = s => s.replaceAll("_", " ");
  Plotly.react("c-tasks", YEARS.map(y => {
    const r = t.filter(x => x.survey_year === y);
    return { x: r.map(x => x.distrust), y: r.map(x => nice(x.task)), name: String(y), mode: "markers",
      marker: { size: 10, color: css("--y" + y), line: { color: css("--surface"), width: 1.5 } }, customdata: r.map(x => x.n_users),
      hovertemplate: "%{y} · " + y + "<br>Distrust %{x:.1%} (n = %{customdata:,})<extra></extra>" };
  }), base({ height: 470, margin: { l: 150, r: 16, t: 10, b: 40 }, xaxis: { tickformat: ".0%", rangemode: "tozero", gridcolor: css("--grid"), tickfont: { color: css("--muted") } },
    yaxis: { categoryorder: "array", categoryarray: order.map(nice), gridcolor: "rgba(0,0,0,0)" } }), cfg);
  table("t-tasks", t, [["Year", "survey_year"], ["Task", "task", nice], ["AI users doing it", "n_users", v => v.toLocaleString()],
    ["Share of AI users", "share_using", pct], ["Distrust (does task)", "distrust", pct], ["Distrust (does not)", "distrust_not_using", pct]]);

  const f = D.frequency, segs = ["Not using", "Monthly or less", "Weekly", "Daily", "No agents", "Copilot/autocomplete only", "Uses agents"];
  const r = segs.map(s => f.find(x => x.segment === s)).filter(Boolean);
  const short = { "Not using": "Not<br>using", "Monthly or less": "Monthly<br>or less", "Copilot/autocomplete only": "Copilot /<br>autocomplete", "No agents": "No<br>agents", "Uses agents": "Uses<br>agents" };
  Plotly.react("c-freq", [{ x: r.map(x => short[x.segment] || x.segment), y: r.map(x => x.share), type: "bar", marker: { color: css("--distrust") },
    error_y: { type: "data", symmetric: false, array: r.map(x => x.ci_high - x.share), arrayminus: r.map(x => x.share - x.ci_low), color: css("--ink-2"), thickness: 1, width: 0 },
    text: r.map(x => pct0(x.share)), textposition: "outside", textfont: { color: css("--ink") }, customdata: r.map(x => [x.n, x.dimension]),
    hovertemplate: "%{customdata[1]}: %{x}<br>Distrust %{y:.1%}<br>n = %{customdata[0]:,}<extra></extra>" }],
    base({ showlegend: false, bargap: 0.35, yaxis: { tickformat: ".0%", range: [0, 0.95], gridcolor: css("--grid") },
      xaxis: { tickfont: { color: css("--muted"), size: 11 }, tickangle: 0 }, margin: { l: 56, r: 16, t: 10, b: 56 },
      shapes: [{ type: "line", x0: 3.5, x1: 3.5, y0: 0, y1: 0.95, line: { color: css("--grid"), width: 1 } }],
      annotations: [{ x: 1.5, y: 0.93, text: "AI use frequency", showarrow: false, font: { color: css("--ink-2") } },
        { x: 5, y: 0.93, text: "AI agents (AI users)", showarrow: false, font: { color: css("--ink-2") } }] }), cfg);
  table("t-freq", f, [["Group", "dimension"], ["Segment", "segment"], ["Distrust", "share", pct], ["95% CI", "ci_low", (v, r) => pct(r.ci_low) + " - " + pct(r.ci_high)], ["n", "n", v => v.toLocaleString()]]);
}

// ---------------- Why
const FR = { almost_right: "Almost right, but not quite", debugging_slower: "Debugging AI code takes longer", less_confident: "Less confident in own problem-solving",
  hard_to_understand: "Hard to understand how/why code works", no_problems: "No problems encountered" };
function why() {
  const f = D.frustrations.filter(r => FR[r.frustration]).sort((a, b) => a.prevalence - b.prevalence);
  const y = f.map(r => FR[r.frustration]);
  Plotly.react("c-frus", [
    { x: f.map(r => r.prevalence), y, type: "bar", orientation: "h", name: "How common", marker: { color: css("--adoption") }, xaxis: "x",
      text: f.map(r => pct0(r.prevalence)), textposition: "outside", textfont: { color: css("--ink-2") }, hovertemplate: "%{y}<br>Reported by %{x:.1%}<extra></extra>" },
    { x: f.map(r => r.distrust_if_not), y, mode: "markers", name: "Distrust: did not report", marker: { color: css("--gray"), size: 11 }, xaxis: "x2",
      hovertemplate: "%{y}<br>Distrust if not reported: %{x:.1%}<extra></extra>" },
    { x: f.map(r => r.distrust_if_reported), y, mode: "markers", name: "Distrust: reported", marker: { color: css("--distrust"), size: 11 }, xaxis: "x2",
      hovertemplate: "%{y}<br>Distrust if reported: %{x:.1%}<extra></extra>" }],
    base({ height: 360, margin: { l: 220, r: 16, t: 30, b: 40 }, legend: { orientation: "h", y: -0.18, x: 0, xanchor: "left", font: { color: css("--ink") } },
      xaxis: { domain: [0, 0.45], tickformat: ".0%", range: [0, 0.95], gridcolor: css("--grid"), tickfont: { color: css("--muted") } },
      xaxis2: { domain: [0.55, 1], tickformat: ".0%", range: [0, 0.65], gridcolor: css("--grid"), tickfont: { color: css("--muted") } },
      yaxis: { gridcolor: "rgba(0,0,0,0)" },
      annotations: [{ text: "How common", x: 0, xref: "paper", y: 1.08, yref: "paper", showarrow: false, xanchor: "left", font: { color: css("--ink") } },
        { text: "Distrust: reported vs not", x: 0.55, xref: "paper", y: 1.08, yref: "paper", showarrow: false, xanchor: "left", font: { color: css("--ink") } }] }), cfg);
  table("t-frus", D.frustrations, [["Frustration", "frustration"], ["Share reporting", "prevalence", pct], ["Distrust if reported", "distrust_if_reported", pct],
    ["Distrust if not", "distrust_if_not", pct], ["n reporting", "n_yes", v => v.toLocaleString()]]);

  const names = { M2a: "Demographics only", M2b: "+ use frequency, agents, tasks", M2c: "+ frustrations" };
  const steps = ["M2a", "M2b", "M2c"], lv = s => s.split(":")[1].split("(")[0].trim();
  Plotly.react("c-step", steps.map((m, i) => {
    const r = D.stepwise.filter(x => x.model === m);
    return { x: r.map(x => lv(x.label)), y: r.map(x => x.ame_pp), type: "bar", name: names[m], marker: { color: css("--step" + (i + 1)) },
      error_y: { type: "data", symmetric: false, array: r.map(x => x.ame_high_pp - x.ame_pp), arrayminus: r.map(x => x.ame_pp - x.ame_low_pp), color: css("--ink-2"), thickness: 1, width: 0 },
      hovertemplate: "%{x} vs 0-4 yrs<br>%{y:+.1f} pp<extra>" + names[m] + "</extra>" };
  }), base({ barmode: "group", yaxis: { title: { text: "pp change in P(distrust)" }, gridcolor: css("--grid") },
    xaxis: { tickfont: { color: css("--muted") }, categoryorder: "array", categoryarray: ["5-9 yrs", "10-19 yrs", "20-29 yrs", "30+ yrs"] } }), cfg);
  table("t-step", D.stepwise, [["Model", "model"], ["Term", "label"], ["AME (pp)", "ame_pp", v => v.toFixed(1)],
    ["95% CI", "ame_low_pp", (v, r) => r.ame_low_pp.toFixed(1) + " to " + r.ame_high_pp.toFixed(1)]]);

  forest("c-forest", D.forest2025);
  table("t-forest", D.forest2025, [["Term", "label"], ["Odds ratio", "odds_ratio", v => v.toFixed(2)],
    ["95% CI", "or_low", (v, r) => r.or_low.toFixed(2) + " - " + r.or_high.toFixed(2)], ["p", "p_value", v => v < 0.001 ? "<0.001" : v.toFixed(3)],
    ["AME (pp)", "ame_pp", v => (v >= 0 ? "+" : "") + v.toFixed(1)]]);
}
function forest(id, rows) {
  const blockOrder = ["Experience", "AI use frequency", "AI agents", "Uses AI for", "Frustration"];
  const blk = l => blockOrder.find(b => l.startsWith(b)) || "Other";
  const r = rows.slice().sort((a, b) => blockOrder.indexOf(blk(b.label)) - blockOrder.indexOf(blk(a.label)) || a.odds_ratio - b.odds_ratio);
  const col = x => x.p_value >= 0.05 ? css("--gray") : (x.odds_ratio > 1 ? css("--distrust") : css("--adoption"));
  const lab = l => l.replace(/ \(vs .*\)$/, "");
  Plotly.react(id, [{ x: r.map(x => x.odds_ratio), y: r.map(x => lab(x.label)), mode: "markers", marker: { size: 9, color: r.map(col) },
    error_x: { type: "data", symmetric: false, array: r.map(x => x.or_high - x.odds_ratio), arrayminus: r.map(x => x.odds_ratio - x.or_low), color: css("--ink-2"), thickness: 1, width: 0 },
    customdata: r.map(x => [x.or_low, x.or_high, x.ame_pp]),
    hovertemplate: "<b>%{y}</b><br>OR %{x:.2f} (%{customdata[0]:.2f}-%{customdata[1]:.2f})<br>AME %{customdata[2]:+.1f} pp<extra></extra>" }],
    base({ height: 640, showlegend: false, margin: { l: 300, r: 16, t: 10, b: 44 },
      xaxis: { type: "log", tickvals: [0.25, 0.5, 1, 2, 4], ticktext: ["0.25", "0.5", "1", "2", "4"], gridcolor: css("--grid"), tickfont: { color: css("--muted") },
        title: { text: "Odds ratio for distrust (log scale)" } },
      yaxis: { categoryorder: "array", categoryarray: r.map(x => lab(x.label)), gridcolor: "rgba(0,0,0,0)", automargin: true },
      shapes: [{ type: "line", x0: 1, x1: 1, yref: "paper", y0: 0, y1: 1, line: { color: css("--axis"), width: 1 } }] }), cfg);
}

// ---------------- Method
function method() {
  const rw = D.reweighted, versions = [...new Set(rw.map(r => r.version))];
  const traces = [];
  versions.forEach((v, i) => {
    for (const [m, c] of [["Adoption", "--adoption"], ["Trust", "--trust"], ["Distrust", "--distrust"]]) {
      const r = rw.filter(x => x.version === v && x.metric === m);
      traces.push({ x: r.map(x => x.survey_year), y: r.map(x => x.share), name: m + (i ? " (reweighted)" : ""), legendgroup: m,
        mode: "lines+markers", line: { color: css(c), width: 2.5, dash: i ? "dot" : "solid" }, marker: { size: 8, symbol: i ? "diamond" : "circle" },
        hovertemplate: v + "<br>%{x}: %{y:.1%}<extra>" + m + "</extra>" });
    }
  });
  Plotly.react("c-rw", traces, base({ legend: { orientation: "h", y: -0.2, x: 0, xanchor: "left", font: { color: css("--ink") } },
    yaxis: { tickformat: ".0%", range: [0, 1], gridcolor: css("--grid") }, xaxis: { tickvals: YEARS, gridcolor: css("--grid"), tickfont: { color: css("--muted") } } }), cfg);
  table("t-rw", rw, [["Version", "version"], ["Metric", "metric"], ["Year", "survey_year"], ["Share", "share", pct], ["Effective n", "n_eff", v => Math.round(v).toLocaleString()]]);
  if (D.robustness.length) table("t-rob", D.robustness, [["Specification", "spec"], ["Association", "key_term"],
    ["OR (95% CI)", "odds_ratio", (v, r) => `${v.toFixed(2)} (${r.or_low.toFixed(2)}-${r.or_high.toFixed(2)})`], ["p", "p_value", v => v < 0.001 ? "<0.001" : v.toFixed(3)], ["n", "n", v => v.toLocaleString()]]);
  table("t-cw", D.crosswalk, [["Variable", "harmonised_var"], ["2023", "col_2023"], ["2024", "col_2024"], ["2025", "col_2025"], ["Tier", "comparability"], ["Rule", "harmonisation_rule"]]);
  document.getElementById("benchTxt").textContent = `${D.benchmark.passed} of ${D.benchmark.checks} published percentages matched within ±1 pp (largest gap ${D.benchmark.max_diff.toFixed(2)} pp)`;
}

// ---------------- wiring
const dimSel = document.getElementById("f-dim");
dimSel.innerHTML = DIMS.map(d => `<option>${d}</option>`).join("");
dimSel.value = DIMS.find(d => d.startsWith("Experience")) || DIMS[0];
["f-dim", "f-metric", "f-year"].forEach(id => document.getElementById(id).addEventListener("change", who));
const renderers = { overview: () => { trend(); official(); }, who, how, why, method };
let current = "overview";
document.querySelectorAll("nav.tabs button").forEach(b => b.addEventListener("click", () => {
  document.querySelectorAll("nav.tabs button").forEach(x => x.setAttribute("aria-selected", x === b));
  document.querySelectorAll(".panel").forEach(p => p.hidden = p.id !== "tab-" + b.dataset.tab);
  current = b.dataset.tab; renderers[current]();
}));
const themes = ["auto", "light", "dark"]; let ti = 0;
try { const saved = localStorage.getItem("ai-trust-theme"); if (saved) ti = Math.max(0, themes.indexOf(saved)); } catch (e) {}
function applyTheme() {
  const t = themes[ti];
  if (t === "auto") document.documentElement.removeAttribute("data-theme"); else document.documentElement.setAttribute("data-theme", t);
  document.getElementById("themeBtn").textContent = "Theme: " + t;
  try { localStorage.setItem("ai-trust-theme", t); } catch (e) {}
  kpis(); renderers[current]();
}
document.getElementById("themeBtn").addEventListener("click", () => { ti = (ti + 1) % 3; applyTheme(); });
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { kpis(); renderers[current](); });
// deep link: ai_trust_dashboard.html#why opens that tab
const startTab = location.hash.slice(1);
if (renderers[startTab]) {
  document.querySelectorAll("nav.tabs button").forEach(x => x.setAttribute("aria-selected", x.dataset.tab === startTab));
  document.querySelectorAll(".panel").forEach(p => p.hidden = p.id !== "tab-" + startTab);
  current = startTab;
}
applyTheme();
</script>
</body>
</html>
"""


def main() -> None:
    data = collect()
    html = (TEMPLATE.replace("__PLOTLY__", po.get_plotlyjs())
            .replace("__DATA__", json.dumps(data))
            .replace("__MINN__", str(MIN_N)))
    out = DASHBOARD / "ai_trust_dashboard.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
