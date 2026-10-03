"""Shared helpers for the Polymarket pipeline: paths, rate-limited HTTP, selection."""
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("PM_DATA", os.path.join(ROOT, "data"))
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
DATA_API = "https://data-api.polymarket.com"
# the Data API has no trades before this date, so markets that started earlier have incomplete volume
TRADES_FROM = "2023-09-30"
# categories left out of the analyses, as in kalshi/scripts/common.py (KL_ALL_CATEGORIES=1 keeps them)
EXCLUDE = [] if os.environ.get("KL_ALL_CATEGORIES") else ["Sports", "Crypto"]


class RateLimiter:
    """Allow at most `rate` calls per second from this process."""

    def __init__(self, rate):
        self.interval = 1.0 / float(rate)
        self.next_t = time.monotonic()
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            now = time.monotonic()
            if now < self.next_t:
                time.sleep(self.next_t - now)
            self.next_t = max(now, self.next_t) + self.interval


_LOCAL = threading.local()


def session():
    """One requests.Session per thread."""
    if not hasattr(_LOCAL, "s"):
        _LOCAL.s = requests.Session()
    return _LOCAL.s


def get_json(url, params, limiter=None, tries=12, max_sleep=120, quiet=False):
    """GET with retries on 429/5xx/network errors; about 12 minutes of backoff before giving up."""
    last = None
    for attempt in range(tries):
        if limiter:
            limiter.wait()
        try:
            r = session().get(url, params=params, timeout=60)
            if r.status_code == 429 or r.status_code >= 500:
                last = f"HTTP {r.status_code}"
            else:
                return r.json()
        except (requests.RequestException, ValueError) as e:
            last = type(e).__name__
        if attempt >= 3 and not quiet:
            print(f"  retry {attempt + 1}/{tries} ({last}) {url}", flush=True)
        time.sleep(min(max_sleep, 2 ** attempt))
    raise RuntimeError(f"giving up ({last}) on {url} {params}")


def fetch_many(items, fn, workers, chunk=200):
    """Run fn over items on `workers` threads, a chunk at a time; yield (item, result, error) in order."""
    with ThreadPoolExecutor(workers) as ex:
        for i in range(0, len(items), chunk):
            part = items[i:i + chunk]
            futs = [ex.submit(fn, it) for it in part]
            for it, f in zip(part, futs):
                try:
                    yield it, f.result(), None
                except RuntimeError as e:
                    yield it, None, e


def shard_of(ids, n):
    return pd.util.hash_pandas_object(pd.Series(ids).astype(str), index=False).to_numpy() % n


def done_ids(pattern_dir, prefix, col="market_id"):
    """Market ids already written by earlier parts of this shard (for resuming)."""
    if not os.path.isdir(pattern_dir):
        return set()
    out = set()
    for f in os.listdir(pattern_dir):
        if f.startswith(prefix) and f.endswith(".parquet"):
            out.update(pd.read_parquet(os.path.join(pattern_dir, f), columns=[col])[col].astype(str))
    return out
