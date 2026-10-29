"""Agent-based simulation of a Kalshi-style yes/no market, for comparing policies.

One contract pays $1 if the event happens. Time runs in days until resolution; each day has a
number of trading slots. Many markets are simulated at once (vectorised over markets).

Information. The outcome Y is drawn at the start from the prior. Information arrives as signals
whose log-likelihood ratio for Y, given Y, is normal with mean +-2k and variance 4k ("k units").
Each day brings public news (seen by everyone) and private signals (each informed trader gets
their own). info_total is the total units over the market's life; public_share splits it between
public and private; info_shape sets the timing (0 = evenly over time, larger = concentrated near
resolution). overlap is the share of the private information that all informed traders have in
common; the rest is drawn afresh for each arriving trader (overlap = 0: all of it is fresh).

Traders. In each slot, an informed trader arrives with probability informed_rate and a noise trader
with probability noise_rate. Noise traders buy or sell at random. An informed trader's belief is
the public information plus their own private signals; they buy if the payoff they expect,
discounted to resolution at their discount rate, beats the ask plus a fee, and sell (buy "no") in
the mirror case. Traders do not learn from prices or trade history. Extension: each day informed
traders can pay effort_cost to get effort_info more units of private information of their own,
which they keep; they do so when the expected gain in trading profit until resolution is larger.

Entry (extension; off when entry_elasticity = 0). Potential informed traders arrive with
probability entry_pool per slot and enter when the expected trading surplus of entering exceeds
a recurring attention cost, drawn for each opportunity from a power distribution on (0, entry_cost]:
P(cost < x) = (x / entry_cost) ** entry_elasticity, so the elasticity of entry with respect to the
surplus is entry_elasticity wherever the surplus is positive and below entry_cost (all potential
traders enter above it). The surplus is judged before the private signal is seen, with the public
information, and net of the value of trading without the signal. Entry and quotes are solved
together in every slot. Informed traders' realized trading profit (at the true outcome) is recorded
next to the profit they expect.
entry_start sets where that search starts (a check: last slot's rate, no entry, or the whole pool).

Market maker. A competitive market maker knows the setup, including the entry rule (but not who is
informed), and sets the ask and bid at its expected value of the contract after a buy or a sell
(Glosten-Milgrom), plus an add-on for the capital it must lock up until resolution. It updates its
belief from public news and from trades (learn_from_no_trade=True also lets it learn from slots
without a trade). With overlap > 0 it also tracks its belief about the shared private information
(normal given each outcome, updated after each trade by matching moments), so trades driven by the
same information are not treated as independent evidence. Quotes are in [0.005, 0.995] with a
1 cent minimum spread.

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
from scipy.special import expit, log_ndtr, logit, ndtr

PRIOR_SD = 1.0          # spread of markets' starting log-odds across markets
TICK = 0.01
BISECT = 22             # bisection steps for the quotes
ENTRY_TOL = 1e-6        # entry rate: largest allowed gap between the rate used for quotes and the
ENTRY_ITERS = 60        # rate those quotes imply, and the most iterations to close it
ENTRY_FAST = 10         # secant steps before switching to bisection


@dataclass(frozen=True)
class Params:
    T: int = 365
    slots: int = 4
    info_total: float = 2.6
    public_share: float = 0.6
    info_shape: float = 0.5
    overlap: float = 0.0
    informed_rate: float = 0.012
    noise_rate: float = 0.06
    informed_discount: float = 0.15
    fee: float = 0.01
    effort_cost: float = 0.0
    effort_info: float = 0.0
    informed_pool: int = 20
    entry_elasticity: float = 0.0
    entry_pool: float = 0.024
    entry_cost: float = 0.0
    entry_start: str = "warm"       # starting entry rate in each slot: warm (last slot's), zero, pool
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


def _thresholds(ask, bid, l_pub, D, fee, F0=0.0, Fd=1.0):
    """Private log-odds above which an informed trader buys, and below which they sell, for a contract
    worth F0 + Fd * P(Y = 1) at settlement (F0 = 0, Fd = 1 for the main contract)."""
    pb = ((ask + fee) / D - F0) / Fd
    xb = np.where(pb >= 1, np.inf, np.where(pb <= 0, -np.inf, logit(np.clip(pb, 1e-12, 1 - 1e-12)))) - l_pub
    ps = (1 - F0 - (1 - bid + fee) / D) / Fd
    xs = np.where(ps >= 1, np.inf, np.where(ps <= 0, -np.inf, logit(np.clip(ps, 1e-12, 1 - 1e-12)))) - l_pub
    return xb, xs


def _entry_share(net, p):
    """Share of potential informed traders whose attention cost is below the surplus net."""
    return np.minimum(np.maximum(net, 0) / p.entry_cost, 1) ** p.entry_elasticity


def _entry_spend(net, p):
    """Expected attention cost paid per potential trader: E[cost; cost < net]."""
    m = np.minimum(np.maximum(net, 0), p.entry_cost)
    return p.entry_elasticity / (p.entry_elasticity + 1) * m * (m / p.entry_cost) ** p.entry_elasticity


class Market:
    """State of n markets and the slot mechanics; see the module docstring."""

    def __init__(self, p, n, rng):
        self.p, self.n, self.rng = p, n, rng
        self.l0 = rng.normal(0, PRIOR_SD, n)
        self.y = (rng.random(n) < expit(self.l0)).astype(float)
        self.sy = 2 * self.y - 1
        self.l_pub = self.l0.copy()
        self.l_mm = self.l0.copy()
        # private information: Hc units shared by all informed traders (true deviation from its mean
        # given Y: dev), He units of each trader's own; the market maker's belief about dev given
        # Y = y is N(mD[y], vD[y])
        self.Hc, self.He = 0.0, np.full(n, 1e-9)
        self.dev = np.zeros(n)
        self.mD, self.vD = np.zeros((2, n)), np.zeros((2, n))
        self.alpha = np.full(n, p.informed_rate if not p.entry_elasticity else p.entry_pool / 2)
        self.cost = np.zeros(n)
        self.trades_today = np.zeros(n)
        self.F0, self.Fd = 0.0, 1.0       # settlement value = F0 + Fd * P(Y = 1)
        self.gross = self.net = np.zeros(n)
        self.stats = {k: np.zeros(n) for k in ["informed_arrivals", "informed_trades", "noise_trades", "expected_profit",
                                                "realized_profit", "entry_spend", "research_spend", "spread", "days_traded"]}
        self.iters, self.max_gap, self.max_rate = [], 0.0, 0.0

    def add_private(self, k):
        """k more units of private information: overlap of it shared, the rest each trader's own."""
        w = self.p.overlap
        self.He = self.He + (1 - w) * k
        if w:
            self.Hc += w * k
            self.vD += 4 * w * k
            self.dev = self.dev + 2 * np.sqrt(w * k) * self.rng.standard_normal(self.n)

    def _side(self, x, sign, y, moments=False):
        """P(an informed trader's private log-odds S is above x (sign +1) or below x (sign -1) | Y = y),
        averaged over the market maker's belief about the shared information; with moments, also the
        mean and variance of that belief given that it happened."""
        sy = 2 * y - 1
        m, v = self.mD[y], self.vD[y]
        c = np.sqrt(v + 4 * self.He)
        u = sign * (m + 2 * (self.Hc + self.He) * sy - x) / c
        Z = ndtr(u)
        if not moments:
            return Z
        uc = np.clip(u, -38, 38)
        r = np.exp(-uc ** 2 / 2 - 0.5 * np.log(2 * np.pi) - log_ndtr(uc))
        return Z, m + sign * v * r / c, v - v ** 2 * r * (uc + r) / c ** 2

    def _terms(self, ask, bid, D, D_panel, fee):
        """Informed and panel buy/sell terms (weight, threshold, sign) and noise probability per side."""
        p = self.p
        xb, xs = _thresholds(ask, bid, self.l_pub, D, fee, self.F0, self.Fd)
        buy, sell = [(self.alpha, xb, 1)], [(self.alpha, xs, -1)]
        if p.panel_rate:
            pxb, pxs = _thresholds(ask, bid, self.l_pub, D_panel, 0.0, self.F0, self.Fd)
            buy.append((p.panel_rate, pxb, 1))
            sell.append((p.panel_rate, pxs, -1))
        return buy, sell, (p.noise_rate + p.extra_noise_rate) / 2

    def likelihoods(self, ask, bid, D, D_panel, fee):
        """P(buy | Y), P(sell | Y) for Y = 1 and 0 at the given quotes."""
        buy, sell, a = self._terms(ask, bid, D, D_panel, fee)
        return {y: (a + sum(w * self._side(x, s, y) for w, x, s in buy),
                    a + sum(w * self._side(x, s, y) for w, x, s in sell)) for y in (1, 0)}

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

    def surplus(self, ask, bid, D, fee, H=None):
        """Expected trading surplus of an informed trader at these quotes, before seeing the private
        signal (H units; S | Y ~ N(2H(2Y-1), 4H)) and judged with the public information: gross, and
        net of the value of trading without the signal. Exact: E[P(Y=1 | S); S > x] = P(Y=1, S > x)."""
        H = self.Hc + self.He if H is None else H
        q = expit(self.l_pub)
        xb, xs = _thresholds(ask, bid, self.l_pub, D, fee, self.F0, self.Fd)
        sd = 2 * np.sqrt(H)
        b1, b0 = ndtr((2 * H - xb) / sd), ndtr((-2 * H - xb) / sd)       # P(S > xb | Y)
        s1, s0 = ndtr((xs - 2 * H) / sd), ndtr((xs + 2 * H) / sd)        # P(S < xs | Y)
        pb, ps = q * b1 + (1 - q) * b0, q * s1 + (1 - q) * s0
        gross = (D * (self.F0 * pb + self.Fd * q * b1) - (ask + fee) * pb
                 + D * ((1 - self.F0) * ps - self.Fd * q * s1) - (1 - bid + fee) * ps)
        v = self.F0 + self.Fd * q
        plain = np.maximum(0, np.maximum(D * v - ask - fee, D * (1 - v) - (1 - bid) - fee))
        return gross, np.maximum(gross - plain, 0)

    def equilibrium(self, D, D_panel, addon, fee, subsidy):
        """Quotes, with the informed entry rate solved jointly when entry responds to profits: the rate
        alpha behind the quotes must equal entry_pool x G(surplus at those quotes). The implied rate
        minus alpha is non-negative at alpha = 0 and negative at alpha = entry_pool, so a consistent rate
        exists; it is found within that bracket by secant steps, then bisection."""
        p = self.p
        if not p.entry_elasticity:
            ask, bid = self.quotes(D, D_panel, addon, fee, subsidy)
            self.gross, self.net = self.surplus(ask, bid, D, fee)
            return ask, bid

        def gap(a):
            self.alpha = a
            ask, bid = self.quotes(D, D_panel, addon, fee, subsidy)
            gross, net = self.surplus(ask, bid, D, fee)
            return p.entry_pool * _entry_share(net, p) - a, (ask, bid, gross, net)

        a = {"warm": self.alpha, "zero": np.zeros(self.n), "pool": np.full(self.n, p.entry_pool)}[p.entry_start]
        lo, hi = np.zeros(self.n), np.full(self.n, p.entry_pool)
        g, res = gap(a)
        a_prev = g_prev = None
        for it in range(ENTRY_ITERS):
            if np.abs(g).max() < ENTRY_TOL:
                break
            lo, hi = np.where(g > 0, a, lo), np.where(g < 0, a, hi)
            step = a + 0.5 * g
            if a_prev is not None:
                slope = (g - g_prev) / np.where(a != a_prev, a - a_prev, np.nan)
                step = np.where((slope < 0) & np.isfinite(slope), a - g / np.where(slope < 0, slope, -1), step)
            step = np.where((step > lo) & (step < hi) & (it < ENTRY_FAST), step, (lo + hi) / 2)
            a_prev, g_prev = a, g
            a = np.where(np.abs(g) < ENTRY_TOL, a, step)
            g, res = gap(a)
        self.iters.append(it + 1)
        self.max_gap = max(self.max_gap, float(np.abs(g).max()))
        self.alpha = a
        ask, bid, self.gross, self.net = res
        return ask, bid

    def _update_shared(self, obs, ask, bid, D, D_panel, fee):
        """Bayes' rule for the market maker after a slot's outcome obs (0 buy, 1 sell, 2 nothing): the
        likelihood of obs given Y = y, and, with overlap, the updated belief about the shared
        information (a mixture of normals reduced to one normal with the same mean and variance)."""
        buy, sell, a = self._terms(ask, bid, D, D_panel, fee)
        none = [(-w, x, s) for w, x, s in buy + sell]
        cases = [(a, buy), (a, sell), (1 - 2 * a, none)]
        like = {}
        for y in (0, 1):
            m, v = self.mD[y], self.vD[y]
            Zs, M1, M2 = [], [], []
            for base, terms in cases:
                Z, s1, s2 = base + 0 * m, base * m, base * (v + m * m)
                for w, x, s in terms:
                    if self.p.overlap:
                        z, mu, va = self._side(x, s, y, moments=True)
                        s1, s2 = s1 + w * z * mu, s2 + w * z * (va + mu * mu)
                    else:
                        z = self._side(x, s, y)
                    Z = Z + w * z
                Zs.append(Z), M1.append(s1), M2.append(s2)
            like[y] = np.choose(obs, Zs)
            if self.p.overlap:
                Z = np.maximum(like[y], 1e-300)
                mean = np.choose(obs, M1) / Z
                var = np.maximum(np.choose(obs, M2) / Z - mean ** 2, 1e-12)
                keep = (obs == 2) & (not self.p.learn_from_no_trade)
                self.mD[y], self.vD[y] = np.where(keep, m, mean), np.where(keep, v, var)
        return like[1], like[0]

    def slot(self, D, D_panel, addon, fee, subsidy, tau, count=True, quotes=None):
        """One trading slot: quotes, an arrival, a trade, and the market maker's update."""
        p, n, rng = self.p, self.n, self.rng
        ask, bid = quotes if quotes is not None else self.equilibrium(D, D_panel, addon, fee, subsidy)
        u = rng.random(n)
        c1 = self.alpha
        c2 = c1 + p.noise_rate
        c3 = c2 + p.extra_noise_rate
        c4 = c3 + p.panel_rate
        self.max_rate = max(self.max_rate, float(c4.max()))
        S = 2 * (self.Hc + self.He) * self.sy + self.dev + 2 * np.sqrt(self.He) * rng.standard_normal(n)
        belief = self.F0 + self.Fd * expit(self.l_pub + S)       # value of the contract to the trader
        coin = rng.random(n) < 0.5
        inf_buy = D * belief > ask + fee
        inf_sell = D * (1 - belief) > (1 - bid) + fee
        pan_buy, pan_sell = D_panel * belief > ask, D_panel * (1 - belief) > (1 - bid)
        is_inf, is_noise = u < c1, (u >= c1) & (u < c2)
        is_extra, is_panel = (u >= c2) & (u < c3), (u >= c3) & (u < c4)
        buy = (is_inf & inf_buy) | ((is_noise | is_extra) & coin) | (is_panel & pan_buy)
        sell = (is_inf & inf_sell & ~inf_buy) | ((is_noise | is_extra) & ~coin) | (is_panel & pan_sell & ~pan_buy)
        if p.learn_from_no_trade or p.overlap:
            obs = np.where(buy, 0, np.where(sell, 1, 2))
            p1, p0 = self._update_shared(obs, ask, bid, D, D_panel, fee)
            if not p.learn_from_no_trade:
                p1, p0 = np.where(obs == 2, 1.0, p1), np.where(obs == 2, 1.0, p0)
        else:
            L = self.likelihoods(ask, bid, D, D_panel, fee)
            p1 = np.where(buy, L[1][0], np.where(sell, L[1][1], 1.0))
            p0 = np.where(buy, L[0][0], np.where(sell, L[0][1], 1.0))
        self.l_mm += np.log(np.clip(p1, 1e-300, None) / np.clip(p0, 1e-300, None))
        traded = buy | sell
        if count:
            self.trades_today += traded
            self.cost += p.mm_subsidy * traded + p.interest_subsidy * tau * traded
            self.cost += np.where(is_extra & buy, ask - self.y, 0) + np.where(is_extra & sell, self.y - bid, 0)
            self.cost += (is_panel & (pan_buy | pan_sell)) * (p.fee + p.informed_discount * tau)
            st = self.stats
            st["informed_arrivals"] += is_inf
            st["informed_trades"] += is_inf & (inf_buy | inf_sell)
            st["noise_trades"] += is_noise | is_extra
            st["expected_profit"] += self.alpha * self.gross
            v = self.F0 + self.Fd * self.y
            st["realized_profit"] += np.where(is_inf & inf_buy, D * v - ask - fee, 0) + np.where(is_inf & inf_sell & ~inf_buy, D * (1 - v) - (1 - bid) - fee, 0)
            if p.entry_elasticity:
                st["entry_spend"] += p.entry_pool * _entry_spend(self.net, p)

    def news(self, k, rng=None):
        """Public news worth k units, seen by everyone."""
        llr = 2 * k * self.sy + 2 * np.sqrt(k) * (rng or self.rng).standard_normal(self.n)
        self.l_pub += llr
        self.l_mm += llr

    def effort(self, ask, bid, D, fee, days_left):
        """Representative informed trader's research decision (extension): buy effort_info more units of
        lasting private information if the expected gain in trading profit, per trade at today's quotes
        (judged with the public information) times the trader's expected trades until resolution,
        exceeds effort_cost."""
        p = self.p
        if not (p.effort_cost and p.effort_info):
            return
        H = self.Hc + self.He
        gain = self.surplus(ask, bid, D, fee, H + p.effort_info)[0] - self.surplus(ask, bid, D, fee, H)[0]
        arrivals = p.slots * self.alpha / p.informed_pool * days_left
        do = gain * arrivals > p.effort_cost
        self.He = self.He + do * p.effort_info
        self.stats["research_spend"] += do * p.effort_cost * p.informed_pool


