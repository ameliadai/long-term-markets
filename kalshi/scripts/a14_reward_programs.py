"""What reward programs Kalshi runs, and which categories get them.

1. Program kinds (all programs, all categories): Kalshi's API labels each program with a type
   (liquidity or volume) and a description ('' = standard, new_event, series_lip, long_dated).
   For each kind: programs, markets, dollars posted, dates, median dollars and length per
   program, and when programs start relative to the market's open and close (markets that are
   in the market list only, i.e. almost only markets still open on 14 Jul 2026 or later).
2. Coverage by category (markets in the market list closing in 2026 or later, sports and crypto
   left out, as in a04's coverage by horizon): share of markets ever given a liquidity reward, share given a
   long-dated reward, reward dollars per 1,000 contracts traded, and share of reward dollars.

Writes results/14_program_kinds.csv and results/14_reward_coverage_by_category.csv.
"""
import numpy as np
import pandas as pd

from common import D, R, markets

ip = pd.read_parquet(f"{D}/incentive_programs.parquet")
for c in ["start_date", "end_date"]:
    ip[c] = pd.to_datetime(ip[c], format="ISO8601", utc=True)
ip["usd"] = ip.period_reward / 1e4
ip["kind"] = np.where(ip.incentive_type == "volume", "volume",
                      ip.incentive_description.replace("", "standard"))
ip["hours"] = (ip.end_date - ip.start_date).dt.total_seconds() / 3600

# ---------------------------------------------------------------- 1. program kinds
allm = pd.read_parquet(f"{D}/markets.parquet", columns=["ticker", "open_time", "close_time"])
x = ip.merge(allm, left_on="market_ticker", right_on="ticker", how="left")
x["days_since_open"] = (x.start_date - x.open_time).dt.total_seconds() / 86400
x["days_to_close"] = (x.close_time - x.start_date).dt.total_seconds() / 86400
g = x.groupby("kind")
kinds = pd.DataFrame({
    "programs": g.size(),
    "markets": g.market_ticker.nunique(),
    "usd": g.usd.sum(),
    "first_start": g.start_date.min().dt.strftime("%Y-%m-%d"),
    "last_start": g.start_date.max().dt.strftime("%Y-%m-%d"),
    "median_usd": g.usd.median(),
    "median_hours": g.hours.median(),
    "share_starting_at_open": g.days_since_open.apply(lambda s: (s.dropna() < 1 / 24).mean()),
    "median_days_since_open": g.days_since_open.median(),
    "median_days_to_close": g.days_to_close.median(),
    "share_closing_within_1d": g.days_to_close.apply(lambda s: (s.dropna() < 1).mean()),
    "share_over_180d_left": g.days_to_close.apply(lambda s: (s.dropna() > 180).mean()),
    "matched_share": g.ticker.apply(lambda s: s.notna().mean()),
}).reset_index()
print(kinds.round(3).to_string())
kinds.to_csv(f"{R}/14_program_kinds.csv", index=False)

# ---------------------------------------------------------------- 2. coverage by category
m = markets()
m = m[m.close_time >= "2026-01-01"]
ip["k3"] = np.where(ip.kind == "volume", "rw_volume", np.where(ip.kind == "long_dated", "rw_long_dated", "rw_liquidity"))
per = ip.groupby(["market_ticker", "k3"]).usd.sum().unstack(fill_value=0)
m = m.join(per, on="ticker")
k3 = ["rw_liquidity", "rw_long_dated", "rw_volume"]
m[k3] = m[k3].fillna(0)
m["rw_usd"] = m[k3].sum(axis=1)
m["any_liq"] = (m.rw_liquidity + m.rw_long_dated) > 0
gc = m.groupby("category")
cov = pd.DataFrame({
    "markets": gc.size(),
    "share_liquidity_reward": gc.any_liq.mean(),
    "share_long_dated": gc.rw_long_dated.apply(lambda s: (s > 0).mean()),
    "reward_usd": gc.rw_usd.sum(),
    "volume_contracts": gc.volume.sum(),
})
cov["reward_usd_per_1k_contracts"] = 1000 * cov.reward_usd / cov.volume_contracts
cov["share_of_reward_usd"] = cov.reward_usd / cov.reward_usd.sum()
cov = cov.sort_values("markets", ascending=False)
print("\n== coverage by category ==")
print(cov.round(3).to_string())
cov.to_csv(f"{R}/14_reward_coverage_by_category.csv")
