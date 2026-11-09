# Assumptions, decisions and work log

This file lists **everything that was built, assumed or decided** while building the project end to end without being able to ask questions. Each judgement call says what was chosen, why, and where to change it if you disagree.

---

## 1. What was delivered

| Deliverable | Location | Status |
|---|---|---|
| Phase-wise plan | `PROJECT_PLAN.md` | ✅ (written first, then followed) |
| One-command pipeline | `run_pipeline.py` (9 steps) | ✅ full run verified end to end |
| Raw data download (reproducible) | `src/download.py` → `data/raw/<year>/` | ✅ 2023, 2024, 2025 + official result tables |
| Question crosswalk (every mapping documented) | `mappings/question_crosswalk.csv` | ✅ 21 variables, tiers A/B/C |
| Answer recodes | `mappings/value_maps.yaml` | ✅ pipeline fails if a raw label is unmapped |
| Data dictionary (exact wording per year) | `reports/data_dictionary.md` | ✅ generated from the official schemas |
| Clean combined dataset | `data/processed/respondents.parquet` (203,812 rows) + 5 bridge tables | ✅ |
| Validation vs official tables | `src/validate.py`, `reports/tables/benchmark_check.csv` | ✅ 84/84 within ±1 pp (max 0.60 pp) |
| SQL layer | `sql/01_views.sql`, `sql/02_segment_metrics.sql`, `data/processed/survey.duckdb` | ✅ |
| Power BI / Tableau inputs | `data/processed/powerbi/*.csv` (star schema + aggregates) | ✅ |
| Descriptive analysis + 12 charts | `src/descriptives.py`, `reports/figures/fig01–fig11` (incl. fig06b) | ✅ |
| Logistic regressions (5 models) | `src/models.py`, `reports/tables/model_*.csv`, `fig12a/b`, `fig13` | ✅ |
| Bias and robustness (reweighting + 12 specifications) | `src/robustness.py`, `fig14`, `fig15` | ✅ |
| Interactive dashboard | `dashboard/ai_trust_dashboard.html` | ✅ 5 pages, filters, data tables, light/dark |
| Power BI build kit | `dashboard/powerbi/` (DAX, theme, guide) | ✅ (`.pbix` itself not created; see D20) |
| Insight memo | `reports/insight_memo.md` / `.html` / `.pdf` | ✅ |
| Notebooks (executed, with outputs) | `notebooks/01–04` | ✅ |
| README | `README.md` | ✅ |

---

## 2. What was done, phase by phase

1. **Setup:** created the folder structure, a Python virtual environment (`.venv`), pinned `requirements.txt` and `.gitignore`, and ran `git init`.
2. **Data:** downloaded the three survey years, their schemas and questionnaires, plus Stack Overflow's **official aggregated result tables** (`official_json/ai.json`), which serve as the benchmark. Profiled every AI and demographic column and every year's skip logic.
3. **Mapping:** built the crosswalk and value maps; found and documented the 2023 column swap and the changing skip logic.
4. **Cleaning:** wrote `load.py` and `harmonise.py`. Straightened curly quotes, recoded every label, converted experience to numbers, created outcomes and analysis flags, and grouped countries and roles.
5. **Multi-select:** split answers into 0/1 dummies (blank when the question was skipped) plus long bridge tables for tasks, tools, frustrations, benefits and challenges.
6. **SQL:** loaded everything into DuckDB, built dimensions and views, wrote segment metrics in SQL, and exported CSVs for BI tools.
7. **Descriptives:** built adoption, trust and distrust tables by year × experience, role, company size, country, age, task, use frequency, agents and frustration, all with Wilson 95% CIs and an n ≥ 100 rule.
8. **Models:** fitted a pooled 2023–2025 logit, a pooled model with tasks, and three nested 2025 models. Reported odds ratios plus average marginal effects.
9. **Bias:** compared sample composition across years, raked 2024 and 2025 to the 2023 mix, and ran 12 robustness specifications.
10. **Dashboard:** built a self-contained HTML dashboard and the Power BI kit. Checked every tab in headless Chrome, in light and dark mode.
11. **Memo, README, notebooks:** wrote the memo and rendered it to PDF, wrote the README, executed the notebooks, and ran the full pipeline end to end.

---

## 3. Assumptions and decisions

### Data and scope
- **D1 – Years 2023–2025 only.** A 2026 survey has since been published (survey.stackoverflow.co lists it). The brief specifies 2023–2025, so 2026 was **not** added. To add it later, add `2026` to `YEARS` in `src/config.py` and extend the crosswalk and value maps.
- **D2 – Data source.** The old ZIP download URLs return 404. The data now lives in the GitHub archive `StackExchange/Survey/packages/archive/<year>`, stored with Git LFS, so `src/download.py` uses `media.githubusercontent.com` links.
- **D3 – Benchmark = official JSON tables**, never media articles. These are the only Stack Overflow figures quoted in the memo: 2025 trust 32.8%, distrust 45.7%, "almost right" 66.0%, and 84% using or planning to use AI.
- **D4 – Main population = professional developers** (`MainBranch = "I am a developer by profession"`, identical option text in all years). "All coders" appears as a robustness check.

