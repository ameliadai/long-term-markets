"""Fetch current order books for a set of open markets (public API) and summarize depth."""
import sys, time, requests, pandas as pd, numpy as np
from concurrent.futures import ThreadPoolExecutor
A = "https://api.elections.kalshi.com/trade-api/v2/markets/{}/orderbook"
tickers = pd.read_parquet(sys.argv[1]).ticker.tolist()

def levels(side):
    return [(float(p), float(q)) for p, q in (side or [])]

def fetch(t):
    for attempt in range(5):
        try:
            r = requests.get(A.format(t), timeout=30)
            if r.status_code == 429:
                time.sleep(1 + attempt); continue
            r.raise_for_status()
            ob = r.json().get("orderbook_fp") or r.json().get("orderbook") or {}
            yes = levels(ob.get("yes_dollars") or ob.get("yes"))
            no = levels(ob.get("no_dollars") or ob.get("no"))
            best_bid = max((p for p, _ in yes), default=np.nan)
            best_ask = 1 - max((p for p, _ in no), default=np.nan)
            row = {"ticker": t, "best_bid": best_bid, "best_ask": best_ask,
                   "n_levels_yes": len(yes), "n_levels_no": len(no),
                   "depth_yes_total": sum(q for _, q in yes), "depth_no_total": sum(q for _, q in no)}
            for w in (0.02, 0.05, 0.10):
                row[f"bid_depth_{int(w*100)}c"] = sum(q for p, q in yes if p >= best_bid - w) if yes else 0
                row[f"ask_depth_{int(w*100)}c"] = sum(q for p, q in no if 1 - p <= best_ask + w) if no else 0
            return row
        except Exception as e:
            err = repr(e)
            time.sleep(1)
    return {"ticker": t, "error": err}

rows = []
with ThreadPoolExecutor(5) as ex:
    for i, r in enumerate(ex.map(fetch, tickers)):
        rows.append(r)
        if i % 2000 == 0: print(i, flush=True)
df = pd.DataFrame(rows); df["snapshot_time"] = pd.Timestamp.utcnow()
df.to_parquet(sys.argv[2], index=False); print("done", len(df), df.get("error", pd.Series()).notna().sum(), "errors")
