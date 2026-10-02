import os
from pathlib import Path

import numpy as np
import pandas as pd

KALSHI = Path(__file__).resolve().parent.parent          # kalshi/
# KL_DATA / KL_RESULTS point the scripts at another dataset in the same shape
# (polymarket/kshape, built by polymarket/scripts/pm_kshape.py)
D = os.environ.get("KL_DATA", str(KALSHI / "data"))
R = os.environ.get("KL_RESULTS", str(KALSHI / "results"))
HZ_BINS = [-1, 1, 7, 30, 90, 180, 365, 730, 1e6]
HZ_LABELS = ["<1d", "1-7d", "7-30d", "1-3m", "3-6m", "6-12m", "1-2y", ">2y"]
MACRO = ["Economics", "Financials", "Economy & Finance"]          # last: Polymarket's coarse category
TECH = ["Science and Technology", "AI", "Companies", "Tech & AI"]


def group_of(cat):
    if cat in MACRO:
        return "Econ/Fin"
    if cat in TECH:
        return "Tech/AI/Co"
    if cat in ("Elections", "Politics", "World"):
        return "Politics"
    if cat == "Sports":
        return "Sports"
    return "Other"


def markets(min_horizon=None):
    m = pd.read_parquet(f"{D}/markets.parquet")
    m = m[m.open_time.notna() & m.close_time.notna()]
    if min_horizon is not None:
        m = m[m.horizon_days >= min_horizon]
    m["hz"] = pd.cut(m.horizon_days, HZ_BINS, labels=HZ_LABELS)
    m["group"] = m.category.map(group_of)
    return m


def candles_for(tickers):
    c = pd.read_parquet(f"{D}/candles_daily.parquet")
    return c[c.ticker.isin(set(tickers))]
