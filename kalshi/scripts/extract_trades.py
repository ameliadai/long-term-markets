"""Stream one archived trades dump part from GCS and write per-market daily aggregates.

One row per (ticker, UTC day) with trade counts, contracts, notional, VWAP,
taker-side split, block trades, and trade-size buckets. `source` records which
dump the rows came from so overlaps between backfill runs can be checked.

usage: python extract_trades.py kalshi-trades2-2026-09-21.sql.gz.part03 OUT_DIR
"""

import sys
import urllib.request
import zlib
from collections import defaultdict

import pandas as pd

BUCKET = "https://storage.googleapis.com/prophet-kalshi-archive/"
PREFIX = b'INSERT OR IGNORE INTO "trades" VALUES('
# contracts per trade: <10, 10-99, 100-999, >=1000
SIZE_EDGES = (10, 100, 1000)
FIELDS = ["n", "contracts", "yes_notional", "n_taker_yes", "contracts_taker_yes",
          "n_block", "n_lt10", "n_10_99", "n_100_999", "n_ge1000", "max_size",
          "first_ts", "last_ts"]


def main(part, out_dir):
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    stream = urllib.request.urlopen(BUCKET + part)
    agg = defaultdict(lambda: [0, 0.0, 0.0, 0, 0.0, 0, 0, 0, 0, 0, 0.0, "~", ""])
    buf, n_rows = b"", 0
    plen = len(PREFIX)
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
            if not line.startswith(PREFIX):
                continue
            v = line[plen:-2].split(b",")
            ticker = v[1][1:-1].decode()
            ts = v[2][1:-1].decode()
            yes = float(v[3]) if v[3] != b"NULL" else 0.0
            cnt = float(v[5]) if v[5] != b"NULL" else 0.0
            a = agg[(ticker, ts[:10])]
            a[0] += 1
            a[1] += cnt
            a[2] += cnt * yes
            if v[6] == b"'yes'":
                a[3] += 1
                a[4] += cnt
            if v[9] == b"1":
                a[5] += 1
            if cnt < SIZE_EDGES[0]:
                a[6] += 1
            elif cnt < SIZE_EDGES[1]:
                a[7] += 1
            elif cnt < SIZE_EDGES[2]:
                a[8] += 1
            else:
                a[9] += 1
            if cnt > a[10]:
                a[10] = cnt
            if ts < a[11]:
                a[11] = ts
            if ts > a[12]:
                a[12] = ts
            n_rows += 1
    df = pd.DataFrame([(t, day, *vals) for (t, day), vals in agg.items()],
                      columns=["ticker", "day"] + FIELDS)
    df["source"] = part.split("-2026")[0]
    df["part"] = part
    stem = part.replace(".sql.gz.", "_")
    df.to_parquet(f"{out_dir}/{stem}.parquet", index=False)
    print(part, "trades", n_rows, "market-days", len(df), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
