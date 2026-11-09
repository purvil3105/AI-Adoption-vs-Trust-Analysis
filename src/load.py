"""Read the raw survey files, keeping only the columns the crosswalk uses."""
import pandas as pd

from src.config import MAPPINGS, RAW, YEARS

COMMON = ["ResponseId", "MainBranch", "Age", "Country", "OrgSize", "DevType", "YearsCode", "EdLevel",
          "ICorPM", "AISelect", "AISent"]

# Year-specific raw columns (see mappings/question_crosswalk.csv for the meaning of each).
# The AITool "interested / plan / don't plan" columns are loaded only to know who answered the task matrix.
AITOOL_23_24 = ["AIToolCurrently Using", "AIToolInterested in Using", "AIToolNot interested in Using"]
AITOOL_25 = ["AIToolCurrently mostly AI", "AIToolCurrently partially AI", "AIToolPlan to mostly use AI",
             "AIToolPlan to partially use AI", "AIToolDon't plan to use AI for this task"]

RAW_COLS = {
    2023: COMMON + AITOOL_23_24 + ["YearsCodePro", "AIBen", "AIAcc",
                                   "AISearchHaveWorkedWith", "AIDevHaveWorkedWith"],
    2024: COMMON + AITOOL_23_24 + ["YearsCodePro", "AIAcc", "AIBen", "AIComplex", "AIThreat",
                                   "AISearchDevHaveWorkedWith", "AIChallenges"],
    2025: COMMON + AITOOL_25 + ["WorkExp", "AIAcc", "AIComplex", "AIThreat", "AIModelsHaveWorkedWith",
                                "DevEnvsHaveWorkedWith", "AIFrustration", "AIAgents"],
}


def load_crosswalk() -> pd.DataFrame:
    return pd.read_csv(MAPPINGS / "question_crosswalk.csv", dtype=str).fillna("")


def normalise_text(s: pd.Series) -> pd.Series:
    """Straighten curly quotes and trim whitespace so labels match value_maps.yaml."""
    return (s.str.replace("’", "'", regex=False)
             .str.replace("‘", "'", regex=False)
             .str.strip())


def load_year(year: int) -> pd.DataFrame:
    df = pd.read_csv(RAW / str(year) / "results.csv", dtype=str, usecols=RAW_COLS[year], encoding="utf-8")
    for c in df.columns:
        df[c] = normalise_text(df[c])
    df["survey_year"] = year
    df["resp_id"] = f"{year}_" + df["ResponseId"].str.zfill(6)
    return df


def raw_row_counts() -> dict[int, int]:
    """Row counts straight from the files (used by validation)."""
    return {y: len(pd.read_csv(RAW / str(y) / "results.csv", usecols=["ResponseId"])) for y in YEARS}