def simulate(p, n=2000, seed=0):
    """Run n markets. Returns per-day arrays (by days to close) of mean Brier of the mid price, mean
    spread, share of markets with a trade and mean informed entry rate; the mean policy cost per
    market; per-market Brier (averaged over the market's life, and at 180, 90 and 30 days to close)
    and per-market activity totals for paired comparisons; and checks of the entry solution."""
    if p.overlap and p.forecast_day >= 0:
        raise NotImplementedError("the forecast contract is not set up for overlapping information")
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
    out = {k: np.zeros(p.T) for k in ["brier", "spread", "traded", "alpha"]}
    sq, nets = np.zeros((p.T, n)), np.zeros((p.T, n))
    for t in range(p.T):
        tau = (p.T - t) / 365
        m.news(pub[t])
        m.add_private(priv[t])
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
        ask, bid = m.equilibrium(D, D_panel, addon, p.fee, p.mm_subsidy)
        nets[t] = m.net
        m.effort(ask, bid, D, p.fee, p.T - t)
        m.trades_today[:] = 0
        for i in range(p.slots):
            m.slot(D, D_panel, addon, p.fee, p.mm_subsidy, tau, quotes=(ask, bid) if i == 0 and not m.p.effort_cost else None)
            out["alpha"][t] += m.alpha.mean() / p.slots
            if fc is not None and t < p.forecast_day:
                tau_f = (p.forecast_day - t) / 365
                fc.l_pub, fc.l_mm, fc.Hc, fc.He, fc.alpha = m.l_pub, m.l_mm, m.Hc, m.He, m.alpha
                fc.slot(np.exp(-r_inf * tau_f), 1.0, p.mm_capital * (1 - np.exp(-r_mm * tau_f)), p.fee, 0.0, tau_f,
                        count=False, quotes=fc.quotes(np.exp(-r_inf * tau_f), 1.0, p.mm_capital * (1 - np.exp(-r_mm * tau_f)), p.fee, 0.0))
                m.l_mm = fc.l_mm
        ask, bid = m.equilibrium(D, D_panel, addon, p.fee, p.mm_subsidy)
        mid = (ask + bid) / 2
        sq[t] = (mid - m.y) ** 2
        out["brier"][t] = sq[t].mean()
        out["spread"][t] = np.mean(ask - bid)
        out["traded"][t] = np.mean(m.trades_today > 0)
        m.stats["spread"] += (ask - bid) / p.T
        m.stats["days_traded"] += (m.trades_today > 0) / p.T
    out["cost"] = float(m.cost.mean() + (p.forecast_cost if fc is not None else 0.0))
    out["market_brier"] = {"life": sq.mean(axis=0), 180: sq[p.T - 180], 90: sq[p.T - 90], 30: sq[p.T - 30]}
    out["market_stats"] = m.stats
    out["days_to_close"] = p.T - np.arange(p.T)
    pos = nets[nets > 0]
    out["checks"] = {"net_q99": float(np.quantile(pos, 0.99)) if pos.size else 0.0, "net_positive": float((nets > 0).mean()),
                     "alpha_mean": float(out["alpha"].mean()), "entry_iters": float(np.mean(m.iters)) if m.iters else 0.0,
                     "entry_iters_max": int(max(m.iters)) if m.iters else 0, "entry_gap_max": m.max_gap,
                     "arrival_prob_max": m.max_rate}
    return out
