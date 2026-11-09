"""Validation checks: row counts, keys, and a benchmark of our harmonised numbers vs the
official Stack Overflow results tables (data/raw/<year>/official_json/ai.json).

Writes reports/tables/benchmark_check.csv. Exits with code 1 if any check fails.
Usage:  python -m src.validate
"""
import json
import sys

import pandas as pd

from src.config import RAW, RESPONDENTS_PARQUET, TABLES, YEARS
from src.harmonise import VM, year_map
from src.load import raw_row_counts

TOLERANCE_PP = 1.0   # public microdata differs from the internal file by a few dozen rows
PROF = "Professional Developers"

# (official question key, harmonised label column, value-map variable, base filter column)
CHECKS = {
    "AISelect": ("ai_use_status", "ai_use_status", None),
    "AISent": ("sentiment_label", "ai_sentiment", None),
    "AIBen_2023": ("trust_label", "ai_trust", "in_trust_base_official"),
    "AIAcc": ("trust_label", "ai_trust", "in_trust_base_official"),
}


def clean(label: str) -> str:
    return label.replace("’", "'").replace("�", "'").strip()


def official_tables(year: int) -> dict:
    return json.loads((RAW / str(year) / "official_json" / "ai.json").read_text(encoding="utf-8"))


def compare_single(resp, year, q_official, label_col, var, base_col, rows):
    block = official_tables(year)[q_official]
    for ds in block["datasets"].values():
        if ds.get("name") not in ("All Respondents", PROF):
            continue
        d = resp[resp.survey_year == year]
        if ds["name"] == PROF:
            d = d[d.is_professional == 1]
        d = d[d[label_col].notna()]
        if base_col:
            d = d[d[base_col] == 1]
        mine = d[label_col].value_counts(normalize=True)
        m = year_map(var, year)
        off = {}
        for r in ds["data"]:
            key = m.get(clean(r["response"]))
            off[key] = off.get(key, 0) + r["percent"]
        for key, pct in off.items():
            rows.append(dict(year=year, question=q_official, group=ds["name"], answer=key,
                             official_pct=round(100 * pct, 2), our_pct=round(100 * mine.get(key, 0), 2),
                             official_base=ds["total_respondents"], our_base=len(d)))


def compare_frustration(resp, rows):
    block = official_tables(2025)["AIFrustration"]
    ds = block["datasets"]["AIFrustration"]
    d = resp[(resp.survey_year == 2025) & (resp.answered_frustration == 1)]
    m = year_map("ai_frustration", 2025)
    for r in ds["data"]:
        key = m[clean(r["response"])]
        rows.append(dict(year=2025, question="AIFrustration", group=ds["name"], answer=key,
                         official_pct=round(100 * r["percent"], 2), our_pct=round(100 * d[f"frus_{key}"].mean(), 2),
                         official_base=ds["total_respondents"], our_base=len(d)))


def main() -> int:
    resp = pd.read_parquet(RESPONDENTS_PARQUET)
    ok = True

    raw_n = raw_row_counts()
    for y in YEARS:
        n = int((resp.survey_year == y).sum())
        status = "PASS" if n == raw_n[y] else "FAIL"
        ok &= status == "PASS"
        print(f"[{status}] row count {y}: harmonised {n:,} vs raw {raw_n[y]:,}")
    dup = resp.resp_id.duplicated().sum()
    print(f"[{'PASS' if dup == 0 else 'FAIL'}] duplicate resp_id: {dup}")
    ok &= dup == 0

    rows = []
    for y in YEARS:
        compare_single(resp, y, "AISelect", "ai_use_status", "ai_use_status", None, rows)
        compare_single(resp, y, "AISent", "sentiment_label", "ai_sentiment", None, rows)
        compare_single(resp, y, "AIBen" if y == 2023 else "AIAcc", "trust_label", "ai_trust",
                       "in_trust_base_official", rows)
    compare_frustration(resp, rows)
    bench = pd.DataFrame(rows)
    bench["diff_pp"] = (bench.our_pct - bench.official_pct).round(2)
    # 2025's official trust table omits "Neither" but keeps it in the base -> our share for it has no counterpart
    bench["status"] = bench.diff_pp.abs().le(TOLERANCE_PP).map({True: "PASS", False: "FAIL"})
    bench.to_csv(TABLES / "benchmark_check.csv", index=False)
    n_fail = (bench.status == "FAIL").sum()
    print(f"[{'PASS' if n_fail == 0 else 'FAIL'}] benchmark vs official tables: "
          f"{len(bench) - n_fail}/{len(bench)} within ±{TOLERANCE_PP}pp; max |diff| = {bench.diff_pp.abs().max():.2f}pp")
    if n_fail:
        print(bench[bench.status == "FAIL"].to_string())
    ok &= n_fail == 0

    # headline figures we are allowed to quote (official definitions)
    head = bench[(bench.group == "All Respondents")]
    for y in YEARS:
        t = head[(head.year == y) & head.question.isin(["AIBen", "AIAcc"])].set_index("answer").official_pct
        trust = t.filter(like="trust").filter(regex="^[45]").sum()
        distrust = t.filter(regex="^[12]").sum()
        print(f"   official {y}: trust {trust:.1f}%  distrust {distrust:.1f}%")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
