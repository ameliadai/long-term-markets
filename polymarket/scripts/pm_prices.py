"""Daily price history for each selected market (CLOB /prices-history, first-outcome token).

interval=max&fidelity=1440 returns one point per day over the market's whole life.
Shard S of N handles the selected markets whose id hashes to S, longest-lived first, on
PM_WORKERS threads. Parts are written every PART_MARKETS markets, with a done-list, so a
killed job resumes where it stopped.

usage: python pm_prices.py SHARD NSHARDS [--limit N]
       env PM_RATE = requests/s for this shard (default 10), PM_WORKERS = threads (default 8)
"""
import argparse
import os

import pandas as pd

from pm_common import CLOB, DATA, RateLimiter, done_ids, fetch_many, get_json, shard_of

PART_MARKETS = 2000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shard", type=int)
    ap.add_argument("nshards", type=int)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    out = os.path.join(DATA, "prices")
    os.makedirs(out, exist_ok=True)
    sel = pd.read_parquet(os.path.join(DATA, "pm_selected.parquet"), columns=["market_id", "yes_token", "duration_days"])
    sel = sel[shard_of(sel.market_id, a.nshards) == a.shard].sort_values("duration_days", ascending=False)
    prefix = f"shard{a.shard:02d}_"
    done = done_ids(out, prefix + "done_")
    todo = sel[~sel.market_id.isin(done)]
    if a.limit:
        todo = todo.head(a.limit)
    part = len([f for f in os.listdir(out) if f.startswith(prefix + "done_")])
    print(f"shard {a.shard}/{a.nshards}: {len(sel):,} markets, {len(done):,} done, {len(todo):,} to fetch", flush=True)
    lim = RateLimiter(float(os.environ.get("PM_RATE", "10")))
    workers = int(os.environ.get("PM_WORKERS", "8"))
    rows, ids, failed = [], [], []
    part_box = [part]

    def flush():
        pd.DataFrame(rows, columns=["market_id", "t", "p"]).to_parquet(
            os.path.join(out, f"{prefix}part{part_box[0]:05d}.parquet"), index=False)
        pd.DataFrame({"market_id": ids}).to_parquet(os.path.join(out, f"{prefix}done_{part_box[0]:05d}.parquet"), index=False)
        print(f"  {n_seen:,}/{len(todo):,} markets, part {part_box[0]}, {len(rows):,} points, {len(failed):,} failed", flush=True)
        part_box[0] += 1
        rows.clear()
        ids.clear()

    # markets that still fail after get_json's retries are tried once more at the end;
    # any left are not marked done, so resubmitting the job picks them up
    queue, n_seen = list(zip(todo.market_id, todo.yes_token)), 0
    for pass_no in (0, 1):
        fetch = lambda it: get_json(f"{CLOB}/prices-history", {"market": it[1], "interval": "max", "fidelity": 1440}, lim)
        for (mid, tok), d, err in fetch_many(queue, fetch, workers):
            n_seen += pass_no == 0
            if err:
                failed.append((mid, tok))
                print(f"  failed {mid}: {err}", flush=True)
                continue
            for pt in (d.get("history") or []) if isinstance(d, dict) else []:
                rows.append((mid, int(pt["t"]), float(pt["p"])))
            ids.append(mid)
            if len(ids) >= PART_MARKETS:
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
