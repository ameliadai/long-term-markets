"""Stream one archived candlestick shard from GCS and write daily per-market aggregates.

Hourly (or minute, for markets that lived <= 2 days) candles are collapsed to
one row per market per UTC day:
  volume          contracts traded that day
  n_trade_bars    bars with volume > 0
  price_close     last traded price of the day (NaN if no trade yet)
  bid_close/ask_close  last yes bid / yes ask of the day
  spread_med      median over bars of (yes ask - yes bid), two-sided bars only
  two_sided_share share of bars with both a bid and an ask
  oi_close        open interest at the day's last bar

usage: python extract_candles.py kalshi-candles-N-2026-09-21.sql.gz.part01 OUT_DIR
"""

import sys
import urllib.request
import zlib

import numpy as np
import pandas as pd

BUCKET = "https://storage.googleapis.com/prophet-kalshi-archive/"
PREFIX = b'INSERT OR IGNORE INTO "candlesticks" VALUES('
NUM_COLS = ["price_close", "bid_close", "ask_close", "volume", "oi"]
# positions within the VALUES tuple
IDX = {"interval": 1, "ts": 2, "price_close": 6, "bid_close": 11, "ask_close": 15,
       "volume": 16, "oi": 17}


def num(b):
    return np.nan if b == b"NULL" else float(b)


def rows(stream):
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    buf = b""
    while True:
        chunk = stream.read(1 << 22)
        if not chunk:
            break
        data = d.decompress(chunk)
        while d.eof and d.unused_data:
            rest = d.unused_data
            d = zlib.decompressobj(16 + zlib.MAX_WBITS)
            data += d.decompress(rest)
        buf += data
        lines = buf.split(b"\n")
        buf = lines.pop()
        for line in lines:
            if line.startswith(PREFIX):
                yield line[len(PREFIX):-2].split(b",")


def aggregate(df):
    df["day"] = pd.to_datetime(df.ts, unit="s", utc=True).dt.floor("D")
    both = (df.bid_close > 0) & (df.ask_close < 1) & (df.ask_close > df.bid_close)
    df["spread"] = (df.ask_close - df.bid_close).where(both)
    df["two_sided"] = both
    df["traded"] = df.volume > 0
    df = df.sort_values(["ticker", "ts"])
    g = df.groupby(["ticker", "day"], sort=False)
    return pd.DataFrame({
        "interval": g.interval.first(),
        "n_bars": g.size(),
        "volume": g.volume.sum(),
        "n_trade_bars": g.traded.sum(),
        "price_close": g.price_close.last(),
        "bid_close": g.bid_close.last(),
        "ask_close": g.ask_close.last(),
        "spread_med": g.spread.median(),
        "two_sided_share": g.two_sided.mean(),
        "oi_close": g.oi.last(),
    }).reset_index()


def main(shard, out_dir):
    cols = {k: [] for k in ["ticker", "interval", "ts"] + NUM_COLS}
    for v in rows(urllib.request.urlopen(BUCKET + shard)):
        cols["ticker"].append(v[0][1:-1].decode())
        cols["interval"].append(int(v[IDX["interval"]]))
        cols["ts"].append(int(v[IDX["ts"]]))
        for c in NUM_COLS:
            cols[c].append(num(v[IDX[c]]))
    df = pd.DataFrame(cols)
    n = len(df)
    out = aggregate(df)
    stem = shard.replace(".sql.gz.", "_")
    out.to_parquet(f"{out_dir}/{stem}.parquet", index=False)
    print(shard, "candles", n, "market-days", len(out), "markets", out.ticker.nunique(), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
