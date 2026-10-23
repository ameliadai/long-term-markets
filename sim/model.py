"""Agent-based simulation of a Kalshi-style yes/no market, for comparing policies.

One contract pays $1 if the event happens. Time runs in days until resolution; each day has a
number of trading slots. Many markets are simulated at once (vectorised over markets).

Information. The outcome Y is drawn at the start from the prior. Information arrives as signals
whose log-likelihood ratio for Y, given Y, is normal with mean +-2k and variance 4k ("k units").
Each day brings public news (seen by everyone) and private signals (each informed trader gets
their own). info_total is the total units over the market's life; public_share splits it between
public and private; info_shape sets the timing (0 = evenly over time, larger = concentrated near
resolution).

Traders. In each slot, an informed trader arrives with probability informed_rate and a noise trader
with probability noise_rate. Noise traders buy or sell at random. An informed trader's belief is
the public information plus their own private signals; they buy if the payoff they expect,
discounted to resolution at their discount rate, beats the ask plus a fee, and sell (buy "no") in
the mirror case. Extension: each day informed traders can pay effort_cost to get effort_info more
units of private information, which they keep; they do so when the expected gain in trading profit
until resolution is larger.

Market maker. A competitive market maker knows the setup (but not who is informed) and sets the
ask and bid at its expected value of the contract after a buy or a sell (Glosten-Milgrom), plus an
add-on for the capital it must lock up until resolution. It updates its belief from public news
and from trades (learn_from_no_trade=True also lets it learn from slots without a trade). Quotes
are in [0.005, 0.995] with a 1 cent minimum spread.

Policies (all off by default):
  interest_subsidy   annual rate paid on collateral; lowers traders' and the market maker's
                     effective discount rates. Cost: rate x collateral x time to resolution.
  mm_subsidy         $ per contract traded paid to the market maker, passed into tighter quotes.
                     Cost: subsidy x contracts traded.
  extra_noise_rate   our own random trades (probability per slot). Cost: what they lose.
  panel_rate         paid informed traders (probability per slot) with the same information as
                     other informed traders; we cover their fee and the capital cost that would
                     otherwise stop them trading, so they neither discount nor pay a fee. Cost:
                     per panel trade, the fee plus informed_discount x time to resolution (an upper
                     bound: capital cost on $1, while a panelist puts up only the price).
  forecast_day       a second contract settles on that day at a panel's published forecast F of
                     the event's probability (YES pays F, NO pays 1 - F). The panel does not trade;
                     it sees the public information on that day plus its own research worth
                     forecast_info units, so F = sigmoid(public log-odds + research signal). Until
                     then the contract trades alongside the main one, with the same market maker
                     (shared belief about Y) and traders arriving at the same rates; a trader with
                     belief p values it at F0 + (F1 - F0) p, where Fy = E[F | Y = y, public
                     information today], discounted only to forecast_day. On that day the panel's
                     research becomes public. Cost: forecast_cost (the panel's fees).
"""
from dataclasses import dataclass, replace

import numpy as np
from scipy.special import expit, logit, ndtr

PRIOR_SD = 1.0          # spread of markets' starting log-odds across markets
TICK = 0.01
BISECT = 22             # bisection steps for the quotes


@dataclass(frozen=True)
class Params:
    T: int = 365
    slots: int = 4
    info_total: float = 2.6
    public_share: float = 0.6
    info_shape: float = 0.5
    informed_rate: float = 0.012
    noise_rate: float = 0.06
    informed_discount: float = 0.15
    fee: float = 0.01
    effort_cost: float = 0.0
    effort_info: float = 0.0
    informed_pool: int = 20
    mm_discount: float = 0.08
    mm_capital: float = 0.5
    learn_from_no_trade: bool = False
    interest_subsidy: float = 0.0
    mm_subsidy: float = 0.0
    extra_noise_rate: float = 0.0
    panel_rate: float = 0.0
    forecast_day: int = -1
    forecast_info: float = 0.0
    forecast_cost: float = 0.0

    def with_(self, **kw):
        return replace(self, **kw)


