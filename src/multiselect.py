"""Split ';'-separated multi-select answers into a long bridge table and wide 0/1 columns.

Rule: if a respondent skipped the whole question, every dummy is NaN (unknown), not 0.
"""
import pandas as pd


class UnmappedLabelError(ValueError):
    pass


def explode(df: pd.DataFrame, col: str, sep: str = ";") -> pd.DataFrame:
    """Return long (resp_id, item) rows for one multi-select column."""
    s = df.set_index("resp_id")[col].dropna().str.split(sep).explode().str.strip()
    s = s[s != ""]
    return s.rename("item").reset_index()


def map_items(long: pd.DataFrame, item_map: dict, var: str, strict: bool = True) -> pd.DataFrame:
    unmapped = sorted(set(long["item"]) - set(item_map))
    if unmapped and strict:
        raise UnmappedLabelError(f"{var}: unmapped items {unmapped}")
    out = long.copy()
    out["key"] = out["item"].map(item_map)
    return out


def to_dummies(long: pd.DataFrame, resp_ids: pd.Series, answered: pd.Series, prefix: str,
               keys: list[str], key_col: str = "key") -> pd.DataFrame:
    """Wide 0/1 frame indexed like resp_ids; rows where `answered` is False are NaN."""
    hit = (long.assign(v=1).drop_duplicates(["resp_id", key_col])
               .pivot(index="resp_id", columns=key_col, values="v"))
    wide = hit.reindex(index=resp_ids, columns=keys).fillna(0.0)
    wide.loc[~answered.values, :] = float("nan")
    wide.columns = [f"{prefix}{k}" for k in wide.columns]
    wide.index = resp_ids.index
    return wide
