"""Two-way fixed-effects OLS with clustered SEs."""
import numpy as np
import pandas as pd


def twfe(df, y, xs, fe=("ticker", "day"), cluster="series_ticker", iters=30):
    """OLS of y on xs after sweeping out two sets of fixed effects."""
    df = df.dropna(subset=[y]).reset_index(drop=True)
    Z = df[[y] + xs].astype(float)
    keys = [df[f].astype(str).values for f in fe]
    for _ in range(iters):
        for k in keys:
            Z = Z - Z.groupby(k).transform("mean")
    X, Y = Z[xs].values, Z[y].values
    beta = np.linalg.lstsq(X, Y, rcond=None)[0]
    u = Y - X @ beta
    XtX_inv = np.linalg.pinv(X.T @ X)
    Xu = pd.DataFrame(X * u[:, None]).groupby(df[cluster].values).sum().values
    G = len(Xu)
    V = XtX_inv @ (Xu.T @ Xu) @ XtX_inv * G / (G - 1)
    se = np.sqrt(np.diag(V))
    return pd.DataFrame({"coef": beta, "se": se, "t": beta / se}, index=xs).assign(
        outcome=y, n=len(df), mean_y=df[y].mean(), clusters=G)
