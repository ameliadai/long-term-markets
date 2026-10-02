#!/usr/bin/env python
"""Collect everything the website shows into website/data/site.json.
  python website/build_site.py     then     cd website && python3 -m http.server 8767
Re-run after the analysis scripts (kalshi/scripts/a*.py, polymarket/scripts) change their outputs;
the page reads only site.json.

The Kalshi results come from kalshi/results/; the same analyses run on Polymarket (scripts with
KL_DATA=polymarket/kshape KL_RESULTS=polymarket/results) go into S["pm"] with the same keys."""
import datetime as dt
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES, DATA = ROOT / "kalshi" / "results", ROOT / "kalshi" / "data"
PM_RES, PM_KSHAPE, PM_DATA = (ROOT / "polymarket" / x for x in ("results", "kshape", "data"))
PM_SITE = PM_RES
OUT = ROOT / "website" / "data"
OUT.mkdir(parents=True, exist_ok=True)

HZ_ORDER = ["<1d", "1-7d", "7-30d", "1-3m", "3-6m", "6-12m", "1-2y", ">2y"]
HZ_LABEL = {"<1d": "< 1 day", "1-7d": "1–7 days", "7-30d": "1–4 weeks", "1-3m": "1–3 months",
            "3-6m": "3–6 months", "6-12m": "6–12 months", "1-2y": "1–2 years", ">2y": "> 2 years"}


def rec(df):
    """DataFrame -> list of dicts with NaN -> None and floats rounded."""
    df = df.copy()
    for c in df.columns:
        if df[c].dtype.kind == "f":
            df[c] = df[c].round(6)
    return json.loads(df.to_json(orient="records"))


