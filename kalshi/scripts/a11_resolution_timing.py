"""When does the outcome become known, relative to the market's close? (Kalshi, settled markets)

Same contract-day panel as a10 (daily price = bid/ask midpoint if two-sided, else last trade).
Per market:
  settle_lag_h      settlement_ts - close_time, hours
  close_vs_exp_h    close_time - expected_expiration_time, hours (> 0: trading went on after the
                    time Kalshi expected the outcome to be known)
  locked_tail_days  panel days at the end of the market's life with the price within LOCK of the
                    final outcome on every day (the outcome already looks settled)
  final_locked      the last panel day is within LOCK of the outcome
Per market-day:
  in_locked_tail    the day is in that tail
  after_expected    the day starts after expected_expiration_time

Writes results/11_resolution_timing.csv (one row per duration group and the two a10 samples).
"""
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from common import D, R, keep

LOCK = 0.02

m = pd.read_parquet(f"{D}/markets.parquet", columns=[
    "ticker", "event_ticker", "status", "result", "close_time", "expected_expiration_time", "settlement_ts",
    "can_close_early", "horizon_days", "category"])
m = keep(m[(m.status == "finalized") & m.result.isin(["yes", "no"])]).copy()
m["y"] = (m.result == "yes").astype(np.float64)
m["settle_lag_h"] = (m.settlement_ts - m.close_time).dt.total_seconds() / 3600
m["close_vs_exp_h"] = (m.close_time - m.expected_expiration_time).dt.total_seconds() / 3600

t = pq.read_table(f"{D}/candles_daily.parquet", columns=["ticker", "day", "price_close", "bid_close", "ask_close"])
t = t.filter(pc.is_in(t.column("ticker"), value_set=pa.array(m.ticker.tolist()))).to_pandas()
two = (t.bid_close > 0) & (t.ask_close < 1) & (t.ask_close > t.bid_close)
t["price"] = np.where(two, (t.bid_close + t.ask_close) / 2, t.price_close)
t = t.dropna(subset=["price"]).drop(columns=["price_close", "bid_close", "ask_close"])
t = t.merge(m[["ticker", "y", "close_time", "expected_expiration_time"]], on="ticker")
t = t[t.close_time >= t.day].sort_values(["ticker", "day"])
t["brier"] = (t.price - t.y) ** 2
t["locked"] = (t.price - t.y).abs() <= LOCK
# a day is in the locked tail if it and every later day of the market are locked
t["in_locked_tail"] = t.iloc[::-1].groupby("ticker").locked.cummin().iloc[::-1].to_numpy()
t["is_final"] = ~t.ticker.duplicated(keep="last")
t["after_expected"] = t.day > t.expected_expiration_time
per = t.groupby("ticker").agg(panel_days=("day", "size"), locked_tail_days=("in_locked_tail", "sum"))
per["final_locked"] = t[t.is_final].set_index("ticker").locked
m = m.merge(per.reset_index(), on="ticker")
t = t.merge(m[["ticker", "horizon_days"]], on="ticker")
print(f"{len(m):,} markets with panel days, {len(t):,} market-days")

BUCKETS = [(0, 1, "< 1 day"), (1, 7, "1-7 days"), (7, 30, "7-30 days"), (30, 180, "30-180 days"), (180, 1e9, "> 180 days")]


def summarize(name, mm, tt):
    return {
        "group": name, "markets": len(mm), "market_days": len(tt),
        "settle_lag_h_median": mm.settle_lag_h.median(),
        "settle_lag_over_1d": (mm.settle_lag_h > 24).mean(),
        "close_after_expected_over_1d": (mm.close_vs_exp_h > 24).mean(),
        "close_before_expected_over_1d": (mm.close_vs_exp_h < -24).mean(),
        "can_close_early": mm.can_close_early.mean(),
        "final_day_locked": mm.final_locked.mean(),
        "locked_tail_days_median": mm.locked_tail_days.median(),
        "locked_tail_days_p90": mm.locked_tail_days.quantile(0.9),
        "locked_tail_over_7d": (mm.locked_tail_days > 7).mean(),
        "rows_in_locked_tail": tt.in_locked_tail.mean(),
        "rows_final_day": tt.is_final.mean(),
        "rows_after_expected": tt.after_expected.mean(),
        "brier_final_day": tt.loc[tt.is_final, "brier"].mean(),
        "brier_other_days": tt.loc[~tt.is_final, "brier"].mean(),
    }


rows = [summarize("all", m, t)]
for lo, hi, name in BUCKETS:
    rows.append(summarize(name, m[(m.horizon_days >= lo) & (m.horizon_days < hi)],
                          t[(t.horizon_days >= lo) & (t.horizon_days < hi)]))
long_m = m[m.horizon_days > 180]
for cat in long_m.category.value_counts().index[:4]:
    rows.append(summarize(f"> 180 days: {cat}", long_m[long_m.category == cat],
                          t[(t.horizon_days > 180) & t.ticker.isin(long_m.ticker[long_m.category == cat])]))
out = pd.DataFrame(rows)
out.to_csv(f"{R}/11_resolution_timing.csv", index=False)
pd.set_option("display.width", 250)
print(out.round(3).T.to_string())
