"""Apply the crosswalk + value maps and build one tidy respondent table for 2023-2025.

Outputs (data/processed/):
  respondents.parquet               one row per respondent per year (harmonised + 0/1 dummies)
  respondent_ai_tasks.parquet       bridge: what respondents currently use AI for
  respondent_ai_tools.parquet       bridge: AI products / models / AI editors used
  respondent_ai_frustrations.parquet, respondent_ai_benefits.parquet, respondent_ai_challenges.parquet

Usage:  python -m src.harmonise
"""
import numpy as np
import pandas as pd
import yaml

from src.config import INTERIM, MAPPINGS, PROCESSED, RESPONDENTS_PARQUET, TOP_COUNTRIES, YEARS
from src.load import load_year
from src.multiselect import UnmappedLabelError, explode, map_items, to_dummies

VM = yaml.safe_load((MAPPINGS / "value_maps.yaml").read_text(encoding="utf-8"))

TRUST_COL = {2023: "AIBen", 2024: "AIAcc", 2025: "AIAcc"}       # 2023 columns are swapped!
BENEFIT_COL = {2023: "AIAcc", 2024: "AIBen"}
EXP_BINS = [0, 5, 10, 20, 30, np.inf]
EXP_LABELS = ["0-4 yrs", "5-9 yrs", "10-19 yrs", "20-29 yrs", "30+ yrs"]


def year_map(var: str, year: int) -> dict:
    block = VM[var]
    m = dict(block.get("all", {}))
    m.update(block.get(year, {}))
    return m


def recode(s: pd.Series, var: str, year: int) -> pd.Series:
    m = year_map(var, year)
    unmapped = sorted(set(s.dropna()) - set(m))
    if unmapped:
        raise UnmappedLabelError(f"{var} ({year}): unmapped labels {unmapped}")
    return s.map(m)


def years_to_num(s: pd.Series) -> pd.Series:
    s = s.replace({"Less than 1 year": "0.5", "More than 50 years": "51"})
    return pd.to_numeric(s, errors="coerce").clip(upper=51)


def exp_bucket(x: pd.Series) -> pd.Series:
    return pd.cut(x, EXP_BINS, right=False, labels=EXP_LABELS).astype("string")


def score(label: pd.Series) -> pd.Series:
    """'4 Somewhat trust' -> 4.0; non-numeric labels such as 'Unsure' -> NaN."""
    return pd.to_numeric(label.str.slice(0, 1), errors="coerce")


def flag(cond: pd.Series, known: pd.Series) -> pd.Series:
    """1.0/0.0 where `known`, else NaN."""
    return cond.astype(float).where(known)