def info_profile(p):
    """Units of information arriving on each day (sums to info_total)."""
    g = ((np.arange(p.T) + 1) / p.T) ** p.info_shape
    return p.info_total * g / g.sum()


def _p_side(x, K, sy, side):
    """P(an informed trader buys / sells | Y) when they trade iff their private log-odds S > x (buy) or
    S < x (sell); S | Y ~ N(2K sy, 4K)."""
    sd = 2 * np.sqrt(K)
    if side == "buy":
        return ndtr((2 * K * sy - x) / sd)
    return ndtr((x - 2 * K * sy) / sd)


def _thresholds(ask, bid, l_pub, D, fee, F0=0.0, Fd=1.0):
    """Private log-odds above which an informed trader buys, and below which they sell, for a contract
    worth F0 + Fd * P(Y = 1) at settlement (F0 = 0, Fd = 1 for the main contract)."""
    pb = ((ask + fee) / D - F0) / Fd
    xb = np.where(pb >= 1, np.inf, np.where(pb <= 0, -np.inf, logit(np.clip(pb, 1e-12, 1 - 1e-12)))) - l_pub
    ps = (1 - F0 - (1 - bid + fee) / D) / Fd
    xs = np.where(ps >= 1, np.inf, np.where(ps <= 0, -np.inf, logit(np.clip(ps, 1e-12, 1 - 1e-12)))) - l_pub
    return xb, xs


