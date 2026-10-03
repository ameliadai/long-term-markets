"""Who trades long-horizon markets? Trade counts and sizes by listing horizon,
from the Jul 15 - Sep 21 2026 trade tape (daily per-market aggregates)."""
import numpy as np, pandas as pd
from common import D, R, markets

t = pd.read_parquet(f"{D}/trades_daily.parquet")
t = t.groupby(["ticker", "day"], as_index=False)[
    ["n", "contracts", "yes_notional", "n_taker_yes", "contracts_taker_yes", "n_block",
     "n_lt10", "n_10_99", "n_100_999", "n_ge1000"]].sum()
m = markets()[["ticker", "hz", "group", "horizon_days", "category"]]
t = t.merge(m, on="ticker", how="inner")      # only markets kept by common.markets()
t["hz"] = t.hz.cat.add_categories(["combo/unknown"]).fillna("combo/unknown")
t["group"] = t.group.fillna("combo/unknown")
# dollars that changed hands: yes side pays price, no side pays 1 - price
t["usd"] = t.contracts  # $1 notional per contract at settlement
g = t.groupby("hz", observed=True)
out = pd.DataFrame({
    "markets_traded": g.ticker.nunique(),
    "trades_M": g.n.sum() / 1e6,
    "contracts_M": g.contracts.sum() / 1e6,
    "share_of_contracts": g.contracts.sum() / t.contracts.sum(),
    "trades_per_market_day": g.n.mean(),
    "median_trades_per_market_day": g.n.median(),
    "mean_trade_size": g.contracts.sum() / g.n.sum(),
    "share_trades_lt10": g.n_lt10.sum() / g.n.sum(),
    "share_trades_ge1000": g.n_ge1000.sum() / g.n.sum(),
    "block_trades": g.n_block.sum(),
    "taker_yes_share": g.n_taker_yes.sum() / g.n.sum(),
})
print(out.round(3).to_string())
out.to_csv(f"{R}/06_trades_by_horizon.csv")
lg = t[t.hz.isin(["6-12m", "1-2y", ">2y"])].groupby("group")
out2 = pd.DataFrame({"markets_traded": lg.ticker.nunique(), "trades": lg.n.sum(),
                     "contracts_M": lg.contracts.sum() / 1e6,
                     "trades_per_market_day": lg.n.mean(),
                     "mean_trade_size": lg.contracts.sum() / lg.n.sum()})
print(out2.round(2).to_string())
out2.to_csv(f"{R}/06_trades_long_by_group.csv")
