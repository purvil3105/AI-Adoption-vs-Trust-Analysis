# Developer AI Adoption vs Trust Analytics: Project Plan

> **Core question:** Developers use AI more every year but trust it less. Who trusts it, and why?
>
> **Audience for the output:** developer-tools product teams, engineering leaders, and anyone planning an AI rollout.

---

## 0. At a glance

| Item | Choice |
|---|---|
| Data | Stack Overflow Developer Survey 2023, 2024 and 2025 (free, public) |
| Language | Python 3.12 |
| Analysis libraries | pandas, numpy, statsmodels, matplotlib/seaborn, pyyaml |
| SQL engine | **DuckDB** (free, no server to install, runs SQL straight on CSV/Parquet files) |
| Storage format | Parquet (small, fast, and Power BI can read it) |
| Notebooks / IDE | VS Code + Jupyter extension |
| Dashboard | **Power BI Desktop** (free on Windows). Alternative: **Tableau Public** (free, but everything you save is public, which is fine for open data) |
| Version control / portfolio | Git + GitHub (free) |
| Memo | Markdown, exported to PDF |
| Total cost | **₹0 / $0** |

**Estimated effort:** about 3 to 4 weeks at 1 to 2 hours a day (roughly 35 to 50 hours).

| Phase | What | Time |
|---|---|---|
| 1 | Setup | 0.5 day |
| 2 | Get and understand the data | 1 to 2 days |
| 3 | Map questions across years (the tricky part) | 2 to 3 days |
| 4 | Clean and harmonise | 2 to 3 days |
| 5 | Split multi-select answers | 1 day |
| 6 | SQL layer (DuckDB) | 1 day |
| 7 | Descriptive analysis: adoption vs trust | 2 to 3 days |
| 8 | Drivers of distrust: logistic regression | 3 days |
| 9 | Sampling bias and robustness checks | 1 to 2 days |
| 10 | Dashboard | 2 to 3 days |
| 11 | Insight memo, README, publish | 2 days |

---

## Folder structure (create this in Phase 1)

```
AI Adoption vs Trust Analysis/
├── data/
│   ├── raw/                 # original zips/CSVs, never edited (git-ignored)
│   │   ├── 2023/
│   │   ├── 2024/
│   │   └── 2025/
│   ├── interim/             # per-year cleaned files
│   └── processed/           # final combined Parquet + DuckDB file (git-ignored)
├── mappings/
│   ├── question_crosswalk.csv   # which column in each year = which harmonised variable
│   └── value_maps.yaml          # how answer labels are recoded per year
├── notebooks/
│   ├── 01_explore_raw.ipynb
│   ├── 02_descriptives.ipynb
│   ├── 03_regression.ipynb
│   └── 04_robustness.ipynb
├── src/
│   ├── load.py              # read raw files
│   ├── harmonise.py         # apply crosswalk + value maps
│   ├── multiselect.py       # split ";"-separated answers into yes/no columns
│   ├── build_db.py          # write Parquet + DuckDB tables
│   └── models.py            # regression helpers
├── sql/
│   ├── 01_views.sql
│   └── 02_segment_metrics.sql
├── dashboard/
│   └── ai_trust.pbix
├── reports/
│   ├── figures/
│   ├── insight_memo.md
│   └── data_dictionary.md
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Phase 1: Setup

**Goal:** a working environment and an empty, organised repo.

1. Install (all free):
   - Python 3.12 from python.org (tick "Add to PATH")
   - VS Code + the Python and Jupyter extensions
   - Git
   - Power BI Desktop from the Microsoft Store
2. Create a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install pandas numpy pyarrow duckdb statsmodels matplotlib seaborn pyyaml jupyter
   pip freeze > requirements.txt
   ```
3. `git init`, create the folders above, and add a `.gitignore` containing `data/raw/`, `data/processed/`, `.venv/` and `*.duckdb`.
4. Create a GitHub repo (public, so it works as a portfolio piece).

