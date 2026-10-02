"""Combine the extracted parts into analysis tables.

data/markets.parquet      non-combo markets + series/category + listing horizon
data/mve_summary.parquet  combo (KXMVE*) markets summarized by series and close month
data/candles_daily.parquet  all candle shards concatenated (if present)
data/trades_daily.parquet   all trade parts concatenated (if present)
"""

import glob

import numpy as np
import pandas as pd

from common import D


def ts(s):
    return pd.to_datetime(s, format="ISO8601", utc=True, errors="coerce")


def build_markets():
    m = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{D}/markets/*_main.parquet"))])
    m = m.drop_duplicates("ticker", keep="last")
    ev = pd.read_parquet(f"{D}/events.parquet")[["event_ticker", "series_ticker", "category", "title"]]
    ev = ev.rename(columns={"title": "event_title"})
    se = pd.read_parquet(f"{D}/series.parquet")[["ticker", "category", "frequency", "tags", "title"]]
    se = se.rename(columns={"ticker": "series_ticker", "category": "series_category",
                            "title": "series_title"})
    m = m.merge(ev, on="event_ticker", how="left")
    m["series_ticker"] = m.series_ticker.fillna(m.event_ticker.str.split("-").str[0])
    m = m.merge(se, on="series_ticker", how="left")
    m["category"] = m.category.fillna(m.series_category)
    for c in ["open_time", "close_time", "created_time", "settlement_ts",
              "expected_expiration_time"]:
        m[c] = ts(m[c])
    m["horizon_days"] = (m.close_time - m.open_time).dt.total_seconds() / 86400
    for c in ["yes_bid_dollars", "yes_ask_dollars", "yes_bid_size_fp", "yes_ask_size_fp",
              "volume_24h_fp", "notional_value_dollars", "previous_price_dollars",
              "settlement_value_dollars"]:
        m[c] = pd.to_numeric(m[c], errors="coerce")
    m.to_parquet(f"{D}/markets.parquet", index=False)
    print("markets", len(m))

    mve = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{D}/markets/*_mve.parquet"))])
    mve["series_ticker"] = mve.event_ticker.str.split("-").str[0]
    mve["close_month"] = ts(mve.close_time).dt.strftime("%Y-%m")
    s = mve.groupby(["series_ticker", "close_month", "status"]).agg(
        n=("ticker", "size"), n_traded=("volume", lambda v: (v > 0).sum()),
        volume=("volume", "sum"), open_interest=("open_interest", "sum")).reset_index()
    s.to_parquet(f"{D}/mve_summary.parquet", index=False)
    print("mve markets", len(mve))


def concat(pattern, out, dedup_on=None):
    files = sorted(glob.glob(pattern))
    if files:
        df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
        if dedup_on:
            df = df.drop_duplicates(dedup_on, keep="first")
        df.to_parquet(out, index=False)
        print(out, len(df), "rows from", len(files), "files")


if __name__ == "__main__":
    import sys
    what = sys.argv[1:] or ["markets", "candles", "trades"]
    if "markets" in what:
        build_markets()
    if "candles" in what:
        # the gap-run shards re-fetched ~36K markets already in the main shards; keep the main-shard row
        concat(f"{D}/candles_daily/kalshi-candles-*.parquet", f"{D}/candles_daily.parquet",
               dedup_on=["ticker", "day"])
    if "trades" in what:
        concat(f"{D}/trades_daily/kalshi-*.parquet", f"{D}/trades_daily.parquet")
