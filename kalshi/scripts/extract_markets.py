"""Stream one part of the archived markets dump from GCS and write a compact parquet.

Multivariate combo markets (tickers starting KXMVE) are ~90% of rows; they are
kept in a separate slim table (no raw JSON) so the main table stays small.

usage: python extract_markets.py kalshi-markets-2026-09-21.sql.gz.partNN OUT_DIR
"""

import json
import re
import sys
import urllib.request
import zlib

import pandas as pd

BUCKET = "https://storage.googleapis.com/prophet-kalshi-archive/"
PREFIX = b'INSERT OR IGNORE INTO "markets" VALUES('
VAL = r"('(?:[^']|'')*'|NULL|-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
HEAD = re.compile(r"\(" + ",".join([VAL] * 13) + r",'(.*)'\);$", re.S)
COLS = ["ticker", "event_ticker", "market_type", "title", "status", "result",
        "open_time", "close_time", "expiration_time", "volume", "open_interest",
        "liquidity_dollars", "last_price_dollars"]
RAW_KEYS = ["created_time", "expected_expiration_time", "latest_expiration_time",
            "settlement_ts", "yes_sub_title", "strike_type", "floor_strike",
            "cap_strike", "can_close_early", "notional_value_dollars",
            "previous_price_dollars", "yes_bid_dollars", "yes_ask_dollars",
            "yes_bid_size_fp", "yes_ask_size_fp", "volume_24h_fp",
            "settlement_value_dollars", "price_level_structure", "rules_primary"]


def unq(v):
    if v == "NULL":
        return None
    if v.startswith("'"):
        return v[1:-1].replace("''", "'")
    return float(v)


def statements(stream):
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    buf, cur = b"", None
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
                if cur is not None:
                    yield cur
                cur = line[len(PREFIX) - 1:]
            elif cur is not None:
                if line.startswith((b"COMMIT", b"CREATE", b"BEGIN", b"INSERT ")):
                    yield cur
                    cur = None
                else:
                    cur += b"\n" + line
    if cur is not None:
        yield cur


def main(part, out_dir):
    main_rows, mve_rows, bad = [], [], 0
    for stmt in statements(urllib.request.urlopen(BUCKET + part)):
        is_mve = stmt.startswith(b"('KXMVE")
        m = HEAD.match(stmt.decode("utf-8", "replace"))
        if not m:
            bad += 1
            continue
        row = {c: unq(v) for c, v in zip(COLS, m.groups()[:13])}
        if is_mve:
            del row["title"]
            mve_rows.append(row)
            continue
        raw = json.loads(m.group(14).replace("''", "'"))
        for k in RAW_KEYS:
            v = raw.get(k)
            row[k] = json.dumps(v) if isinstance(v, (list, dict)) else v
        main_rows.append(row)
    stem = part.replace(".sql.gz.", "_")
    pd.DataFrame(main_rows).to_parquet(f"{out_dir}/{stem}_main.parquet", index=False)
    pd.DataFrame(mve_rows).to_parquet(f"{out_dir}/{stem}_mve.parquet", index=False)
    print(part, "main", len(main_rows), "mve", len(mve_rows), "unparsed", bad, flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
