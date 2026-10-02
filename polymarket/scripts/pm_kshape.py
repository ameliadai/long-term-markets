"""Polymarket data in the shape of the Kalshi tables, so the Kalshi analysis scripts (scripts/a0*.py,
a11) run on it unchanged, from the repo root:
  KL_DATA=polymarket/kshape KL_RESULTS=polymarket/results python kalshi/scripts/a01_landscape.py

  markets.parquet        one row per market: ticker (= market id), event_ticker (= event id), status
                         (finalized = resolved yes/no, active = open, closed = closed without a yes/no
                         result), result (yes = first outcome won), open_time, close_time,
                         expected_expiration_time (scheduled end date), horizon_days, category (coarse
                         Polymarket category), volume (shares, Gamma volumeNum)
  candles_daily.parquet  one row per market-day with a price or a trade, for the markets in
                         pm_selected.parquet that started on or after TRADES_FROM: price_close (CLOB daily price of the first outcome),
                         volume (shares traded that day). No bid/ask, spread or open interest history.
  trades_daily.parquet   n (trades), contracts (shares), yes_notional (USD) per market-day
  incentive_programs.parquet  empty: Polymarket's reward history is not available
"""
import glob
import os

import numpy as np
import pandas as pd

from pm_common import DATA, ROOT, TRADES_FROM

OUT = os.environ.get("PM_KSHAPE", os.path.join(ROOT, "kshape"))


def read_parts(sub, cols=None):
    return pd.concat([pd.read_parquet(f, columns=cols) for f in sorted(glob.glob(os.path.join(DATA, sub, "*_part*.parquet")))],
                     ignore_index=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    m = pd.read_parquet(os.path.join(DATA, "pm_markets.parquet"), columns=[
        "id", "event_id", "closed", "resolved", "y", "start", "end", "endDate", "duration_days",
        "category_coarse", "volumeNum", "question"])
    out = pd.DataFrame({
        "ticker": m["id"].astype(str), "event_ticker": m.event_id.astype(str), "title": m.question,
        "status": np.where(m.resolved, "finalized", np.where(m.closed.astype(bool), "closed", "active")),
        "result": np.where(m.y == 1, "yes", np.where(m.y == 0, "no", None)),
        "open_time": m.start, "close_time": m["end"],
        "expected_expiration_time": pd.to_datetime(m.endDate, format="ISO8601", utc=True, errors="coerce"),
        "settlement_ts": pd.NaT, "can_close_early": np.nan,
        "horizon_days": m.duration_days, "category": m.category_coarse,
        "volume": pd.to_numeric(m.volumeNum, errors="coerce").fillna(0)})
    out["settlement_ts"] = pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns, UTC]")
    out.to_parquet(os.path.join(OUT, "markets.parquet"), index=False)
    print(f"markets {len(out):,}", out.status.value_counts().to_dict(), flush=True)

    # daily prices and trades only for markets whose trade history is complete
    keep = set(out.ticker[out.open_time >= pd.Timestamp(TRADES_FROM, tz="UTC")])
    pr = read_parts("prices")
    pr = pr[pr.market_id.astype(str).isin(keep)]
    pr["day"] = pd.to_datetime(pr.t, unit="s", utc=True).dt.floor("D")
    pr = pr.sort_values(["market_id", "t"]).drop_duplicates(["market_id", "day"], keep="last")
    td = read_parts("trades_daily", ["market_id", "day", "n_trades", "shares", "usd"])
    td = td[td.market_id.astype(str).isin(keep)]
    td["day"] = pd.to_datetime(td.day, utc=True).dt.floor("D")
    td = td.groupby(["market_id", "day"], as_index=False)[["n_trades", "shares", "usd"]].sum()
    for d in (pr, td):
        d["day"] = d.day.astype("datetime64[ns, UTC]")
        d["market_id"] = d.market_id.astype(str)
    c = pr[["market_id", "day", "p"]].merge(td, on=["market_id", "day"], how="outer")
    c = pd.DataFrame({
        "ticker": c.market_id, "day": c.day, "interval": "1d", "n_bars": 1,
        "volume": c.shares.fillna(0), "n_trade_bars": (c.n_trades.fillna(0) > 0).astype(int),
        "price_close": c.p, "bid_close": np.nan, "ask_close": np.nan, "spread_med": np.nan,
        "two_sided_share": np.nan, "oi_close": np.nan}).sort_values(["ticker", "day"])
    c.to_parquet(os.path.join(OUT, "candles_daily.parquet"), index=False)
    print(f"candles {len(c):,} market-days, {c.ticker.nunique():,} markets", flush=True)

    t = pd.DataFrame({"ticker": td.market_id, "day": td.day, "n": td.n_trades, "contracts": td.shares,
                      "yes_notional": td.usd, "n_taker_yes": np.nan, "contracts_taker_yes": np.nan, "n_block": 0,
                      "n_lt10": np.nan, "n_10_99": np.nan, "n_100_999": np.nan, "n_ge1000": np.nan})
    t.to_parquet(os.path.join(OUT, "trades_daily.parquet"), index=False)
    print(f"trades_daily {len(t):,} market-days, {int(t.n.sum()):,} trades", flush=True)

    pd.DataFrame({c: pd.Series(dtype=t_) for c, t_ in [
        ("market_ticker", "str"), ("incentive_type", "str"), ("incentive_description", "str"), ("start_date", "str"),
        ("end_date", "str"), ("period_reward", "int64"), ("paid_out", "bool")]}).to_parquet(
        os.path.join(OUT, "incentive_programs.parquet"), index=False)


if __name__ == "__main__":
    main()