**Done when:** `python -c "import pandas, duckdb, statsmodels"` runs without errors and the first commit is pushed.

---

## Phase 2: Get and understand the data

**Goal:** know exactly which questions exist each year, how they were worded, and who was asked them.

1. Download the 2023, 2024 and 2025 zips from **https://survey.stackoverflow.co/** into `data/raw/<year>/`. Each zip contains:
   - `survey_results_public.csv`: one row per respondent
   - `survey_results_schema.csv`: column name and question text
   - the questionnaire PDF: the exact wording, answer options and **skip logic**
   - a README and licence file (the data is under the **Open Database License (ODbL)**, so credit Stack Overflow in your README)
2. In `01_explore_raw.ipynb`, for each year record:
   - number of rows and columns
   - the full list of AI-related columns (names starting with `AI`)
   - the demographic columns you'll need: `MainBranch`, `Age`, `Country`, `DevType`, `OrgSize`, `YearsCode` / `YearsCodePro` / `WorkExp` (check which exist each year), `RemoteWork`, `EdLevel`, `Employment`
3. **Read the questionnaire PDFs for skip logic.** For example, check whether the trust question (`AIAcc`) was shown to everyone or only to people who use or plan to use AI. That decides the correct denominator for every trust percentage.
4. Write down the official headline figures from each year's results page (AI use %, trust %, distrust %) in a "benchmark" table. You'll use it in Phase 4 to check your own numbers, and these are the **only** figures you quote. Don't use numbers from media articles, which often disagree.

| Metric | 2023 official | 2024 official | 2025 official | Your number | Matches? |
|---|---|---|---|---|---|
| Use or plan to use AI tools | | | 84% (from release) | | |
| Trust AI accuracy (highly + somewhat) | | | | | |
| Distrust AI accuracy (highly + somewhat) | | | | | |
| "Almost right, but not quite" frustration (2025) | — | — | | | |

**Deliverable:** a short `reports/data_dictionary.md` listing each question you'll use, with its exact wording in each year.

---

## Phase 3: Map questions across years (the tricky part)

**Goal:** one documented crosswalk saying which questions can be compared across years and how.