# --------------------------------------------------------------------------------------------
def harmonise_year(year: int) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    raw = load_year(year)
    out = pd.DataFrame({"resp_id": raw["resp_id"], "survey_year": year})

    # ---- who answered ----
    out["main_branch"] = raw["MainBranch"]
    out["is_professional"] = (raw["MainBranch"] == "I am a developer by profession").astype(int)
    out["age_group"] = recode(raw["Age"], "age_group", year)
    out["country"] = raw["Country"].replace(VM["country"]["rename"])
    out["org_size"] = recode(raw["OrgSize"], "org_size", year)
    out["role_family"] = recode(raw["DevType"], "role_family", year)
    out["dev_type_raw"] = raw["DevType"]
    out["ed_level"] = recode(raw["EdLevel"], "ed_level", year)
    out["ic_or_pm"] = recode(raw["ICorPM"], "ic_or_pm", year)
    out["years_code"] = years_to_num(raw["YearsCode"])
    out["exp_bucket"] = exp_bucket(out["years_code"])
    pro_col = "WorkExp" if year == 2025 else "YearsCodePro"
    out["years_pro"] = years_to_num(raw[pro_col])
    out["pro_exp_bucket"] = exp_bucket(out["years_pro"])

    # ---- adoption ----
    out["ai_use_status"] = recode(raw["AISelect"], "ai_use_status", year)
    known = out["ai_use_status"].notna()
    out["uses_ai"] = flag(out["ai_use_status"] == "Yes", known)
    out["uses_or_plans_ai"] = flag(out["ai_use_status"].isin(["Yes", "Plan to"]), known)
    out["ai_use_frequency"] = (recode(raw["AISelect"], "ai_use_frequency", year) if year == 2025 else pd.NA)

    # ---- trust (the 2023 trust question lives in AIBen) ----
    out["trust_label"] = recode(raw[TRUST_COL[year]], "ai_trust", year)
    out["trust_score"] = score(out["trust_label"])
    tk = out["trust_score"].notna()
    out["trusts_ai"] = flag(out["trust_score"] >= 4, tk)
    out["distrusts_ai"] = flag(out["trust_score"] <= 2, tk)
    out["highly_distrusts_ai"] = flag(out["trust_score"] == 1, tk)
    # comparable base: current AI users who answered the trust question (same population every year)
    out["in_trust_base_users"] = ((out["uses_ai"] == 1) & tk).astype(int)
    # official base used by Stack Overflow's published tables = everyone who answered the trust question.
    # Because of skip logic that is users+planners (2023), users (2024), everyone (2025) -> not comparable.
    # (The 2023 official table header says 39,042 respondents, but its counts sum to 61,396 = users+planners.)
    out["in_trust_base_official"] = tk.astype(int)

    # ---- sentiment / complexity / threat ----
    out["sentiment_label"] = recode(raw["AISent"], "ai_sentiment", year)
    out["sentiment_score"] = score(out["sentiment_label"])
    out["favorable_ai"] = flag(out["sentiment_score"] >= 4, out["sentiment_label"].notna())
    if year >= 2024:
        out["complex_label"] = recode(raw["AIComplex"], "ai_complex", year)
        out["ai_good_at_complex"] = flag(score(out["complex_label"]) >= 4, out["complex_label"].notna())
        out["ai_threat"] = recode(raw["AIThreat"], "ai_threat", year)
        out["sees_ai_threat"] = flag(out["ai_threat"] == "Yes", out["ai_threat"].notna())
    if year == 2025:
        out["ai_agents"] = recode(raw["AIAgents"], "ai_agents", year)

    bridges = {}
    rid = out["resp_id"]

    # ---- AI tasks (type of AI use) ----
    task_map = year_map("ai_tasks", year)
    task_keys = [k for k, yrs in VM["ai_tasks_years"].items() if year in yrs]
    if year == 2025:
        parts = []
        for col, level in (("AIToolCurrently mostly AI", "mostly"), ("AIToolCurrently partially AI", "partially")):
            parts.append(explode(raw, col).assign(intensity=level))
        tasks_long = pd.concat(parts, ignore_index=True)
        task_cols = [c for c in raw.columns if c.startswith("AITool")]
    else:
        tasks_long = explode(raw, "AIToolCurrently Using").assign(intensity="current")
        task_cols = [c for c in raw.columns if c.startswith("AITool")]
    tasks_long = map_items(tasks_long, task_map, f"ai_tasks {year}")
    answered = raw[task_cols].notna().any(axis=1)
    out["answered_ai_tasks"] = answered.astype(int)
    dummies = to_dummies(tasks_long, rid, answered, "task_", task_keys)
    out = pd.concat([out, dummies], axis=1)
    out["n_ai_tasks"] = dummies.drop(columns=["task_other"], errors="ignore").sum(axis=1, min_count=1)
    bridges["respondent_ai_tasks"] = tasks_long.rename(columns={"key": "task", "item": "task_raw"})

    # ---- AI tools / models ----
    tool_sources = {2023: ["AISearchHaveWorkedWith", "AIDevHaveWorkedWith"],
                    2024: ["AISearchDevHaveWorkedWith"],
                    2025: ["AIModelsHaveWorkedWith"]}[year]
    tools_long = pd.concat([explode(raw, c).assign(source=c) for c in tool_sources], ignore_index=True)
    tool_answered = raw[tool_sources].notna().any(axis=1)
    if year == 2025:
        editors = explode(raw, "DevEnvsHaveWorkedWith").assign(source="DevEnvsHaveWorkedWith")
        editors = editors[editors["item"].isin(VM["ai_editors_2025"])]
        tools_long = pd.concat([tools_long, editors], ignore_index=True)
        tool_answered = tool_answered | raw["DevEnvsHaveWorkedWith"].notna()
    meta = VM["ai_tools"]
    default_kind = "LLM model" if year == 2025 else "Product"
    tools_long["tool"] = tools_long["item"].map(lambda x: meta.get(x, [x])[0])
    tools_long["vendor"] = tools_long["item"].map(lambda x: meta.get(x, [x, "Other"])[1])
    tools_long["tool_kind"] = tools_long["item"].map(lambda x: meta.get(x, [x, "Other", default_kind])[2])
    out["answered_ai_tools"] = tool_answered.astype(int)
    out["n_ai_tools"] = (tools_long.groupby("resp_id")["tool"].nunique()
                         .reindex(rid).fillna(0).where(tool_answered.values).values)
    for name, tool in (("tool_chatgpt_or_gpt", ["ChatGPT", "OpenAI GPT models"]),
                       ("tool_github_copilot", ["GitHub Copilot"]),
                       ("tool_claude", ["Claude", "Claude Sonnet", "Claude Code"])):
        users = set(tools_long.loc[tools_long["tool"].isin(tool), "resp_id"])
        out[name] = flag(rid.isin(users), tool_answered)
    bridges["respondent_ai_tools"] = tools_long.rename(columns={"item": "tool_raw"})

    # ---- frustrations (2025), benefits (2023-24), challenges (2024) ----
    if year == 2025:
        fr = map_items(explode(raw, "AIFrustration"), year_map("ai_frustration", year), "ai_frustration")
        keys = list(dict.fromkeys(year_map("ai_frustration", year).values()))
        ans = raw["AIFrustration"].notna()
        out = pd.concat([out, to_dummies(fr, rid, ans, "frus_", keys)], axis=1)
        out["answered_frustration"] = ans.astype(int)
        bridges["respondent_ai_frustrations"] = fr.rename(columns={"key": "frustration", "item": "frustration_raw"})
    if year in BENEFIT_COL:
        col = BENEFIT_COL[year]
        bn = map_items(explode(raw, col), year_map("ai_benefits", year), "ai_benefits")
        keys = sorted(set(bn["key"]))
        out = pd.concat([out, to_dummies(bn, rid, raw[col].notna(), "ben_", keys)], axis=1)
        bridges["respondent_ai_benefits"] = bn.rename(columns={"key": "benefit", "item": "benefit_raw"})
    if year == 2024:
        ch = map_items(explode(raw, "AIChallenges"), year_map("ai_challenges", year), "ai_challenges")
        keys = list(dict.fromkeys(year_map("ai_challenges", year).values()))
        out = pd.concat([out, to_dummies(ch, rid, raw["AIChallenges"].notna(), "chal_", keys)], axis=1)
        bridges["respondent_ai_challenges"] = ch.rename(columns={"key": "challenge", "item": "challenge_raw"})

    for name, b in bridges.items():
        b.insert(1, "survey_year", year)
    return out, bridges