### Comparability (the tricky part)
- **D5 – Trust base = current AI users.** The trust question was shown to users + planners (2023), users only (2024) and everyone (2025). Current AI users is the only group asked in all three years, so all trend comparisons use it.
- **D6 – The official 2023 table header is misleading.** It says the base is 39,042 respondents (AI users), but its counts add up to 61,396 (users + planners). The pipeline reproduces the official percentages using the 61,396 base. This is documented in `harmonise.py` and the crosswalk.
- **D7 – 2023 column swap.** Trust is stored in `AIBen` and benefits in `AIAcc` in 2023 only. This was confirmed from the values and the official schema.
- **D8 – Trust and distrust definitions.** Trust = "Highly" or "Somewhat" trust; distrust = "Somewhat" or "Highly" distrust. "Neither" **stays in the denominator**, matching Stack Overflow's method.
- **D9 – Adoption.** Adoption = "Yes" among those who answered the AI-use question. 2025's daily, weekly and monthly answers are collapsed into "Yes" (tier B).
- **D10 – Main experience variable = `YearsCode`** (years coding including education). Its wording is identical in all years; only the answer format changed. 2023/24 values "Less than 1 year" → 0.5 and "More than 50 years" → 51; 2025 values above 50 are capped at 51. Buckets: 0–4, 5–9, 10–19, 20–29, 30+. Professional experience (`YearsCodePro` in 2023/24, `WorkExp` in 2025) is a different concept, so it is used only as a robustness check (tier B-).
- **D11 – Company size.** 2025 merged "2 to 9" and "10 to 19" into "Less than 20", so all years use: Solo / Under 20 / 20–99 / 100–999 / 1k–9.9k / 10k+. "I don't know" counts as missing.
- **D12 – Roles.** 49 job-title labels (renamed across years) are mapped to 13 role families. "Architect, software or solutions" exists only in 2025 and is kept as its own family rather than forced into another one. Respondents whose job title is "Student" are dropped from the regressions only (they are ambiguous among professional developers).
- **D13 – Countries.** The 15 largest countries (pooled) are kept, the rest become "Other". Long official names are shortened (e.g. "United Kingdom of Great Britain and Northern Ireland" → "United Kingdom"), and Macedonia is harmonised.
- **D14 – Age.** "55–64" and "65+" are merged into "55+"; "Prefer not to say" counts as missing. "Under 18" exists only in 2023/24.
- **D15 – Type of AI use.** For 2025, "currently uses AI for task X" = "mostly AI" **or** "partially AI" from the new matrix question. "Debugging and getting help" (2023/24) is treated as the same task as "Debugging or fixing code" (2025). Tasks offered only in some years are left blank (not 0) in the other years.
- **D16 – AI tools.** 2023/24 ask about products (ChatGPT, Copilot, …); 2025 asks about LLM *models* plus AI-native editors. Tools are therefore descriptive only and never compared as a trend from 2024 to 2025. AI editors counted for 2025: Cursor, Claude Code, Windsurf, Cline/Roo, Aider, Lovable, Bolt, Trae.
- **D17 – Missing data.** If a respondent skipped a whole multi-select question, all its dummies are blank. Categorical controls get an explicit "Missing" level so no rows are silently dropped. A complete-case model is one of the robustness checks.

### Analysis
- **D18 – Reporting rules.** Segments with fewer than **100** AI users are hidden. Proportions use Wilson 95% CIs. Every chart states its base.
- **D19 – Models.**
  - Logistic regression (statsmodels) with **HC1 robust** standard errors.
  - Reference levels: year 2023, 0–4 yrs, full-stack developer, 100–999 employees, United States, age 25–34, individual contributor, daily use, no agents.
  - The 2025 nested models use **one fixed sample** (AI users who answered both the task and the frustration questions, n = 18,651), so coefficients are comparable across steps.
  - The "I don't use AI tools regularly" frustration is left out of the models because it duplicates use frequency; "Other" is also left out.
  - Effects are reported as odds ratios plus **average marginal effects** in percentage points.
- **D20 – Ordered logit.** statsmodels' `OrderedModel` uses numerical gradients and was far too slow on about 80,000 rows. The same model was re-implemented with analytic gradients (`src/stats_utils.ordered_logit`). It was **validated against statsmodels on a sample**: coefficients match to four decimals and standard errors are identical, at about 23× the speed.
- **D21 – Reweighting.** 2024 and 2025 professional respondents are raked to the 2023 margins of country group, years-coding bucket, age group and company size. Weights are trimmed to 0.2–5. Role is **not** a raking variable because "Architect" has no 2023 counterpart. The weighted regression uses the raking weights as variance weights with HC1 errors.
- **D22 – Causality.** All results are described as **associations**. In particular, "people who use AI for riskier tasks distrust it less" is read as trusting users delegating more, not as tasks building trust.

