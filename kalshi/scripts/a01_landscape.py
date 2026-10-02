"""How many markets and how much volume at each listing horizon, by category."""
import pandas as pd
from common import R, markets

m = markets()
g = m.groupby("hz", observed=True)
t = pd.DataFrame({"markets": g.size(), "traded_share": g.volume.apply(lambda v: (v > 0).mean()),
                  "resolved_share": g.status.apply(lambda s: s.isin(["finalized", "determined"]).mean()),
                  "volume_M": g.volume.sum() / 1e6, "vol_share": g.volume.sum() / m.volume.sum(),
                  "med_vol_traded": g.volume.apply(lambda v: v[v > 0].median())})
print(t.round(3).to_string())
t.to_csv(f"{R}/01_horizon_landscape.csv")
cat = m.pivot_table(index="category", columns="hz", values="volume", aggfunc="sum", observed=True).fillna(0)
cat["total"] = cat.sum(axis=1)
cat.sort_values("total", ascending=False).to_csv(f"{R}/01_volume_by_category_horizon.csv")