class Market:
    """State of n markets and the slot mechanics; see the module docstring."""

    def __init__(self, p, n, rng):
        self.p, self.n, self.rng = p, n, rng
        self.l0 = rng.normal(0, PRIOR_SD, n)
        self.y = (rng.random(n) < expit(self.l0)).astype(float)
        self.sy = 2 * self.y - 1
        self.l_pub = self.l0.copy()
        self.l_mm = self.l0.copy()
        self.K = np.full(n, 1e-9)
        self.cost = np.zeros(n)
        self.trades_today = np.zeros(n)
        self.F0, self.Fd = 0.0, 1.0       # settlement value = F0 + Fd * P(Y = 1)

    def likelihoods(self, ask, bid, D, D_panel, fee):
        """P(buy | Y), P(sell | Y) for Y = 1 and 0 at the given quotes."""
        p = self.p
        xb, xs = _thresholds(ask, bid, self.l_pub, D, fee, self.F0, self.Fd)
        out = {}
        for y, sy in ((1, 1.0), (0, -1.0)):
            buy = p.informed_rate * _p_side(xb, self.K, sy, "buy") + (p.noise_rate + p.extra_noise_rate) / 2
            sell = p.informed_rate * _p_side(xs, self.K, sy, "sell") + (p.noise_rate + p.extra_noise_rate) / 2
            if p.panel_rate:
                pxb, pxs = _thresholds(ask, bid, self.l_pub, D_panel, 0.0, self.F0, self.Fd)
                buy = buy + p.panel_rate * _p_side(pxb, self.K, sy, "buy")
                sell = sell + p.panel_rate * _p_side(pxs, self.K, sy, "sell")
            out[y] = (buy, sell)
        return out

    def quotes(self, D, D_panel, addon, fee, subsidy):
        """Competitive ask and bid: expected value after a buy (sell), plus (minus) the capital add-on,
        minus (plus) the per-contract subsidy. Solved by bisection (the condition is monotone)."""
        mid = self.F0 + self.Fd * expit(self.l_mm)

        def solve(side):
            lo = mid.copy() if side == "ask" else np.zeros(self.n)
            hi = np.ones(self.n) if side == "ask" else mid.copy()
            for _ in range(BISECT):
                q = (lo + hi) / 2
                a, b = (q, mid) if side == "ask" else (mid, q)
                L = self.likelihoods(a, b, D, D_panel, fee)
                k = 0 if side == "ask" else 1
                post = self.F0 + self.Fd * expit(self.l_mm + np.log(L[1][k] / L[0][k]))
                target = post + addon - subsidy if side == "ask" else post - addon + subsidy
                if side == "ask":
                    hi, lo = np.where(q > target, q, hi), np.where(q > target, lo, q)
                else:
                    lo, hi = np.where(q < target, q, lo), np.where(q < target, hi, q)
            return (lo + hi) / 2

        ask, bid = np.clip(solve("ask"), TICK, 1 - TICK), np.clip(solve("bid"), TICK, 1 - TICK)
        gap = ask - bid < TICK
        c = np.clip((ask + bid) / 2, TICK, 1 - TICK)
        ask = np.where(gap, np.minimum(c + TICK / 2, 1 - TICK / 2), ask)
        bid = np.where(gap, np.maximum(c - TICK / 2, TICK / 2), bid)
        return ask, bid

    def slot(self, D, D_panel, addon, fee, subsidy, tau, count=True):
        """One trading slot: quotes, an arrival, a trade, and the market maker's update."""
        p, n, rng = self.p, self.n, self.rng
        ask, bid = self.quotes(D, D_panel, addon, fee, subsidy)
        L = self.likelihoods(ask, bid, D, D_panel, fee)
        u = rng.random(n)
        c1 = p.informed_rate
        c2 = c1 + p.noise_rate
        c3 = c2 + p.extra_noise_rate
        c4 = c3 + p.panel_rate
        S = 2 * self.K * self.sy + 2 * np.sqrt(self.K) * rng.standard_normal(n)
        belief = self.F0 + self.Fd * expit(self.l_pub + S)       # value of the contract to the trader
        coin = rng.random(n) < 0.5
        inf_buy = D * belief > ask + fee
        inf_sell = D * (1 - belief) > (1 - bid) + fee
        pan_buy, pan_sell = D_panel * belief > ask, D_panel * (1 - belief) > (1 - bid)
        is_inf, is_noise = u < c1, (u >= c1) & (u < c2)
        is_extra, is_panel = (u >= c2) & (u < c3), (u >= c3) & (u < c4)
        buy = (is_inf & inf_buy) | ((is_noise | is_extra) & coin) | (is_panel & pan_buy)
        sell = (is_inf & inf_sell & ~inf_buy) | ((is_noise | is_extra) & ~coin) | (is_panel & pan_sell & ~pan_buy)
        none1 = 1 - L[1][0] - L[1][1] if p.learn_from_no_trade else np.ones(n)
        none0 = 1 - L[0][0] - L[0][1] if p.learn_from_no_trade else np.ones(n)
        p1 = np.where(buy, L[1][0], np.where(sell, L[1][1], none1))
        p0 = np.where(buy, L[0][0], np.where(sell, L[0][1], none0))
        self.l_mm += np.log(np.clip(p1, 1e-300, None) / np.clip(p0, 1e-300, None))
        traded = buy | sell
        if count:
            self.trades_today += traded
            self.cost += p.mm_subsidy * traded + p.interest_subsidy * tau * traded
            self.cost += np.where(is_extra & buy, ask - self.y, 0) + np.where(is_extra & sell, self.y - bid, 0)
            self.cost += (is_panel & (pan_buy | pan_sell)) * (p.fee + p.informed_discount * tau)

    def news(self, k, rng=None):
        """Public news worth k units, seen by everyone."""
        llr = 2 * k * self.sy + 2 * np.sqrt(k) * (rng or self.rng).standard_normal(self.n)
        self.l_pub += llr
        self.l_mm += llr

    def effort(self, ask, bid, D, fee, days_left):
        """Representative informed trader's research decision (extension): buy effort_info more units of
        lasting private information if the expected gain in trading profit, per trade at today's quotes
        times the trader's expected trades until resolution, exceeds effort_cost."""
        p = self.p
        if not (p.effort_cost and p.effort_info):
            return
        nodes, w = np.polynomial.hermite_e.hermegauss(20)
        w = w / w.sum()
        prior = expit(self.l_mm)

        def value(K):
            v = 0
            for y, sy, py in ((1, 1.0, prior), (0, -1.0, 1 - prior)):
                S = 2 * K[:, None] * sy + 2 * np.sqrt(K)[:, None] * nodes[None, :]
                b = expit(self.l_pub[:, None] + S)
                gain = np.maximum(0, np.maximum(D * b - ask[:, None] - fee, D * (1 - b) - (1 - bid[:, None]) - fee))
                v = v + py * (gain * w).sum(axis=1)
            return v

        arrivals = p.slots * p.informed_rate / p.informed_pool * days_left
        do = (value(self.K + p.effort_info) - value(self.K)) * arrivals > p.effort_cost
        self.K = self.K + do * p.effort_info


