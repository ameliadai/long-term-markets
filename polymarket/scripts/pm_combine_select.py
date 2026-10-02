"""Combine the event snapshot parts into one market table and pick the markets to fetch.

data/pm_markets.parquet   every market (deduplicated), with parsed dates, outcome and a coarse category
data/pm_selected.parquet  resolved binary markets with volume > 0 and duration >= MIN_DURATION_HOURS
                          (default 24, i.e. skips the 5/15-minute and hourly crypto markets)
"""
import glob
import json
import os

import numpy as np
import pandas as pd

from pm_common import DATA

MIN_DURATION_HOURS = float(os.environ.get("MIN_DURATION_HOURS", "24"))

# first matching rule wins; matched against the market category, event category and event tags
CATEGORY_RULES = [
    ("Crypto", ["crypto", "bitcoin", "ethereum", "solana", "xrp", "memecoin"]),
    ("Sports", ["sports", "nba", "nfl", "mlb", "nhl", "soccer", "football", "tennis", "ufc", "golf", "f1",
                "esports", "cricket", "boxing", "ncaa", "epl", "champions league", "world cup", "olympics"]),
    ("Politics", ["politics", "election", "elections", "trump", "congress", "senate", "president", "geopolitics"]),
    ("Economy & Finance", ["economy", "economics", "finance", "fed", "inflation", "gdp", "stocks", "business",
                           "ipo", "ipos", "earnings", "interest rates", "recession"]),
    ("Tech & AI", ["tech", "ai", "openai", "science", "space", "spacex"]),
    ("Culture", ["pop culture", "culture", "entertainment", "movies", "music", "celebrities", "awards", "tv"]),
    ("World", ["world", "middle east", "ukraine", "russia", "china", "israel", "iran"]),
    ("Weather", ["weather", "climate", "temperature", "hurricane"]),
]


def coarse_category(row):
    words = [str(row.get("category") or ""), str(row.get("event_category") or "")] + str(row.get("event_tags") or "").split("|")
    words = [w.strip().lower() for w in words if w and w.strip() and w.strip().lower() != "all"]
    for name, keys in CATEGORY_RULES:
        if any(w in keys for w in words):
            return name
    return "Other"


def ts(s):
    return pd.to_datetime(s.astype(str).str.replace(" ", "T", regex=False).replace({"None": None, "nan": None}),
                          format="ISO8601", utc=True, errors="coerce")


def parse_list(s):
    try:
        v = json.loads(s) if isinstance(s, str) else s
        return v if isinstance(v, list) else None
    except (ValueError, TypeError):
        return None


def main():
    files = sorted(glob.glob(os.path.join(DATA, "events", "*_part*.parquet")))
    m = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    m["id"] = m["id"].astype(str)
    m = m.sort_values("closed").drop_duplicates("id", keep="last")   # a closed record beats an open duplicate
    m["start"] = ts(m.startDate).fillna(ts(m.createdAt))
    m["end"] = ts(m.closedTime).fillna(ts(m.endDate))
    m["duration_days"] = (m.end - m.start).dt.total_seconds() / 86400
    toks = m.clobTokenIds.map(parse_list)
    m["yes_token"] = toks.map(lambda v: str(v[0]) if v else None)
    prices = m.outcomePrices.map(parse_list)
    outs = m.outcomes.map(parse_list)
    p0 = prices.map(lambda v: float(v[0]) if v and len(v) == 2 else np.nan)
    p1 = prices.map(lambda v: float(v[1]) if v and len(v) == 2 else np.nan)
    m["binary"] = outs.map(lambda v: bool(v) and len(v) == 2)
    m["resolved"] = m.closed.astype(bool) & (((p0 == 1) & (p1 == 0)) | ((p0 == 0) & (p1 == 1)))
    m["y"] = np.where(m.resolved, (p0 == 1).astype(float), np.nan)   # 1 if the first outcome (usually "Yes") won
    m["first_outcome"] = outs.map(lambda v: v[0] if v else None)
    m["category_coarse"] = m.apply(coarse_category, axis=1)
    m["volumeNum"] = pd.to_numeric(m.volumeNum, errors="coerce")
    m.to_parquet(os.path.join(DATA, "pm_markets.parquet"), index=False)

    sel = m[m.binary & m.resolved & (m.volumeNum > 0) & m.yes_token.notna()
            & (m.duration_days * 24 >= MIN_DURATION_HOURS)]
    sel = sel[["id", "conditionId", "yes_token", "event_id", "start", "end", "duration_days", "volumeNum",
               "category_coarse", "y"]].rename(columns={"id": "market_id"})
    sel.to_parquet(os.path.join(DATA, "pm_selected.parquet"), index=False)
    print(f"markets {len(m):,}; resolved binary {int((m.binary & m.resolved).sum()):,}; "
          f"selected (volume > 0, duration >= {MIN_DURATION_HOURS:g} h) {len(sel):,}; "
          f"selected with duration > 180 days {int((sel.duration_days > 180).sum()):,}")
    print(sel.category_coarse.value_counts().to_string())


if __name__ == "__main__":
    main()