def add_country_group(df: pd.DataFrame) -> pd.DataFrame:
    top = df["country"].value_counts().head(TOP_COUNTRIES).index
    df["country_group"] = df["country"].where(df["country"].isin(top), "Other").where(df["country"].notna())
    return df


def build() -> pd.DataFrame:
    frames, bridges = [], {}
    for year in YEARS:
        df, br = harmonise_year(year)
        df.to_parquet(INTERIM / f"respondents_{year}.parquet", index=False)
        frames.append(df)
        for k, v in br.items():
            bridges.setdefault(k, []).append(v)
        print(f"{year}: {len(df):,} rows, {df.shape[1]} columns")
    resp = add_country_group(pd.concat(frames, ignore_index=True))
    # stable column types for parquet / DuckDB / Power BI
    for c in resp.columns:
        if resp[c].dtype == object:
            resp[c] = resp[c].astype("string")
    resp.to_parquet(RESPONDENTS_PARQUET, index=False)
    for k, parts in bridges.items():
        pd.concat(parts, ignore_index=True).to_parquet(PROCESSED / f"{k}.parquet", index=False)
    print(f"combined: {len(resp):,} rows, {resp.shape[1]} columns -> {RESPONDENTS_PARQUET.name}")
    return resp


def main() -> pd.DataFrame:
    return build()


if __name__ == "__main__":
    main()
