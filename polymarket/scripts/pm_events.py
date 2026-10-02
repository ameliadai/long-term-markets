"""Snapshot every Polymarket event with its markets (Gamma /events/keyset), resumably.

The keyset endpoint is walked one page at a time, so the events are split into chains that
run in parallel threads, each with its own filter on the event's startDate:
  closed=false  windows covering all start dates, each walked by increasing id
  closed=true   weekly windows from SEQ_START on, walked by increasing id, plus one chain for
                start dates before SEQ_START walked by decreasing id down to SEQ_MAX_ID.
                Closed events with id <= SEQ_MAX_ID are in true_part00000-00009 (a single
                chain over all closed events, which stopped there).
Duplicates between chains are dropped in pm_combine_select.py. Events with no startDate
(about 4 in 100,000) are not returned by any window.

One output row per market, carrying its event's title, tags and category. Each chain saves
parts to data/events/<chain>_partNNNNN.parquet and its cursor to data/events/<chain>_state.json,
so a killed job resumes where it stopped.

usage: python pm_events.py [--workers N] [--only CHAIN] [--max-pages N]
"""
import argparse
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from pm_common import DATA, GAMMA, RateLimiter, get_json

PART_PAGES = 100
PAGE_SIZES = [100, 99, 50, 20, 5, 1]
SEQ_START = pd.Timestamp("2026-05-15", tz="UTC")
SEQ_MAX_ID = 513907
LAST_WEEK = pd.Timestamp("2026-10-01", tz="UTC")
EV_FIELDS = ["id", "title", "slug", "category", "startDate", "endDate", "closedTime", "enableNegRisk", "seriesSlug"]
MK_FIELDS = ["id", "conditionId", "question", "slug", "category", "startDate", "createdAt", "endDate", "closedTime",
             "volumeNum", "liquidityNum", "closed", "active", "outcomes", "outcomePrices", "clobTokenIds",
             "umaResolutionStatuses", "holdingRewardsEnabled", "rewardsMinSize", "rewardsMaxSpread",
             "feesEnabled", "marketType", "fpmmLive", "negRiskOther"]
LOG = threading.Lock()


def log(msg):
    with LOG:
        print(msg, flush=True)


def iso(t):
    return pd.Timestamp(t).strftime("%Y-%m-%dT%H:%M:%SZ")


def chains():
    """(name, params, stop_at_id) for every chain."""
    weeks = list(pd.date_range(SEQ_START, LAST_WEEK, freq="7D"))
    weeks = [w for w in weeks if w < LAST_WEEK] + [LAST_WEEK]
    weekly = [(f"w{a:%Y%m%d}", {"start_date_min": iso(a), "start_date_max": iso(b)}) for a, b in zip(weeks, weeks[1:])]
    weekly.append((f"w{LAST_WEEK:%Y%m%d}", {"start_date_min": iso(LAST_WEEK)}))
    edges = [None, "2025-01-01", "2025-07-01", "2026-01-01", "2026-03-01", SEQ_START]
    early = []
    for a, b in zip(edges, edges[1:]):
        p = {"start_date_max": iso(b)}
        if a is not None:
            p["start_date_min"] = iso(a)
        early.append((f"s{pd.Timestamp(b):%Y%m%d}", p))
    out = [("true_before", {"closed": "true", "start_date_max": iso(SEQ_START), "order": "id", "ascending": "false"},
            SEQ_MAX_ID)]
    out += [(f"true_{n}", {"closed": "true", **p}, None) for n, p in weekly]
    out += [(f"false_{n}", {"closed": "false", **p}, None) for n, p in early + weekly]
    return out


def rows_from(events):
    out = []
    for e in events:
        tags = "|".join(t.get("label", "") for t in (e.get("tags") or []))
        ev = {f"event_{k}": e.get(k) for k in EV_FIELDS}
        ev["event_tags"] = tags
        for m in e.get("markets") or []:
            row = {k: m.get(k) for k in MK_FIELDS}
            row.update(ev)
            out.append(row)
    return out


def fetch_page(params, cursor, lim, name):
    """One keyset page. Gamma sometimes returns 500 for a page size at a given cursor while
    other sizes work, so fall back to smaller pages, then wait and cycle again."""
    for cycle in range(6):
        for size in PAGE_SIZES:
            p = {**params, "limit": size}
            if cursor:
                p["after_cursor"] = cursor
            try:
                return get_json(f"{GAMMA}/events/keyset", p, lim, tries=5 if size == 100 else 3, quiet=True)
            except RuntimeError:
                log(f"  [{name}] page size {size} failed")
        time.sleep(600)
    raise RuntimeError(f"keyset page failed at every size, cursor={cursor}")


def run_chain(name, params, stop_at_id, lim, out_dir, max_pages=0):
    state_f = os.path.join(out_dir, f"{name}_state.json")
    state = json.load(open(state_f)) if os.path.exists(state_f) else {"cursor": None, "part": 0, "pages": 0, "done": False}
    if state["done"]:
        return
    buf, pages, since = [], 0, 0
    cursor = state["cursor"]
    while True:
        d = fetch_page(params, cursor, lim, name)
        got = d.get("events") or []
        evs = [e for e in got if stop_at_id is None or int(e["id"]) > stop_at_id]
        buf += rows_from(evs)
        pages += 1
        since += 1
        cursor = d.get("next_cursor")
        exhausted = not cursor or not got or len(evs) < len(got)
        finished = exhausted or (max_pages and pages >= max_pages)
        if since >= PART_PAGES or finished:
            if buf:
                df = pd.DataFrame(buf)
                for c in df.columns:
                    if df[c].map(lambda v: isinstance(v, (list, dict))).any():
                        df[c] = df[c].map(json.dumps)
                df.to_parquet(os.path.join(out_dir, f"{name}_part{state['part']:05d}.parquet"), index=False)
                state["part"] += 1
            state.update(cursor=cursor, pages=state["pages"] + since, done=bool(exhausted))
            json.dump(state, open(state_f, "w"))
            log(f"[{name}] pages={state['pages']} parts={state['part']} markets_in_part={len(buf)}"
                + (" done" if exhausted else ""))
            buf, since = [], 0
        if finished:
            return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--only", default="")
    ap.add_argument("--max-pages", type=int, default=0)
    a = ap.parse_args()
    out_dir = os.path.join(DATA, "events")
    os.makedirs(out_dir, exist_ok=True)
    todo = [c for c in chains() if not a.only or c[0] == a.only]
    log(f"{len(todo)} chains: " + ", ".join(c[0] for c in todo))
    lim = RateLimiter(30)
    failed = []
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(run_chain, n, p, s, lim, out_dir, a.max_pages): n for n, p, s in todo}
        for f, n in futs.items():
            try:
                f.result()
            except Exception as e:
                failed.append(n)
                log(f"[{n}] FAILED: {e}")
    if failed:
        raise SystemExit(f"{len(failed)} chains failed (resubmit to resume): {failed}")
    log("all chains done")


if __name__ == "__main__":
    main()