### Tools and environment
- **D23 – Python 3.11** (already installed) instead of 3.12.
- **D24 – pandas pinned to 2.3.3.** pandas 3.x DLLs were **blocked by Windows Smart App Control** on this machine. 2.3.3 is a well-established release and works.
- **D25 – Dashboard = self-contained HTML (Plotly.js embedded, works offline) plus a Power BI build kit, instead of a `.pbix` file.**
  - A `.pbix` can only be authored in the Power BI Desktop interface, which wasn't installed here and can't be operated without you present.
  - The kit (`dashboard/powerbi/`) contains the star-schema CSVs, DAX measures, a theme in the same validated colours, and a step-by-step build guide (about 30–45 minutes).
- **D26 – Free services only.** No paid service or API was used. Plotly.js is embedded, so the dashboard needs no CDN or internet. The PDF memo is rendered with the free headless Microsoft Edge already on Windows.
- **D27 – Git.** The repository was initialised (`git init`) but **nothing was committed or pushed**. Publishing to GitHub is an outward-facing action that should be yours. `.gitignore` already excludes the raw data and large row-level CSVs.
- **D28 – Reproducibility check.** The environment's safety guard blocked bulk-deleting the generated `data/processed` folder. Instead, the full pipeline was re-run from raw with one command, overwriting every output. The DuckDB file is always rebuilt from scratch, and the headline numbers matched.
- **D29 – Chart colours** come from a validated, colour-blind-checked palette. It was run through a palette validator: all checks pass, and the one contrast warning (aqua) is handled by direct labels and data tables.
- **D30 – Notebooks are thin.** They call the `src/` functions and display the results, so the logic lives in one place. `04_robustness` reads saved results rather than refitting, which takes about 6 minutes.

---

## 4. Where this differs from the original plan

| Plan said | What happened | Why |
|---|---|---|
| Python 3.12 | Python 3.11 | Already installed; everything works on 3.11 |
| Download ZIPs from survey.stackoverflow.co | GitHub LFS archive | ZIP links now return 404 |
| `ai_trust.pbix` | HTML dashboard + Power BI kit | See D25 |
| Ordered logit via statsmodels | Validated custom implementation | See D20 |
| "Almost right" expected to be a key driver | It is **not**, once controls are added; "debugging takes longer" is | That is what the data shows; reported honestly |
| Delete interim/processed and rerun | Full rerun that overwrites outputs | See D28 |

---

## 5. Headline numbers (for quick reference)

| Metric (professional developers) | 2023 | 2024 | 2025 |
|---|---|---|---|
| Use AI tools | 44.2% | 63.3% | 80.8% |
| Trust AI accuracy (AI users) | 46.3% | 41.4% | 38.4% |
| Distrust AI accuracy (AI users) | 25.1% | 31.3% | 38.0% |
| Distrust, reweighted to the 2023 mix | 25.1% | 32.8% | 38.6% |

Key model results:
- **Year:** odds of distrust 1.87× higher in 2025 than in 2023 (+13 pp).
- **Experience:** 30+ vs 0–4 years ≈ 3× the odds (+21 to +29 pp).
- **Use frequency:** monthly vs daily = 3.3× the odds (+24 pp).
- **"Debugging takes longer":** OR 2.2 (+15 pp).
- **"Almost right":** OR 0.97, not significant.
- **Company size:** no association once controls are added.

---

## 6. What you may want to do next

1. **Open** `dashboard/ai_trust_dashboard.html` and `reports/insight_memo.pdf`.
2. **Optional:** build the Power BI version with `dashboard/powerbi/POWERBI_BUILD_GUIDE.md`.
3. **Publish to GitHub:** create a public repo, then `git add . && git commit -m "AI adoption vs trust analysis" && git push`. Raw data is git-ignored.
4. **Resume bullets,** with the real numbers filled in:
   - Built an end-to-end analytics pipeline (Python, DuckDB SQL, Plotly; Power BI-ready star schema) on **203,812** Stack Overflow survey responses from 2023–2025. Harmonised **21** questions across years with a documented crosswalk and comparability tiers, and reproduced all **84** published benchmark percentages within ±1 pp.
   - Found that distrust of AI among professional AI users rose from **25% to 38%** while adoption climbed from **44% to 81%**. The decline held after controls (OR 1.87) and after reweighting to a fixed respondent mix.
   - Used logistic regression with controls and 12 robustness checks to show that **experience (≈3× odds)** and **slow debugging of AI output (+15 pp)**, not the widely cited "almost right" frustration, are associated with distrust. Delivered a 3-page insight memo and a 5-page interactive dashboard.
