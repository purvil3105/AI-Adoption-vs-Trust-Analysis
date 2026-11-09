"""Project-wide paths and constants."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
POWERBI = PROCESSED / "powerbi"
MAPPINGS = ROOT / "mappings"
SQL_DIR = ROOT / "sql"
FIGURES = ROOT / "reports" / "figures"
TABLES = ROOT / "reports" / "tables"
DASHBOARD = ROOT / "dashboard"

YEARS = (2023, 2024, 2025)
DB_PATH = PROCESSED / "survey.duckdb"
RESPONDENTS_PARQUET = PROCESSED / "respondents.parquet"

# Segments smaller than this are suppressed in charts, tables and the dashboard.
MIN_N = 100
# Number of individual countries kept before grouping the rest into "Other".
TOP_COUNTRIES = 15

for _p in (INTERIM, PROCESSED, POWERBI, FIGURES, TABLES):
    _p.mkdir(parents=True, exist_ok=True)