1. Build `mappings/question_crosswalk.csv` with these columns:

   | harmonised_var | col_2023 | col_2024 | col_2025 | wording_changed? | options_changed? | comparability | notes |
   |---|---|---|---|---|---|---|---|
   | ai_use_status | AISelect | AISelect | AISelect | no | **yes** (2025 splits "Yes" by frequency) | Harmonisable | Collapse 2025 daily/weekly/monthly into "Yes" |
   | ai_trust_accuracy | AIAcc | AIAcc | AIAcc | check | check | check | Check skip logic each year |
   | ai_sentiment | AISent | AISent | AISent | check | check | check | |
   | almost_right_frustration | — | — | AIFrustration (check name) | — | — | 2025 only | Not comparable across years |

   *(The column names above are examples to verify against each year's schema file, not confirmed facts.)*

2. Give every variable one of three **comparability tiers**:
   - **Tier A, identical:** same wording, same options. Fine for trend comparisons.
   - **Tier B, harmonisable:** small changes that can be mapped one-to-one or collapsed (e.g. splitting "Yes" into frequencies, renamed age buckets, renamed tools). Usable for trends after mapping, flagged in charts.
   - **Tier C, not comparable:** new question, changed meaning, or a different audience. **Analyse within its own year only.**
3. Build `mappings/value_maps.yaml` for answer-label recoding, for example:
   ```yaml
   ai_use_status:
     2025:
       "Yes, I use AI tools daily": "Yes"
       "Yes, I use AI tools weekly": "Yes"
       "Yes, I use AI tools monthly or infrequently": "Yes"
       "No, but I plan to soon": "Plan to"
       "No, and I don't plan to": "No"
   ```
4. Common things to harmonise: experience in years (convert "Less than 1 year" and "More than 50 years" to numbers, then bucket as 0–2, 3–5, 6–10, 11–20, 20+), country name spellings, org-size labels, role (`DevType`) labels, and AI tool names.

**Rule:** every recode lives in the crosswalk or the YAML file, **never** hard-coded in a notebook. That's what makes the project explainable.

**Done when:** every variable used anywhere in the project has a row in the crosswalk with a tier.

---

## Phase 4: Clean and harmonise

**Goal:** one tidy combined table, `respondents`, with one row per respondent per year.

1. `src/load.py`: read each year's CSV with `dtype=str` (so nothing is silently converted), and add `survey_year` and a `resp_id` such as `2024_000123`.
2. `src/harmonise.py`:
   - rename columns using the crosswalk
   - apply the value maps
   - convert experience fields to numbers and buckets
   - group `Country` into the top ~15 countries plus "Other"
   - group `DevType` into about 8 role families (e.g. Back-end, Front-end, Full-stack, Data/ML, DevOps/Cloud, Mobile, Manager/Lead, Student/Other)
   - group `OrgSize` into Solo / Small (2–99) / Mid (100–999) / Large (1,000+)
3. **Scope decision (document it):** the main analysis uses **professional developers** (`MainBranch` = "I am a developer by profession"). Students and hobbyists are a sensitivity check.
4. Create the analysis outcomes:
   - `uses_ai` = 1 if currently using AI tools
   - `trusts_ai` = 1 if "Highly trust" or "Somewhat trust"
   - `distrusts_ai` = 1 if "Somewhat distrust" or "Highly distrust"
   - keep the original 5-point trust scale too, for the ordinal model in Phase 9
5. Validation checks (put these in a script and rerun them every time):
   - row counts per year match the raw files
   - no unmapped answer labels (any label not found in the YAML raises an error)
   - your AI use % and trust % **match the official benchmark table** from Phase 2 (using the same denominator as Stack Overflow). If they don't match, fix your denominator before going further.
6. Save to `data/processed/respondents.parquet`.

---

## Phase 5: Split multi-select answers

**Goal:** turn answers like `"ChatGPT;GitHub Copilot;Claude"` into separate yes/no columns.

1. `src/multiselect.py` produces two outputs per multi-select question:
   - **Wide:** `pandas.Series.str.get_dummies(sep=";")` gives columns like `tool_chatgpt`, `tool_copilot`, ... with 0/1 values (good for regression).
   - **Long:** a bridge table `respondent_ai_tools(resp_id, survey_year, tool)` (good for SQL and Power BI).
2. Apply this to: AI tools / models used, AI uses in the workflow (writing code, debugging, documentation, learning, testing...), AI benefits, AI challenges, and AI frustrations (2025).
3. Normalise tool names across years (e.g. "Bing AI" vs "Microsoft Copilot") through `value_maps.yaml`, and mark renamed tools as Tier B.
4. **Keep "did not answer" separate from "did not select."** If the whole question is blank, every dummy is `NaN`, not 0.
5. Build summary features for the model, such as `n_ai_tools_used` and `uses_ai_for_code_generation`.

---

## Phase 6: SQL layer (DuckDB)

**Goal:** show SQL skills and give the dashboard clean tables to read.

1. `src/build_db.py` creates `data/processed/survey.duckdb` with:
   - `respondents` (fact table)
   - `respondent_ai_tools`, `respondent_ai_uses`, `respondent_ai_frustrations` (bridge tables)
   - `dim_country`, `dim_role`, `dim_org_size`, `dim_experience`
2. `sql/02_segment_metrics.sql` holds the reusable queries, for example:
   ```sql
   -- Adoption and trust by year and experience
   SELECT survey_year,
          experience_bucket,
          COUNT(*)                         AS n,
          AVG(uses_ai)                     AS adoption_rate,
          AVG(trusts_ai)    FILTER (WHERE ai_trust_accuracy IS NOT NULL) AS trust_rate,
          AVG(distrusts_ai) FILTER (WHERE ai_trust_accuracy IS NOT NULL) AS distrust_rate
   FROM respondents
   WHERE is_professional
   GROUP BY ALL
   HAVING COUNT(*) >= 100        -- suppress tiny segments
   ORDER BY 1, 2;
   ```
3. Export the final tables as Parquet/CSV into `data/processed/` for Power BI.

---

## Phase 7: Descriptive analysis (adoption vs trust)

**Goal:** answer "who trusts it?" with simple, honest charts.

In `02_descriptives.ipynb`:

1. **Headline trend:** adoption % and trust % by year on the same chart (Tier A/B variables only). This is the "using more, trusting less" story.
2. **Segment breakdowns** of adoption and trust by experience bucket, role family, org size, top countries, and AI use frequency (2025).
3. **The adoption–trust gap per segment:** a scatter with adoption on the x-axis and trust on the y-axis, one dot per segment, sized by n. Segments that use AI heavily but trust it little are the key finding for product teams.
4. **Trust by AI use type:** do people who use AI for code generation trust it less than people who use it for learning or documentation?
5. **2025 deep dive:** how common is the "almost right, but not quite" frustration, and how does trust look for people who report it versus those who don't?
6. Good habits on every chart:
   - show **95% confidence intervals** (Wilson intervals for proportions)
   - show **n** for each bar and hide segments with n < 100
   - put the denominator in the subtitle (e.g. "Base: professional developers who answered the trust question")
   - use the same colours for the same year everywhere
7. Save figures to `reports/figures/` as PNG.

---

## Phase 8: Drivers of distrust (logistic regression)

**Goal:** separate the factors linked to distrust from each other, using controls.

In `03_regression.ipynb` with `statsmodels.formula.api.logit`:

1. **Outcome:** `distrusts_ai` (1 = somewhat or highly distrust).
2. **Model 1, pooled 2023–2025** (Tier A/B variables only):
   ```python
   smf.logit(
       "distrusts_ai ~ C(survey_year) + C(experience_bucket) + C(role_family)"
       " + C(org_size) + C(country_group) + C(age_group) + uses_ai",
       data=pooled
   ).fit()
   ```
   This asks whether distrust rose between years even after controlling for who answered.
3. **Model 2, 2025 only** (adds the 2025-only variables):
   `+ C(ai_use_frequency) + uses_ai_for_code_gen + uses_ai_for_learning + ... + almost_right_frustration`
   This asks which matters most: experience, the type of AI use, or the "almost right" frustration.
4. **Build it up step by step** (demographics, then + use type, then + frustration) and show how the experience coefficient changes. If it shrinks a lot once frustration is added, that suggests experienced developers distrust AI *because* they notice the almost-right answers.
5. **Report results in plain language:**
   - odds ratios with 95% CIs, as a forest plot
   - **average marginal effects** (`result.get_margeff()`), e.g. "reporting the almost-right frustration is associated with a +X percentage-point higher chance of distrust, holding other factors constant"
   - pseudo-R², number of observations, and how many rows were dropped for missing data
6. **Missing data:** use complete cases for the main model and add an explicit "Missing" category for key controls as a check.
7. **Wording rule:** say "associated with," **never** "causes." This is cross-sectional, self-reported data.

---

## Phase 9: Sampling bias and robustness checks

**Goal:** be upfront about the fact that respondents chose to take part.

1. **Describe the bias.** Compare who answered each year (country mix, experience, role, age). Stack Overflow users who answer a long survey are not all developers: they skew toward engaged, English-speaking, Stack Overflow-active people.
2. **Composition check (reweighting).** Reweight 2024 and 2025 to match 2023's mix of country group × experience bucket × role family, using simple cell weights or raking. If trust still falls after reweighting, the decline isn't just "a different crowd answered." Report both weighted and unweighted numbers.
3. **Robustness models:**
   - ordinal logit on the full 5-point trust scale (`statsmodels.miscmodels.ordinal_model.OrderedModel`)
   - include students and hobbyists
   - drop the largest country (usually the US) and rerun
   - a different distrust definition (e.g. "highly distrust" only)
4. Put a results table in the notebook showing which findings hold up in every check. **Only those go in the headline memo.**
5. Write a **Limitations** section: self-selection, possible survey fatigue, wording changes (link to the crosswalk), questions shown only to certain respondents, and self-reported answers.

---

## Phase 10: Dashboard (Power BI Desktop)

**Goal:** an interactive view for product teams and engineering leaders.

1. Import the Parquet/CSV tables from Phase 6 and set up relationships (fact table → dimensions, fact → bridge tables).
2. Write DAX measures: `Adoption %`, `Trust %`, `Distrust %`, `Trust Gap = Adoption % − Trust %`, and `Respondents (n)`.
3. Pages:
   1. **Overview:** KPI cards for 2023/2024/2025 and the adoption vs trust trend line
   2. **Who trusts AI:** bars by experience, role, org size and country, with year and segment slicers
   3. **How AI is used:** trust by use type and by tool (from the bridge tables)
   4. **Why distrust (2025):** the almost-right frustration, the forest plot (as an image or a table of odds ratios)
   5. **Method & caveats:** data sources, the comparability tiers, minimum n, and the self-selection warning
4. Show n in tooltips and hide segments with n < 100.
5. Save as `dashboard/ai_trust.pbix` and export a PDF plus screenshots for the README.
   - Power BI's free "Publish to web" needs a work/school account. If you don't have one, use screenshots, a PDF, and a short screen recording. Or rebuild the main pages in **Tableau Public** for a free live link.

---

## Phase 11: Insight memo, README and publishing

**Goal:** turn the analysis into something a busy leader reads in 3 minutes.

1. **`reports/insight_memo.md`** (1–2 pages, exported to PDF):
   - **Headline** (one sentence)
   - **3–5 key findings**, each with one number, one chart, and a "so what" for product teams or rollout planners
   - **Recommendations** (e.g. "target accuracy and verification features at senior developers; 'almost right' answers are the main trust problem")
   - **Caveats** (self-selection, cross-sectional, wording changes)
   - quote only figures that match the official tables or that you calculated yourself, with the denominator stated
2. **`README.md`:** problem, data source and ODbL credit, the tech stack, how to reproduce (`pip install -r requirements.txt` → run `src/` scripts in order → open notebooks), key charts, a link to the memo and dashboard, and the limitations.
3. **Reproducibility check:** delete `data/interim` and `data/processed`, rerun the pipeline from raw, and make sure the numbers are identical.
4. Push to GitHub and pin the repo on your profile.

---

## Final checklist

- [ ] Every cross-year comparison uses only Tier A/B variables
- [ ] Every mapping is documented in `question_crosswalk.csv` / `value_maps.yaml`
- [ ] Your headline figures match Stack Overflow's official tables
- [ ] Every chart shows its base (denominator) and n
- [ ] Regression results are reported as odds ratios + marginal effects in plain language
- [ ] Main findings survive the robustness checks
- [ ] The memo uses "associated with," not "causes"
- [ ] The limitations section covers self-selection
- [ ] The pipeline reruns from raw data in one go
- [ ] The README credits the data under ODbL

---

## Example resume bullets (fill in your real numbers at the end)

- Built an end-to-end analytics pipeline (Python, DuckDB SQL, Power BI) on **~200k** Stack Overflow survey responses (2023–2025), harmonising **N** questions across years with a documented crosswalk and comparability tiers.
- Used logistic regression with demographic controls to identify drivers of AI distrust; found that the "almost right" frustration is associated with a **+X pp** higher chance of distrust, larger than the effect of experience level.
- Checked findings against self-selection bias by reweighting each year to a common respondent mix, and summarised the results in a 2-page memo and a 5-page dashboard for engineering leaders.
