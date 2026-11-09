# 02 · Architecture

How the project is wired together: one pipeline, nine steps, each a module in [src/](../src/).

## The pipeline runner

[run_pipeline.py](../run_pipeline.py) runs the steps in order. Each step is a Python module with a `main()` function. The runner imports and calls them one by one.

- Run everything: `python run_pipeline.py`
- Run one step: `python run_pipeline.py --only models`
- Resume from a step: `python run_pipeline.py --from descriptives`

## The nine steps

```mermaid
flowchart LR
    A[download] --> B[harmonise]
    B --> C[validate]
    C --> D[build_db]
    D --> E[descriptives]
    E --> F[models]
    F --> G[robustness]
    G --> H[dashboard]
    H --> I[memo]
```

Each box is one module in `src/` run in this fixed order; later steps read files written by earlier ones.

| Step | Module | Reads | Writes |
|---|---|---|---|
| download | [download.py](../src/download.py) | internet | `data/raw/` |
| harmonise | [harmonise.py](../src/harmonise.py) | raw CSVs + mappings | `respondents.parquet`, bridge tables |
| validate | [validate.py](../src/validate.py) | parquet + official JSON | `benchmark_check.csv` |
| build_db | [build_db.py](../src/build_db.py) | parquet + SQL files | `survey.duckdb`, Power BI CSVs |
| descriptives | [descriptives.py](../src/descriptives.py) | parquet | tables + figures 1–11 |
| models | [models.py](../src/models.py) | parquet | model tables + forest plots |
| robustness | [robustness.py](../src/robustness.py) | parquet | robustness tables + figures |
| dashboard | [dashboard.py](../src/dashboard.py) | tables | `ai_trust_dashboard.html` |
| memo | [memo.py](../src/memo.py) | memo markdown | memo HTML + PDF |
| build_site | [build_site.py](../src/build_site.py) | dashboard, memo, figures, tables | `site/` static website (deploy) |

## Shared helpers (not pipeline steps)

- [config.py](../src/config.py) — all file paths and constants (e.g. `MIN_N = 100`) in one place.
- [load.py](../src/load.py) — reads raw CSVs, keeping only needed columns.
- [multiselect.py](../src/multiselect.py) — splits `;`-separated answers into columns.
- [stats_utils.py](../src/stats_utils.py) — Wilson confidence intervals, raking, ordered logit.
- [viz.py](../src/viz.py) — shared chart colours and styling.

## Why a step pipeline

- **Safety:** `validate` sits early and stops the run if the numbers look wrong.
- **Speed:** you can rerun just one step while developing, not the whole thing.
- **Clarity:** each module has one job and one `main()`.