def core(res, data):
    """Results that both platforms have (horizons, life cycle, accuracy, liquidity, last days)."""
    def csv(name, **kw):
        return pd.read_csv(res / name, **kw)

    S = {}
    h = csv("01_horizon_landscape.csv").set_index("hz").reindex(HZ_ORDER).reset_index()
    h["label"] = h.hz.map(HZ_LABEL)
    S["horizon"] = rec(h)
    cat = csv("01_volume_by_category_horizon.csv").set_index("category")
    cat = cat[[c for c in HZ_ORDER if c in cat] + ["total"]].sort_values("total", ascending=False).head(12) / 1e6
    S["cat_horizon"] = rec(cat.reset_index())
    t = csv("06_trades_by_horizon.csv").set_index("hz")
    t = t.reindex(HZ_ORDER).reset_index()
    t["label"] = t.hz.map(HZ_LABEL)
    S["trades_hz"] = rec(t)
    S["trades_long_group"] = rec(csv("06_trades_long_by_group.csv"))
    S["vol_to_close"] = rec(csv("02_volume_to_close.csv"))

    S["accuracy"] = {H: rec(csv(f"03_accuracy_h{H}.csv")) for H in (90, 180, 365)}
    S["accuracy_group"] = rec(csv("03_accuracy_by_group.csv"))
    S["calibration"] = {k: rec(csv(f"03_calibration_k{k}.csv")) for k in (30, 90, 180)}

    q8 = csv("08_quintiles.csv")
    S["liq_quintiles"] = rec(q8[q8.k == 30])
    S["liq_regression"] = rec(csv("08_regression.csv"))
    f8 = pd.read_parquet(res / "08_market_features.parquet")
    S["liq_n"] = {int(k): {"markets": int(len(d)), "events": int(d.event_ticker.nunique())} for k, d in f8.groupby("k")}
    S["liq_equal"] = rec(csv("08_equal_sure.csv"))
    S["liq_equal_sig"] = rec(csv("08_equal_sure_sig.csv"))
    S["liq_near"] = rec(csv("08_near_certain.csv"))
    S["liq_measures"] = sorted(q8.measure.unique().tolist())
    f30 = f8[f8.k == 30]
    S["liq_dots"] = {}
    for meas, sign in {"volume": 1, "days_traded": 1, "open_interest": 1, "spread": -1}.items():
        if meas not in S["liq_measures"]:
            continue
        d = f30.dropna(subset=[meas]).copy()
        d["q"] = pd.qcut((sign * d[meas]).rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
        S["liq_dots"][meas] = [d[d.q == q].p.sample(min(600, (d.q == q).sum()), random_state=0).round(3).tolist()
                               for q in range(1, 6)]
    S["liq_sample"] = int(q8[(q8.k == 30) & (q8.measure == "volume")].markets.sum())
    S["cal_by_h"] = rec(csv("09_calibration_by_horizon.csv"))
    S["cal_curves"] = rec(csv("09_calibration_curves.csv"))
    S["fav_rob"] = rec(csv("09_favourite_robustness.csv"))
    S["fav_ref"] = rec(csv("09_fav_reference_4060.csv"))
    S["tail"] = rec(csv("11_resolution_timing.csv"))

    mk = pd.read_parquet(data / "markets.parquet", columns=["ticker", "status", "volume", "open_time", "close_time"])
    cd_t = pd.read_parquet(data / "candles_daily.parquet", columns=["ticker"]).ticker.unique()
    lm = mk[(mk.close_time - mk.open_time).dt.total_seconds() / 86400 >= 90]
    settled = lm[lm.status == "finalized"]
    active = settled[settled.volume >= 100]
    S["funnel"] = {
        "listed_90d": len(lm), "open": int((lm.status == "active").sum()),
        "other_status": int((~lm.status.isin(["active", "finalized"])).sum()), "settled": len(settled),
        "under_100": int((settled.volume < 100).sum()),
        "no_bars": int((~active.ticker.isin(set(cd_t))).sum()),
        "used": int(active.ticker.isin(set(cd_t)).sum()),
    }
    S["samples"] = {
        "horizon_markets": int(mk.open_time.notna().mul(mk.close_time.notna()).sum()),
        "accuracy": {H: int(csv(f"03_accuracy_h{H}.csv").markets.iloc[0]) for H in (90, 180, 365)},
        "accuracy_group": csv("03_accuracy_by_group.csv").query("k == 1").set_index("group").markets.astype(int).to_dict(),
        "calibration": {k: int(csv(f"03_calibration_k{k}.csv").n.sum()) for k in (30, 90, 180)},
        "trade_markets": int(t.markets_traded.sum()),
    }
    return S, mk


S = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
K, mk = core(RES, DATA)
S.update(K)


def csv(name, **kw):
    return pd.read_csv(RES / name, **kw)


# ---- Kalshi-only pieces --------------------------------------------------------------------
share = csv("06_contract_share_noncombo.csv").set_index("hz")
S["trades_share_noncombo"] = {k: float(share.loc[k, "share_noncombo_contracts"]) for k in HZ_ORDER}
S["combo"] = {"share_contracts": 0.478, "share_trades": 0.102, "share_yes_dollars": 0.106}
S["favlong"] = rec(csv("05_favourite_longshot_returns.csv"))
S["reg10"] = rec(csv("10_brier_volume_regressions.csv"))
S["reg10_cat"] = rec(csv("10_category_mix.csv"))
S["reg10_bycat"] = rec(csv("10_by_category.csv"))
S["fresh"] = rec(csv("09_reward_info_fresh.csv"))

# ---- rewards --------------------------------------------------------------------------------
ip = pd.read_parquet(DATA / "incentive_programs.parquet")
ip["start"] = pd.to_datetime(ip.start_date, format="ISO8601", utc=True)
ip["usd"] = ip.period_reward / 1e4
ip["kind"] = np.select(
    [ip.incentive_type == "volume", ip.incentive_description == "long_dated",
     ip.incentive_description == "new_event", ip.incentive_description == "series_lip"],
    ["Volume reward", "Long-dated liquidity", "New-event liquidity", "Series liquidity"],
    "Standard liquidity")
ip["month"] = ip.start.dt.strftime("%Y-%m")
mo = ip.pivot_table(index="month", columns="kind", values="usd", aggfunc="sum", fill_value=0)
S["reward_months"] = {"months": list(mo.index), "series": {k: [round(v) for v in mo[k]] for k in mo.columns},
                      "programs": ip.groupby("month").size().reindex(mo.index).tolist()}
S["reward_totals"] = {"usd": round(ip.usd.sum()), "programs": len(ip), "paid_share": float(ip.paid_out.mean()),
                      "markets": int(ip.market_ticker.nunique()),
                      "by_kind": {k: round(v) for k, v in ip.groupby("kind").usd.sum().items()},
                      "first": ip.start.min().date().isoformat(), "last": ip.start.max().date().isoformat()}
cov = csv("04_reward_coverage_by_horizon.csv").set_index("hz").loc[HZ_ORDER].reset_index()
cov["label"] = cov.hz.map(HZ_LABEL)
S["reward_coverage"] = rec(cov)
S["reward_coverage_group"] = rec(csv("04_reward_coverage_long_by_group.csv"))
S["reward_effects"] = rec(csv("04_reward_effects_twfe.csv"))
S["info_effects"] = rec(csv("05_info_vs_activity_twfe.csv"))
S["event_study"] = rec(csv("04_long_dated_event_study.csv"))

# ---- open markets now -----------------------------------------------------------------------
om = pd.read_parquet(DATA / "open_markets_enriched.parquet")
om["hz"] = om.horizon.astype(str)
g = om.groupby("hz")
o = pd.DataFrame({"markets": g.size(), "traded_ever": g.volume_fp.apply(lambda v: (v > 0).mean()),
                  "traded_24h": g.volume_24h_fp.apply(lambda v: (v > 0).mean()),
                  "two_sided": g.two_sided.mean(), "spread_med": g.spread.median()}).loc[HZ_ORDER].reset_index()
o["label"] = o.hz.map(HZ_LABEL)
S["open_now"] = rec(o)
S["open_snapshot"] = {"markets": len(om), "time": str(om.snapshot_time.iloc[0])[:16],
                      "over_1y": int((om.days_to_close > 365).sum())}
ob = pd.read_parquet(DATA / "orderbooks_enriched.parquet")
ob = ob[ob.group == "focus"]
ob["hz"] = ob.horizon.astype(str)
gb = ob.groupby("hz")
S["orderbook_focus"] = rec(pd.DataFrame({
    "markets": gb.size(), "two_sided": gb.two_sided.mean(), "spread_med": gb.spread.median(),
    "depth5_med": gb.depth5.median(), "traded_24h": gb.volume_24h_fp.apply(lambda v: (v > 0).mean())})
    .reindex([k for k in HZ_ORDER if k in gb.groups]).reset_index().assign(label=lambda d: d.hz.map(HZ_LABEL)))

# ---- data inventory and analysis samples (Data tab) -----------------------------------------
mve = pd.read_parquet(DATA / "mve_summary.parquet")
cd = pd.read_parquet(DATA / "candles_daily.parquet", columns=["ticker", "day", "n_bars"])
td = pd.read_parquet(DATA / "trades_daily.parquet", columns=["day", "n", "contracts"])
S["inventory"] = {
    "markets": len(mk), "markets_traded": int((mk.volume > 0).sum()),
    "markets_settled": int((mk.status == "finalized").sum()), "markets_open": int((mk.status == "active").sum()),
    "markets_close_2026": float((mk.close_time.dt.year == 2026).mean()),
    "combos": int(mve.n.sum()), "events": len(pd.read_parquet(DATA / "events.parquet", columns=["event_ticker"])),
    "series": len(pd.read_parquet(DATA / "series.parquet", columns=["ticker"])),
    "bars": int(cd.n_bars.sum()), "bar_markets": int(cd.ticker.nunique()), "bar_days": len(cd),
    "bar_first": cd.day.min().date().isoformat(), "bar_last": cd.day.max().date().isoformat(),
    "trades": int(td.n.sum()), "trade_contracts": float(td.contracts.sum()),
    "trade_first": str(td.day.min()), "trade_last": str(td.day.max()),
    "orderbooks": len(pd.read_parquet(DATA / "orderbooks_snapshot.parquet", columns=["ticker"])),
}
samp = {k: json.loads((RES / f"{k}_sample.json").read_text()) for k in ("04", "05")}
S["samples"].update({
    "panel": samp["04"], "settled_panel": samp["05"],
    "coverage_markets": int(cov.markets.sum()),
    "event_study_markets": int(csv("04_long_dated_event_study.csv").markets.max()),
})

# ---- Polymarket -----------------------------------------------------------------------------
if (PM_SITE / "11_resolution_timing.csv").exists():
    P, _ = core(PM_SITE, PM_KSHAPE)
    for key, name in [("reg", "pm_brier_volume_regressions.csv"), ("reg_cat", "pm_category_mix.csv"),
                      ("reg_bycat", "pm_by_category.csv")]:
        P[key] = rec(pd.read_csv(PM_RES / name)) if (PM_RES / name).exists() else []
    pm = pd.read_parquet(PM_DATA / "pm_markets.parquet", columns=[
        "closed", "resolved", "binary", "volumeNum", "holdingRewardsEnabled", "rewardsMinSize", "event_id", "start", "end"])
    sel = pd.read_parquet(PM_DATA / "pm_selected.parquet", columns=["market_id", "duration_days", "start"])
    sel = sel[sel.start >= pd.Timestamp("2023-09-30", tz="UTC")]     # TRADES_FROM in polymarket/scripts/pm_common.py
    pc_ = pd.read_parquet(PM_KSHAPE / "candles_daily.parquet", columns=["ticker", "day", "price_close"])
    ptd = pd.read_parquet(PM_KSHAPE / "trades_daily.parquet", columns=["day", "n", "contracts"])
    open_ = pm[~pm.closed.astype(bool)]
    P["inventory"] = {
        "markets": len(pm), "events": int(pm.event_id.nunique()),
        "markets_traded": int((pd.to_numeric(pm.volumeNum, errors="coerce") > 0).sum()),
        "markets_resolved": int(pm.resolved.sum()), "markets_open": len(open_), "markets_binary": int(pm.binary.sum()),
        "selected": len(sel), "selected_180": int((sel.duration_days > 180).sum()),
        "price_days": int(pc_.price_close.notna().sum()), "price_markets": int(pc_[pc_.price_close.notna()].ticker.nunique()),
        "price_first": pc_.day.min().date().isoformat(), "price_last": pc_.day.max().date().isoformat(),
        "trades": int(ptd.n.sum()), "trade_shares": float(ptd.contracts.sum()),
        "trade_first": str(ptd.day.min())[:10], "trade_last": str(ptd.day.max())[:10],
        "first_start": str(pm.start.min())[:10], "last_end": str(pm["end"].max())[:10],
        "open_holding_rewards": int(open_.holdingRewardsEnabled.fillna(False).astype(bool).sum()),
        "open_liquidity_rewards": int((pd.to_numeric(open_.rewardsMinSize, errors="coerce") > 0).sum()),
    }
    S["pm"] = P

def clean(o):
    """NaN/inf -> None anywhere in the structure (JSON has no NaN)."""
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    if isinstance(o, float) and not np.isfinite(o):
        return None
    return o


(OUT / "site.json").write_text(json.dumps(clean(S), separators=(",", ":"), allow_nan=False))
print("wrote", OUT / "site.json", f"{(OUT / 'site.json').stat().st_size / 1e3:.0f} KB")