def simulate(p, n=2000, seed=0):
    """Run n markets. Returns per-day arrays (by days to close) of mean Brier of the mid price, mean
    spread and share of markets with a trade; the mean policy cost per market; and per-market Brier
    (averaged over the market's life, and at 180, 90 and 30 days to close) for paired comparisons."""
    rng = np.random.default_rng(seed)
    m = Market(p, n, rng)
    # the forecast contract has its own random draws, so the main market's draws match the baseline;
    # it shares the outcome, the information state and the market maker's belief with the main market
    fc = Market(p, n, np.random.default_rng(seed + 1)) if p.forecast_day >= 0 else None
    if fc is not None:
        fc.l0, fc.y, fc.sy = m.l0, m.y, m.sy
    kday = info_profile(p)
    pub, priv = p.public_share * kday, (1 - p.public_share) * kday
    nodes, wts = np.polynomial.hermite_e.hermegauss(20)
    wts = wts / wts.sum()
    out = {"brier": np.zeros(p.T), "spread": np.zeros(p.T), "traded": np.zeros(p.T)}
    sq = np.zeros((p.T, n))
    for t in range(p.T):
        tau = (p.T - t) / 365
        m.news(pub[t])
        m.K = m.K + priv[t]
        if fc is not None and t == p.forecast_day:
            m.news(p.forecast_info, fc.rng)      # the panel's research becomes public with its forecast
        if fc is not None and t < p.forecast_day:
            # F = sigmoid(public log-odds on forecast_day + research); X = what is added from now on
            V = pub[t + 1: p.forecast_day + 1].sum() + p.forecast_info
            Fy = [(expit(m.l_pub[:, None] + 2 * V * sy + 2 * np.sqrt(V) * nodes[None, :]) * wts).sum(axis=1) for sy in (-1.0, 1.0)]
            fc.F0, fc.Fd = Fy[0], np.maximum(Fy[1] - Fy[0], 1e-9)
        r_inf = max(p.informed_discount - p.interest_subsidy, 0)
        r_mm = max(p.mm_discount - p.interest_subsidy, 0)
        D, D_panel = np.exp(-r_inf * tau), 1.0      # panel traders do not discount
        addon = p.mm_capital * (1 - np.exp(-r_mm * tau))
        ask, bid = m.quotes(D, D_panel, addon, p.fee, p.mm_subsidy)
        m.effort(ask, bid, D, p.fee, p.T - t)
        m.trades_today[:] = 0
        for _ in range(p.slots):
            m.slot(D, D_panel, addon, p.fee, p.mm_subsidy, tau)
            if fc is not None and t < p.forecast_day:
                tau_f = (p.forecast_day - t) / 365
                fc.l_pub, fc.l_mm, fc.K = m.l_pub, m.l_mm, m.K
                fc.slot(np.exp(-r_inf * tau_f), 1.0, p.mm_capital * (1 - np.exp(-r_mm * tau_f)), p.fee, 0.0, tau_f, count=False)
                m.l_mm = fc.l_mm
        ask, bid = m.quotes(D, D_panel, addon, p.fee, p.mm_subsidy)
        mid = (ask + bid) / 2
        sq[t] = (mid - m.y) ** 2
        out["brier"][t] = sq[t].mean()
        out["spread"][t] = np.mean(ask - bid)
        out["traded"][t] = np.mean(m.trades_today > 0)
    out["cost"] = float(m.cost.mean() + (p.forecast_cost if fc is not None else 0.0))
    out["market_brier"] = {"life": sq.mean(axis=0), 180: sq[p.T - 180], 90: sq[p.T - 90], 30: sq[p.T - 30]}
    out["days_to_close"] = p.T - np.arange(p.T)
    return out
