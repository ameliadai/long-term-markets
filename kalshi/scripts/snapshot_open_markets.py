"""Snapshot every currently open non-combo Kalshi market (public API) to parquet."""
import sys, time, requests, pandas as pd
A = "https://api.elections.kalshi.com/trade-api/v2/markets"
out, cursor = [], None
while True:
    p = {"limit": 1000, "status": "open", "mve_filter": "exclude"}
    if cursor:
        p["cursor"] = cursor
    for attempt in range(5):
        r = requests.get(A, params=p, timeout=60)
        if r.status_code == 429:
            time.sleep(2 ** attempt); continue
        r.raise_for_status(); break
    j = r.json()
    out += j["markets"]
    cursor = j.get("cursor")
    if len(out) % 20000 < 1000:
        print(len(out), flush=True)
    if not cursor or not j["markets"]:
        break
df = pd.DataFrame(out)
for c in df.columns:
    if df[c].map(lambda v: isinstance(v, (list, dict))).any():
        df[c] = df[c].map(lambda v: None if v is None else str(v))
df["snapshot_time"] = pd.Timestamp.utcnow()
df.to_parquet(sys.argv[1], index=False)
print("open markets", len(df))
