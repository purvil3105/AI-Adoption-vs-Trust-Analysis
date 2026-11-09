"""Load the harmonised parquet files into DuckDB, run the SQL layer, and export Power BI / Tableau files.

Usage:  python -m src.build_db
"""
import duckdb

from src.config import DB_PATH, POWERBI, PROCESSED, SQL_DIR

TABLES = ["respondents", "respondent_ai_tasks", "respondent_ai_tools", "respondent_ai_frustrations",
          "respondent_ai_benefits", "respondent_ai_challenges"]

# Slim fact table for BI tools (keeps the file small and the model simple).
FACT_COLS = """resp_id, survey_year, is_professional, age_group, country, country_group, org_size, role_family,
    exp_bucket, years_code, ed_level, ai_use_status, ai_use_frequency, ai_agents, uses_ai, uses_or_plans_ai,
    trust_label, trust_score, trusts_ai, distrusts_ai, highly_distrusts_ai, in_trust_base_users,
    in_trust_base_official, sentiment_label, favorable_ai, complex_label, ai_threat,
    frus_almost_right, frus_debugging_slower, frus_less_confident, frus_hard_to_understand, n_ai_tasks, n_ai_tools"""

EXPORTS = {
    "fact_respondents": f"SELECT {FACT_COLS} FROM respondents",
    "bridge_ai_tasks": "SELECT resp_id, survey_year, task, intensity FROM respondent_ai_tasks",
    "bridge_ai_tools": "SELECT resp_id, survey_year, tool, vendor, tool_kind FROM respondent_ai_tools",
    "bridge_ai_frustrations": "SELECT resp_id, survey_year, frustration FROM respondent_ai_frustrations",
    "dim_experience": "SELECT * FROM dim_experience",
    "dim_org_size": "SELECT * FROM dim_org_size",
    "dim_role": "SELECT role_family, n_total, CAST(years_present AS VARCHAR) AS years_present FROM dim_role",
    "dim_country": "SELECT * FROM dim_country",
    "dim_trust": "SELECT * FROM dim_trust",
    "dim_year": "SELECT DISTINCT survey_year FROM respondents ORDER BY 1",
    "agg_segment_metrics": "SELECT * FROM segment_metrics",
    "agg_task_trust": "SELECT * FROM task_trust",
    "agg_tool_trust": "SELECT * FROM tool_trust",
    "agg_headline": "SELECT * FROM headline",
}


def run_sql_file(con, path) -> None:
    # drop full-line comments first (they may contain ';'), then run statement by statement
    code = "\n".join(l for l in path.read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--"))
    for stmt in code.split(";"):
        if stmt.strip():
            con.execute(stmt)


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = duckdb.connect(str(DB_PATH))
    for t in TABLES:
        con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_parquet('{(PROCESSED / (t + '.parquet')).as_posix()}')")
        print(f"table {t:28s} {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>9,} rows")
    for f in sorted(SQL_DIR.glob("*.sql")):
        run_sql_file(con, f)
        print(f"ran {f.name}")
    for name, q in EXPORTS.items():
        out = (POWERBI / f"{name}.csv").as_posix()
        con.execute(f"COPY ({q}) TO '{out}' (HEADER, DELIMITER ',')")
    print(f"exported {len(EXPORTS)} CSV files -> {POWERBI}")
    print(con.execute("SELECT * FROM headline").df().round(3).to_string())
    con.close()


if __name__ == "__main__":
    main()
