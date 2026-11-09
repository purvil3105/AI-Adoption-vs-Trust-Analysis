"""Small statistics helpers: Wilson intervals, weighted shares and raking (iterative proportional fitting)."""
import numpy as np
import pandas as pd

Z = 1.959964


def wilson_ci(p: float, n: float, z: float = Z) -> tuple[float, float]:
    """95% Wilson score interval for a proportion."""
    if n <= 0 or pd.isna(p):
        return (np.nan, np.nan)
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (centre - half, centre + half)


def share_table(df: pd.DataFrame, by: list[str], outcome: str, base_mask: pd.Series | None = None,
                weight: str | None = None, min_n: int = 0) -> pd.DataFrame:
    """Share of `outcome`==1 per group with Wilson CI (weights use the Kish effective n)."""
    d = df if base_mask is None else df[base_mask]
    d = d[d[outcome].notna()]
    w = d[weight] if weight else pd.Series(1.0, index=d.index)
    g = d.assign(_w=w, _wy=w * d[outcome], _w2=w**2).groupby(by, observed=True)
    out = g.agg(n=("_w", "size"), sw=("_w", "sum"), swy=("_wy", "sum"), sw2=("_w2", "sum")).reset_index()
    out["share"] = out.swy / out.sw
    out["n_eff"] = out.sw**2 / out.sw2
    ci = [wilson_ci(p, n) for p, n in zip(out.share, out.n_eff)]
    out["ci_low"] = [c[0] for c in ci]
    out["ci_high"] = [c[1] for c in ci]
    out = out[out.n >= min_n]
    return out.drop(columns=["sw", "swy", "sw2"])


def ordered_logit(y: np.ndarray, X: np.ndarray) -> dict:
    """Proportional-odds (ordered) logit with analytic gradient: P(y<=j) = F(c_j - Xb).
    y must be integer categories 1..J. Cut points are parametrised c_1 = a_1, c_k = c_{k-1} + exp(a_k)
    so they stay ordered. Returns coefficients b with standard errors from the inverse Hessian
    (computed by finite differences of the analytic gradient). Equivalent to statsmodels OrderedModel,
    but fast enough for ~80k rows."""
    from scipy.optimize import minimize
    from scipy.special import expit

    y = np.asarray(y, dtype=int)
    X = np.asarray(X, dtype=float)
    n, k = X.shape
    J = int(y.max())
    lo_idx, hi_idx = y - 2, y - 1                   # index of lower / upper cut point (may be -1 or J-1)

    def unpack(theta):
        b, a = theta[:k], theta[k:]
        c = np.cumsum(np.concatenate([[a[0]], np.exp(a[1:])]))
        return b, a, c

    def nll_grad(theta):
        b, a, c = unpack(theta)
        xb = X @ b
        cu = np.where(hi_idx < J - 1, c[np.clip(hi_idx, 0, J - 2)], np.inf)
        cl = np.where(lo_idx >= 0, c[np.clip(lo_idx, 0, J - 2)], -np.inf)
        Fu, Fl = expit(cu - xb), expit(cl - xb)
        p = np.clip(Fu - Fl, 1e-300, None)
        fu, fl = Fu * (1 - Fu), Fl * (1 - Fl)
        g_b = X.T @ ((fu - fl) / p)                 # d(-ll)/db
        g_c = np.zeros(J - 1)
        np.add.at(g_c, np.clip(hi_idx, 0, J - 2), np.where(hi_idx < J - 1, -fu / p, 0.0))
        np.add.at(g_c, np.clip(lo_idx, 0, J - 2), np.where(lo_idx >= 0, fl / p, 0.0))
        # chain rule to a: dc_m/da_1 = 1 ; dc_m/da_j = exp(a_j) for m >= j
        g_a = np.array([g_c.sum()] + [np.exp(a[j]) * g_c[j:].sum() for j in range(1, J - 1)])
        return -np.log(p).sum(), np.concatenate([g_b, g_a])

    cum = np.array([(y <= j).mean() for j in range(1, J)])
    c0 = np.log(cum / (1 - cum))
    a0 = np.concatenate([[c0[0]], np.log(np.diff(c0))])
    res = minimize(nll_grad, np.concatenate([np.zeros(k), a0]), jac=True, method="L-BFGS-B",
                   options={"maxiter": 5000, "gtol": 1e-6})
    theta = res.x
    eps = 1e-5
    H = np.empty((len(theta), len(theta)))
    for i in range(len(theta)):
        d = np.zeros_like(theta)
        d[i] = eps
        H[:, i] = (nll_grad(theta + d)[1] - nll_grad(theta - d)[1]) / (2 * eps)
    cov = np.linalg.inv((H + H.T) / 2)
    se = np.sqrt(np.diag(cov))[:k]
    return {"params": theta[:k], "se": se, "converged": bool(res.success), "nobs": n, "loglike": -res.fun}


def rake(df: pd.DataFrame, targets: dict[str, pd.Series], max_iter: int = 100, tol: float = 1e-6,
         trim: tuple[float, float] = (0.2, 5.0)) -> pd.Series:
    """Raking weights so that the weighted margins of `df` match `targets`
    (dict: column -> Series of target shares). Weights are normalised to mean 1 and trimmed."""
    w = pd.Series(1.0, index=df.index)
    for _ in range(max_iter):
        max_change = 0.0
        for col, tgt in targets.items():
            cur = w.groupby(df[col]).sum() / w.sum()
            factor = (tgt / cur).reindex(df[col]).fillna(1.0).values
            new_w = w * factor
            max_change = max(max_change, float(np.abs(new_w - w).max()))
            w = new_w
        w = (w / w.mean()).clip(*trim)
        w = w / w.mean()
        if max_change < tol:
            break
    return w
