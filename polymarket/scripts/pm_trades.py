"""Full trade history for each selected market (Data API /trades), aggregated per day.

The API refuses offsets beyond 10,000, so pages are walked backwards in time with the
`end=<unix ts>` parameter (10,000 trades per call), de-duplicating the boundary second.
takerOnly=true gives one row per fill; summed `size` matches Gamma's volume.

Writes per shard S:
  trades_daily/shardSS_partNNNNN.parquet  market_id, day, n_trades, shares, usd, n_buy, n_sell, n_wallets
  trades_raw/shardSS_partNNNNN.parquet    every trade, for markets open >= RAW_MIN_DAYS (default 30)
  trades_daily/shardSS_done_NNNNN.parquet market ids finished (for resuming)

Markets are fetched longest-lived first, on PM_WORKERS threads.

usage: python pm_trades.py SHARD NSHARDS [--limit N]
       env PM_RATE = requests/s for this shard (default 4), PM_WORKERS = threads (default 4)
"""
import argparse
import os

import pandas as pd

from pm_common import DATA, DATA_API, RateLimiter, done_ids, fetch_many, get_json, shard_of

PART_MARKETS = 500
RAW_MIN_DAYS = float(os.environ.get("RAW_MIN_DAYS", "30"))
PART_TRADES = 5_000_000      # also write a part once this many trades are buffered


def fetch_all(cond, lim):
    seen, rows, end = set(), [], None
    while True:
        p = {"market": cond, "limit": 10000, "takerOnly": "true"}
        if end is not None:
            p["end"] = end
        d = get_json(f"{DATA_API}/trades", p, lim)
        if not isinstance(d, list) or not d:
            break
        new = 0
        for t in d:
            k = (t.get("transactionHash"), t.get("asset"), t.get("side"), t.get("size"), t.get("price"),
                 t.get("proxyWallet"), t.get("timestamp"))
            if k in seen:
                continue
            seen.add(k)
            rows.append((int(t["timestamp"]), t.get("side"), int(t.get("outcomeIndex") or 0), float(t["price"]),
                         float(t["size"]), t.get("proxyWallet"), t.get("transactionHash")))
            new += 1
        mn = min(int(t["timestamp"]) for t in d)
        if len(d) < 10000 and new == len(d):
            break
        end = mn - 1 if new == 0 else mn
    return pd.DataFrame(rows, columns=["ts", "side", "outcome_index", "price", "size", "wallet", "tx"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shard", type=int)
    ap.add_argument("nshards", type=int)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    out_d, out_r = os.path.join(DATA, "trades_daily"), os.path.join(DATA, "trades_raw")
    os.makedirs(out_d, exist_ok=True)
    os.makedirs(out_r, exist_ok=True)
    sel = pd.read_parquet(os.path.join(DATA, "pm_selected.parquet"), columns=["market_id", "conditionId", "duration_days"])
    sel = sel[shard_of(sel.market_id, a.nshards) == a.shard].sort_values("duration_days", ascending=False)
    prefix = f"shard{a.shard:02d}_"
    done = done_ids(out_d, prefix + "done_")
    todo = sel[~sel.market_id.isin(done)]
    if a.limit:
        todo = todo.head(a.limit)
    part = len([f for f in os.listdir(out_d) if f.startswith(prefix + "done_")])
    print(f"shard {a.shard}/{a.nshards}: {len(sel):,} markets, {len(done):,} done, {len(todo):,} to fetch", flush=True)
    lim = RateLimiter(float(os.environ.get("PM_RATE", "4")))
    workers = int(os.environ.get("PM_WORKERS", "4"))
    daily, raw, ids, failed = [], [], [], []
    st = {"part": part, "n_tr": 0, "seen": 0, "buf": 0}

    def flush():
        if daily:
            pd.concat(daily).to_parquet(os.path.join(out_d, f"{prefix}part{st['part']:05d}.parquet"), index=False)
        if raw:
            pd.concat(raw).to_parquet(os.path.join(out_r, f"{prefix}part{st['part']:05d}.parquet"), index=False)
        pd.DataFrame({"market_id": ids}).to_parquet(os.path.join(out_d, f"{prefix}done_{st['part']:05d}.parquet"), index=False)
        print(f"  {st['seen']:,}/{len(todo):,} markets, part {st['part']}, {st['n_tr']:,} trades so far, "
              f"{len(failed):,} failed", flush=True)
        st["part"] += 1
        daily.clear()
        raw.clear()
        st["buf"] = 0
        ids.clear()

    # markets that still fail after get_json's retries are tried once more at the end;
    # any left are not marked done, so resubmitting the job picks them up
    queue = list(zip(todo.market_id, todo.conditionId, todo.duration_days))
    for pass_no in (0, 1):
        for (mid, cond, dur), t, err in fetch_many(queue, lambda it: fetch_all(it[1], lim), workers):
            st["seen"] += pass_no == 0
            if err:
                failed.append((mid, cond, dur))
                print(f"  failed {mid}: {err}", flush=True)
                continue
            if len(t):
                t["day"] = pd.to_datetime(t.ts, unit="s", utc=True).dt.floor("D")
                t["usd"] = t["size"] * t.price
                g = t.groupby("day")
                dd = pd.DataFrame({"n_trades": g.size(), "shares": g["size"].sum(), "usd": g.usd.sum(),
                                   "n_buy": g.side.apply(lambda s: (s == "BUY").sum()),
                                   "n_sell": g.side.apply(lambda s: (s == "SELL").sum()),
                                   "n_wallets": g.wallet.nunique()}).reset_index()
                dd.insert(0, "market_id", mid)
                daily.append(dd)
                if dur >= RAW_MIN_DAYS:
                    raw.append(t.drop(columns=["day", "usd"]).assign(market_id=mid))
                st["n_tr"] += len(t)
                st["buf"] += len(t)
            ids.append(mid)
            if len(ids) >= PART_MARKETS or st["buf"] >= PART_TRADES:
                flush()
        queue, failed = failed, []
        if not queue:
            break
    failed = queue if pass_no == 1 else []
    if ids:
        flush()
    print(f"shard {a.shard} finished; {len(failed):,} markets still failing (resubmit to retry)", flush=True)

if __name__ == "__main__":
    main()
