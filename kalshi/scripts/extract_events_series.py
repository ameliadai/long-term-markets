"""Pull the events and series tables out of the archived dumps into parquet.

Both tables sit at the start of the main dump (before the trades), plus a few
rows in the gap dump, so this stops reading once trades begin.

usage: python extract_events_series.py OUT_DIR
"""

import json
import re
import sys
import urllib.request
import zlib

import pandas as pd

BUCKET = "https://storage.googleapis.com/prophet-kalshi-archive/"
SOURCES = ["kalshi-2026-09-21.sql.gz.part01", "kalshi-gap-2026-09-21.sql.gz.part01"]
VAL = r"('(?:[^']|'')*'|NULL|-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
TABLES = {
    "events": ["event_ticker", "series_ticker", "title", "sub_title", "category",
               "mutually_exclusive", "raw"],
    "series": ["ticker", "title", "category", "frequency", "raw"],
}
PATTERNS = {t: re.compile(r"INSERT OR IGNORE INTO \"" + t + r"\" VALUES\("
                          + ",".join([VAL] * len(c)) + r"\);$", re.S)
            for t, c in TABLES.items()}


def unq(v):
    if v == "NULL":
        return None
    if v.startswith("'"):
        return v[1:-1].replace("''", "'")
    return float(v)


def statements(name):
    stream = urllib.request.urlopen(BUCKET + name)
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    buf, cur = b"", None
    while True:
        chunk = stream.read(1 << 20)
        if not chunk:
            break
        buf += d.decompress(chunk)
        lines = buf.split(b"\n")
        buf = lines.pop()
        for line in lines:
            if line.startswith((b"INSERT", b"CREATE", b"COMMIT", b"BEGIN")):
                if cur is not None:
                    yield cur
                cur = line if line.startswith(b"INSERT") else None
                if line.startswith(b'INSERT OR IGNORE INTO "trades"'):
                    return
            elif cur is not None:
                cur += b"\n" + line
    if cur is not None:
        yield cur


def main(out_dir):
    rows = {t: [] for t in TABLES}
    for name in SOURCES:
        for stmt in statements(name):
            s = stmt.decode("utf-8", "replace")
            for t, pat in PATTERNS.items():
                if s.startswith(f'INSERT OR IGNORE INTO "{t}"'):
                    m = pat.match(s)
                    vals = [unq(v) for v in m.groups()]
                    rows[t].append(dict(zip(TABLES[t], vals)))
    for t, r in rows.items():
        df = pd.DataFrame(r)
        key = "event_ticker" if t == "events" else "ticker"
        df = df.drop_duplicates(key, keep="last")
        raw = df["raw"].map(json.loads)
        if t == "events":
            for k in ["strike_date", "strike_period", "last_updated_ts"]:
                df[k] = raw.map(lambda j: j.get(k))
        else:
            df["tags"] = raw.map(lambda j: "|".join(j.get("tags") or []))
            df["fee_type"] = raw.map(lambda j: j.get("fee_type"))
            df["settlement_sources"] = raw.map(
                lambda j: "|".join(s.get("name", "") for s in j.get("settlement_sources") or []))
        df.to_parquet(f"{out_dir}/{t}.parquet", index=False)
        print(t, len(df))


if __name__ == "__main__":
    main(sys.argv[1])
