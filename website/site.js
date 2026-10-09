const $ = (s, r = document) => r.querySelector(s);
const h = (tag, attrs = {}, ...kids) => { const e = document.createElement(tag); for (const k in attrs) { if (attrs[k] == null || attrs[k] === false) continue; if (k === 'class') e.className = attrs[k]; else if (k.startsWith('on')) e.addEventListener(k.slice(2), attrs[k]); else e.setAttribute(k, attrs[k]); } for (const k of kids.flat()) if (k != null) e.appendChild(typeof k === 'string' || typeof k === 'number' ? document.createTextNode(k) : k); return e; };
const fi = v => v == null ? '–' : Math.round(v).toLocaleString();
const f2 = v => v == null ? '–' : (+v).toFixed(2), f3 = v => v == null ? '–' : (+v).toFixed(3);
const pct = (v, d = 0) => v == null ? '–' : (v * 100).toFixed(d) + '%';
const cents = v => v == null ? '–' : (v * 100).toFixed(1).replace(/\.0$/, '') + '¢';
const usd = v => v == null ? '–' : v >= 1e6 ? '$' + (v / 1e6).toFixed(1) + 'M' : v >= 1e3 ? '$' + (v / 1e3).toFixed(0) + 'K' : '$' + (+v).toFixed(v < 10 ? 2 : 0);
const big = v => v == null ? '–' : v >= 1e9 ? (v / 1e9).toFixed(1) + 'B' : v >= 1e6 ? (v / 1e6).toFixed(1) + 'M' : v >= 1e3 ? (v / 1e3).toFixed(0) + 'K' : (+v).toFixed(0);
// two-sided normal p-value from a t statistic (erfc approximation)
const pval = t => { const z = Math.abs(t) / Math.SQRT2, k = 1 / (1 + 0.3275911 * z); return k * (0.254829592 + k * (-0.284496736 + k * (1.421413741 + k * (-1.453152027 + k * 1.061405429)))) * Math.exp(-z * z); };
const stars = p => p < 0.001 ? '***' : p < 0.01 ? '**' : p < 0.05 ? '*' : '';
let S, S_ALL;
// which platform the pages show; remembered per viewer when storage is available
let PLAT = (() => { try { return localStorage.getItem('plat') || 'kalshi'; } catch (e) { return 'kalshi'; } })();
const isPM = () => PLAT === 'polymarket' && !!(S_ALL && S_ALL.pm);
const PNAME = () => isPM() ? 'Polymarket' : 'Kalshi';
const tex = (src, display = false) => { const e = h(display ? 'div' : 'span'); if (window.katex) katex.render(src, e, { displayMode: display, throwOnError: false }); else e.textContent = src; return e; };
const SHORT = { '<1d': '< 1d', '1-7d': '1–7d', '7-30d': '1–4w', '1-3m': '1–3m', '3-6m': '3–6m', '6-12m': '6–12m', '1-2y': '1–2y', '>2y': '> 2y' };

function infoIcon(text) { const i = h('span', { class: 'info', tabindex: '0', 'aria-label': Array.isArray(text) ? text.join('. ') : text }); i.textContent = 'i'; const show = () => { const d = document.createElement('div'); if (Array.isArray(text)) { const ul = document.createElement('ul'); ul.className = 'tipul'; text.forEach(t => { const li = document.createElement('li'); li.textContent = t; ul.appendChild(li); }); d.appendChild(ul); } else d.textContent = text; d.style.maxWidth = '340px'; const b = i.getBoundingClientRect(); C.showTip({ clientX: b.right, clientY: b.bottom }, d); }; i.addEventListener('pointerenter', show); i.addEventListener('focus', show); i.addEventListener('pointerleave', C.hideTip); i.addEventListener('blur', C.hideTip); return i; }
const card = (title, sub, how, cls = 'card') => h('div', { class: cls }, h('h3', {}, title, how ? infoIcon(how) : null), sub ? h('div', { class: 'sub' }, sub) : null);
function pageHead(main, title, lead) { main.append(h('h2', { class: 'pagetitle' }, title), h('p', { class: 'lead' }, lead)); }
function sectionHead(main, title, desc) { main.append(h('div', { class: 'section' }, h('h3', {}, title), desc ? h('p', {}, desc) : null)); }
function tile(v, l, s) { return h('div', { class: 'tile' }, h('div', { class: 'v' }, v), h('div', { class: 'l' }, l), s ? h('div', { class: 's' }, s) : null); }
function simpleTable(cols, rows) { return h('div', { class: 'tablewrap' }, h('table', {}, h('thead', {}, h('tr', {}, cols.map(c => h('th', { class: c.num ? 'num' : '' }, c.label, c.tip ? infoIcon(c.tip) : null)))), h('tbody', {}, rows.map(r => h('tr', {}, cols.map(c => h('td', { class: (c.num ? 'num ' : '') + (c.cls ? c.cls(r) : '') }, c.render ? c.render(r) : r[c.key] ?? '–'))))))); }
const grid = (...cards) => h('div', { class: 'grid' }, ...cards);

// ------------------------------------------------------------------ Overview
function pageOverview(main) {
  const PM = isPM();
  pageHead(main, `${PNAME()} long-horizon markets`, 'What each tab shows. The switch at the top right changes the platform.');
  const tabs = [
    ['horizons', 'Horizons', `Which markets exist, by how ${PM ? 'long they were open' : 'far ahead of their close they were listed'}, how many long markets are usable, and when long markets trade before resolving.`],
    ['accuracy', 'Accuracy', 'How accurate prices are at different distances from resolution: Brier score, calibration, accuracy by liquidity, and returns from buying favourites early.'],
    ['regressions', 'Regression', `Whether days with more past trading have more accurate prices, in five specifications, by category${PM ? ' and by year the market closed' : ''}.`],
    ['tail', 'Last days', 'Whether the outcome is already known before a market closes, and how much of the data comes from those days.'],
    ['rewards', 'Rewards', PM ? 'What can and can’t be seen about Polymarket’s reward programs.' : 'The programs Kalshi pays for liquidity and trading, which markets get them, and whether rewards make markets easier to trade and more accurate (with a comparison against similar unrewarded markets).'],
    ['coverage', 'What we have', 'The data available, in plain terms, and what is missing.'],
    ['data', 'Data', 'Dataset sizes and the sample behind each analysis.'],
    ['notes', 'Notes', 'How the regression works: assumptions, fixed effects, and what to be careful of.'],
  ];
  main.append(h('ul', { class: 'findings' }, tabs.map(([href, name, text]) => h('li', {}, h('a', { href: '#/' + href }, h('b', {}, name)), ' — ' + text))));
  main.append(h('p', { class: 'muted small', style: 'margin-top:14px' }, PM
    ? `Polymarket: resolved yes/no markets open at least a day that started from 30 Sep 2023; data to ${S.inventory.price_last}. Sports and crypto markets are left out.`
    : 'Kalshi: markets still open on 14 Jul 2026 or later (plus about 4,000 that closed earlier in 2026); combo (parlay) markets excluded; data to 21 Sep 2026. Sports and crypto markets are left out.'));
}

// ------------------------------------------------------------------ Horizons
function pageHorizons(main) {
  pageHead(main, 'Which markets exist, by horizon', isPM() ? 'Every Polymarket market except sports and crypto, grouped by how long it was open (start to close).' : 'Every non-combo market except sports and crypto, grouped by how far ahead of its close it was listed.');
  const H = S.horizon, T = Object.fromEntries(S.trades_hz.map(r => [r.hz, r])), PM = isPM(), unit = PM ? 'shares' : 'contracts';
  const c3 = card('By horizon', null, null, 'card wide'); main.append(h('div', { class: 'grid' }, c3));
  c3.append(simpleTable([
    { key: 'label', label: PM ? 'Open for' : 'Listed ahead' },
    { key: 'markets', label: 'Markets', num: true, render: r => fi(r.markets) },
    { key: 'resolved_share', label: PM ? 'Resolved yes/no' : 'Resolved', num: true, render: r => pct(r.resolved_share) },
    { key: 'vol_share', label: `Share of ${unit}`, num: true, render: r => pct(r.vol_share, 1) },
    { key: 'med_vol_traded', label: `${PM ? 'Shares' : 'Contracts'} per traded market (median)`, num: true, render: r => fi(r.med_vol_traded) },
    { key: 'size', label: 'Average trade size', num: true, render: r => fi(T[r.hz].mean_trade_size) }], H));

  const F = S.funnel;
  const c4 = card(PM ? 'How many long markets are usable' : 'Why so few long markets have resolved', PM ? 'Markets open 3+ months, narrowed down to those resolved yes/no that traded and have a price history.' : 'Markets listed 3+ months ahead, narrowed down to those settled that traded and have a price history. Long markets that ended before 2026 are not in Kalshi’s data at all.', null, 'card wide');
  c4.append(simpleTable([{ key: 0, label: 'Step' }, { key: 1, label: 'Markets', num: true }, { key: 2, label: 'Why' }], PM ? [
    ['Open 3+ months', fi(F.listed_90d), 'All long markets in our data'],
    ['− Sports and crypto', fi(F.excluded), 'Left out of the analyses'],
    ['− Still open', fi(F.open), 'They haven’t ended yet'],
    ['− Closed without a yes/no result', fi(F.other_status), 'Markets with more than two outcomes, or no clear 0/1 result'],
    [h('b', {}, 'Resolved yes/no'), h('b', {}, fi(F.settled)), 'Ended 2023 – 2026'],
    ['− Never traded', fi(F.never_traded), 'No volume to split across time'],
    ['− No price history', fi(F.no_bars), 'Polymarket returned no daily prices'],
    [h('b', {}, 'Usable long markets'), h('b', {}, fi(F.used)), ''],
  ] : [
    ['Listed 3+ months before close', fi(F.listed_90d), 'All long markets in our data'],
    ['− Sports and crypto', fi(F.excluded), 'Left out of the analyses'],
    ['− Still open', fi(F.open), 'They close later in 2026 or in 2027+, so they haven’t ended'],
    ['− Other statuses', fi(F.other_status), 'Closed but not yet settled, paused, or not yet open'],
    [h('b', {}, 'Already settled'), h('b', {}, fi(F.settled)), 'Ended between Jan and 21 Sep 2026'],
    ['− Never traded', fi(F.never_traded), 'No volume to split across time'],
    ['− No price history', fi(F.no_bars), 'Kalshi returned no hourly bars'],
    [h('b', {}, 'Usable long markets'), h('b', {}, fi(F.used)), ''],
  ]));
  main.append(h('div', { class: 'grid', style: 'margin-top:16px' }, c4));

  const V = S.vol_to_close || [];
  const WIN = ['>365d', '180-365d', '90-180d', '30-90d', '7-30d', '1-7d', '0-1d'];
  const VLAB = { '>365d': '> 1y', '180-365d': '6–12m', '90-180d': '3–6m', '30-90d': '1–3m', '7-30d': '1–4w', '1-7d': '1–7d', '0-1d': 'final day' };
  const GRP = [['3-6m', 'open 3–6 months'], ['6-12m', 'open 6–12 months'], ['>1y', 'open > 1 year']];
  const row = (g, w) => V.find(r => r.group === g && r.dtc_bin === w);
  const nG = g => (V.find(r => r.group === g) || {}).markets || 0;
  const series = key => GRP.map(([g, name]) => ({ name: `${name} (${fi(nG(g))})`, values: WIN.map(w => row(g, w)?.[key] ?? 0) }));
  sectionHead(main, 'When long markets trade', `The ${fi(F.used)} usable long markets above, split by how long they were open, by time left until they resolved. A market can only trade in windows it was open for, so a short market has no bars far out. Each window has a different length.`);
  const totG = (g, key) => WIN.reduce((a, w) => a + (row(g, w)?.[key] ?? 0), 0);
  const nWC = (V.find(r => r.group === '>1y') || {}).wc_markets || 0, hasWC = totG('>1y', 'avg_volume_wc') > 0.1 * totG('>1y', 'avg_volume');   // split shown only when the World Cup is a big part
  const v1 = card(`Average ${unit} traded in each window`, 'Per market in the group; a market not yet open counts as 0, so each group’s bars add up to its average lifetime volume.' + (hasWC ? ' The lighter top of each bar is markets about the 2026 World Cup.' : ''));
  if (!hasWC) C.vbar(v1, WIN.map(w => VLAB[w]), series('avg_volume'), { fmtV: big, H: 240 });
  else C.vbarGS(v1, WIN.map(w => VLAB[w]), GRP.map(([g, name], k) => ({ name: `${name} (${fi(nG(g))})`, color: C.SERIES[k], parts: [
    { name: 'other markets', values: WIN.map(w => (row(g, w)?.avg_volume ?? 0) - (row(g, w)?.avg_volume_wc ?? 0)) },
    { name: 'World Cup markets', values: WIN.map(w => row(g, w)?.avg_volume_wc ?? 0), opacity: 0.4 }] })), { fmtV: big, H: 240 });
  const v2 = card('Share of lifetime volume in each window', 'The part of each market’s lifetime volume traded in that window, averaged over the group; each group’s bars add up to 100%.');
  C.vbar(v2, WIN.map(w => VLAB[w]), series('share_of_volume'), { fmtV: v => pct(v, v < 0.01 ? 1 : 0), H: 240 });
  const sum = (g, key, ws) => ws.reduce((a, w) => a + (row(g, w)?.[key] ?? 0), 0);
  const EARLY = ['>365d', '180-365d'], LATE = ['30-90d', '7-30d', '1-7d', '0-1d'];
  const wcShare = sum('>1y', 'avg_volume_wc', WIN) / sum('>1y', 'avg_volume', WIN);
  v1.append(h('p', { class: 'note' }, hasWC && wcShare > 0.5
    ? `The tall bars for markets open over a year are mostly ${fi(nWC)} markets about the 2026 World Cup (${pct(wcShare)} of that group’s volume); the other long markets trade much less.`
    : `Markets open over a year trade about ${big(sum('>1y', 'avg_volume', EARLY))} ${unit} each more than 6 months before resolving, against ${big(sum('>1y', 'avg_volume', LATE))} in the last 3 months.`));
  v2.append(h('p', { class: 'note' }, `Even markets open over a year do only ${pct(sum('>1y', 'share_of_volume', EARLY))} of their trading more than 6 months out and ${pct(sum('>1y', 'share_of_volume', LATE))} in the last 3 months (markets open 6–12 months: ${pct(sum('6-12m', 'share_of_volume', EARLY))} and ${pct(sum('6-12m', 'share_of_volume', LATE))}).`));
  main.append(grid(v1, v2));
}

// ------------------------------------------------------------------ Accuracy
function pageAccuracy(main) {
  const wrap = h('div', { class: 'narrow' }); main.append(wrap); main = wrap;
  pageHead(main, 'How good are prices far from resolution?', 'Settled yes/no markets, scored with the Brier score: the squared gap between the price and what happened (0 = perfect, lower is better).');

  // 1 ── accuracy by distance and by market type
  sectionHead(main, '1. Prices get less accurate the further out they are');
  const A = Object.fromEntries(S.accuracy[180].map(r => [r.k, r])), Y = Object.fromEntries(S.accuracy[365].map(r => [r.k, r]));
  const ks = [365, 180, 90, 30, 7, 1], lab = k => k === 365 ? '1 year' : k === 1 ? '1 day' : k + ' days';
  const c1 = card('By days before close', `One year out, prices score ${f2(Y[365].brier)}; on the final day, about ${f2(A[1].brier)}.`, ['Each line follows the same markets at every point', `${fi(Y[1].markets)} markets were open a full year, ${fi(A[1].markets)} at least 180 days`]);
  C.line(c1, ks.map(lab), [
    { name: `open 1+ year (${fi(Y[1].markets)})`, values: ks.map(k => Y[k]?.brier ?? null) },
    { name: `open 180+ days (${fi(A[1].markets)})`, values: ks.map(k => A[k]?.brier ?? null) }], { fmtV: f3, ymin: 0, fmtX: x => x, H: 170 });
  const by = S.accuracy_group, groups = ['Econ/Fin', 'Politics', 'Sports', 'Tech/AI/Co', 'Other'].filter(g => by.some(r => r.group === g));
  const at90 = groups.map(g => by.find(r => r.group === g && r.k === 90)).filter(Boolean).sort((a, b) => b.brier - a.brier);
  const c2 = card('By market type', `${at90[0].group} markets are the least accurate 90 days out (${f3(at90[0].brier)}), ${at90[at90.length - 1].group} the most (${f3(at90[at90.length - 1].brier)}).`, ['Markets open 90+ days, same markets at each point', 'Groups: ' + groups.map(g => `${g} ${fi(by.find(r => r.group === g)?.markets)}`).join(' · '), 'Small groups are noisy; treat differences as rough']);
  C.line(c2, ['90 days', '30 days', '7 days', '1 day'], groups.map(g => ({ name: `${g} (${fi(by.find(r => r.group === g)?.markets)})`, values: [90, 30, 7, 1].map(k => by.find(r => r.group === g && r.k === k)?.brier ?? null) })), { fmtV: f3, ymin: 0, fmtX: x => x, H: 170 });
  main.append(grid(c1, c2));
  const CB = S.cal_by_h, CC = S.cal_curves, allK = k => CB.find(r => r.k === k && r.sample.startsWith('all')), fixK = k => CB.find(r => r.k === k && r.sample.startsWith('same'));
  const klab = k => k === 1 ? '1 day' : k + ' days';
  const cc = card('Calibration by days before close', 'Share that came true vs the price, in 10¢ bins. On the diagonal = calibrated; dot size = number of markets.', ['All settled yes/no markets with a price at that distance', ...[1, 30, 180].map(k => `${klab(k)} before: ${fi(allK(k).markets)} markets, ${fi(allK(k).events)} events`)]);
  C.calibration(cc, [1, 30, 180].map(k => ({ name: `${klab(k)} before`, bins: CC.filter(r => r.k === k).map(r => ({ mean_pred: r.mean_pred, mean_y: r.mean_obs, n: r.n, bin: r.bin })) })), { H: 220 });
  const cd = card('Why Brier rises: calibration vs resolution', `Brier = miscalibration − resolution + uncertainty (Murphy decomposition), same ${fi(fixK(1).markets)} markets at every distance. Far-out Brier is higher mainly because resolution falls (prices separate outcomes less); miscalibration stays small. Calibration error (ECE) rises somewhat.`, ['Miscalibration (reliability) = weighted squared gap between price and observed frequency, by 10¢ bin', 'Resolution = how far the bins’ observed frequencies spread from the base rate (higher = more informative)', 'ECE = weighted mean |price − observed frequency|; 95% CI bootstrapped over events', `On all markets priced at each distance, ECE rises from ${f3(allK(1).ece)} (1 day) to ${f3(allK(180).ece)} (180 days)`]);
  cd.append(simpleTable([{ key: 'k', label: 'Before', render: r => h('span', { style: 'white-space:nowrap' }, klab(r.k)) }, { key: 'brier', label: 'Brier', num: true, render: r => f3(r.brier) }, { key: 'reliability', label: 'Miscalib.', num: true, render: r => f3(r.reliability) }, { key: 'resolution', label: 'Resolution', num: true, render: r => f3(r.resolution) }, { key: 'ece', label: 'ECE', num: true, render: r => h('span', {}, f3(r.ece), h('div', { class: 'muted small' }, `${f3(r.ece_lo)}–${f3(r.ece_hi)}`)) }], [1, 7, 30, 90, 180].map(fixK)));
  main.append(h('div', { class: 'grid', style: 'margin-top:16px' }, cc, cd));

  // 2 ── liquidity vs accuracy, one liquidity measure at a time
  sectionHead(main, isPM() ? '2. Liquidity and accuracy' : '2. Liquid markets look more accurate, mostly because their prices are more sure', `${fi(S.liq_sample)} settled markets priced 30 days before close; liquidity measured over the 30 days before. ${isPM() ? 'Polymarket has no spread or open-interest history, so only trading volume and trading days are shown.' : 'Order-book depth isn’t available historically.'}`);
  const rngl = (lo, hi, f) => `${f(lo)}–${f(hi)}`;
  const MEAS_ALL = [
    ['spread', 'Bid–ask spread', 'gap between the best buy and sell price', r => rngl(r.min, r.max, v => (v * 100).toFixed(v < 0.01 ? 1 : 0)) + '¢'],
    ['open_interest', 'Contracts held', 'contracts people held on the scoring day', r => rngl(r.min, r.max, big)],
    ['volume', 'Contracts traded', 'contracts bought and sold in the 30 days before', r => rngl(r.min, r.max, big)],
    ['days_traded', 'How often it traded', 'days, out of 30, with at least one trade', r => rngl(r.min, r.max, v => Math.round(v * 30)) + ' days'],
  ];
  const MEAS = MEAS_ALL.filter(m => (S.liq_measures || ['spread', 'open_interest', 'volume', 'days_traded']).includes(m[0]));
  if (isPM()) { MEAS.find(m => m[0] === 'volume')[1] = 'Shares traded'; MEAS.find(m => m[0] === 'volume')[2] = 'shares bought and sold in the 30 days before'; }
  const bands = ['40–60¢', '20–40¢ or 60–80¢', '5–20¢ or 80–95¢', '0–5¢ or 95–100¢'], blab = ['40–60¢', '20–40 / 60–80¢', '5–20 / 80–95¢', '0–5 / 95–100¢'];
  let meas = MEAS[0][0];
  const seg = h('div', { class: 'seg' });
  main.append(h('div', { class: 'filters' }, h('label', {}, 'Liquidity measure'), seg));
  const row = h('div', { class: 'grid liq' }); main.append(row);
  const takeaway = h('p', { class: 'note', style: 'max-width:900px;margin-top:10px' }); main.append(takeaway);
  function drawLiq() {
    seg.replaceChildren(...MEAS.map(([k, t]) => h('button', { class: k === meas ? 'on' : '', onclick: () => { meas = k; drawLiq(); } }, t)));
    const [k, title, what, labf] = MEAS.find(m => m[0] === meas);
    const rows = [1, 2, 3, 4, 5].map(q => S.liq_quintiles.find(r => r.measure === k && r.quintile === q)), labels = rows.map(labf);
    const left = card(`Brier score by ${title.toLowerCase()}`, `Five equal-size groups by ${what}; least liquid on the left.`);
    C.vbar(left, labels, rows.map(r => r.brier), { fmtV: f3, H: 125, sublabels: rows.map(r => 'n=' + fi(r.markets)) });
    left.append(h('div', { class: 'note', style: 'margin:4px 0 0' }, 'Each market’s price 30 days before close (random 600 per group)'));
    C.strip(left, labels, S.liq_dots[k], { H: 55, tips: [1, 2, 3, 4, 5].map(q => { const x = S.liq_near.find(r => r.measure === k && r.quintile === q); return [{ value: pct(x.share_0_5_or_95_100), label: 'priced 0–5¢ or 95–100¢' }, { value: pct(x.share_0_20_or_80_100), label: 'priced 0–20¢ or 80–100¢' }]; }) });
    const right = card('Same comparison, at equal price sureness', 'Markets grouped by how sure the price was; within each group, the more vs the less liquid half.', ['* p < 0.05, ** p < 0.01: the two halves differ significantly (bootstrap over events)', `${4 * MEAS.length} comparisons in total across the ${MEAS.length} measures, so a single star could be chance`]);
    const marks = bands.map(b => { const x = S.liq_equal_sig.find(r => r.measure === k && r.band === b); return !x ? '' : x.p < 0.01 ? '**' : x.p < 0.05 ? '*' : ''; });
    C.vbar(right, blab, ['less liquid half', 'more liquid half'].map(hf => ({ name: hf, values: bands.map(b => S.liq_equal.find(r => r.measure === k && r.band === b && r.half === hf)?.brier ?? null) })), { fmtV: f3, H: 190, marks, sublabels: bands.map(b => 'n=' + fi(S.liq_equal.filter(r => r.measure === k && r.band === b).reduce((a, r) => a + r.markets, 0))) });
    row.replaceChildren(left, right);
    const sigs = bands.map(b => S.liq_equal_sig.find(r => r.measure === k && r.band === b)).filter(x => x && x.p < 0.05);
    const qq = [1, 5].map(q => S.liq_quintiles.find(r => r.measure === k && r.quintile === q));
    const nb = sigs.filter(x => x.diff_less_minus_more > 0).length, nw = sigs.length - nb;
    takeaway.textContent = `Left: the least liquid group scores ${f3(qq[0].brier)}, the most liquid ${f3(qq[1].brier)}. Right: at equal price sureness, ${nb + nw === 0 ? 'no difference between the halves is significant' : `the more liquid half is significantly better in ${nb} of 4 groups and significantly worse in ${nw}`}.`;
  }
  drawLiq();

  // 3 ── capital lockup
  sectionHead(main, '3. A cost to tying up money?', 'If waiting months for the payout were costly, buying the likely outcome early and holding to resolution should pay more than buying late. The waiting cost should matter most for favourites, where a lot of money is locked up for a small profit.');
  const FR = S.fav_rob.filter(r => r.price === 'midpoint else last trade (baseline)'), ks3 = [180, 90, 30, 7, 1];
  const f80 = FR.find(r => r.threshold === 0.8 && r.k === 180);
  const f90 = FR.find(r => r.threshold === 0.9 && r.k === 180), refs = S.fav_ref.map(r => r.return);
  const f80_1 = FR.find(r => r.threshold === 0.8 && r.k === 1), ref180 = S.fav_ref.find(r => r.k === 180);
  const cf = card('Return from buying favourites and holding to resolution', `Buying markets priced ≥ 80% 180 days before close returned ${pct(f80.return, 1)} (95% CI ${pct(f80.ci_lo, 1)} to ${pct(f80.ci_hi, 1)}, ${f80.events} events), against ${pct(f80_1.return, 1)} one day before. Near-50/50 markets (40–60¢) returned ${pct(ref180.return, 1)} at 180 days (95% CI ${pct(ref180.ci_lo, 1)} to ${pct(ref180.ci_hi, 1)}).`, ['Return = came true ÷ price − 1, averaged within each event, then across events', 'Events per point, 180 → 1 days: ≥70% ' + ks3.map(k => FR.find(r => r.threshold === 0.7 && r.k === k)?.events ?? '–').join(' / ') + '; ≥90% ' + ks3.map(k => FR.find(r => r.threshold === 0.9 && r.k === k)?.events ?? '–').join(' / '), 'Full table with intervals and other price definitions: results/09_favourite_robustness.csv'], 'card wide');
  C.line(cf, ks3.map(klab), [
    ...[0.9, 0.8, 0.7].map(t => ({ name: `favourites, price ≥ ${Math.round(t * 100)}%`, values: ks3.map(k => FR.find(r => r.threshold === t && r.k === k)?.return ?? null) })),
    { name: 'near 50/50 (40–60¢), for reference', values: ks3.map(k => S.fav_ref.find(r => r.k === k)?.return ?? null), dash: '5 4', color: 'var(--muted)' }], { fmtV: v => (v > 0 ? '+' : '') + pct(v, 1), fmtX: x => x + ' before close', ymin: Math.min(-0.06, ...refs.filter(v => v != null)), ymax: Math.max(0.08, ...FR.map(r => r.return).filter(v => v != null)), W: 900, H: 220 });
  main.append(h('div', { class: 'grid' }, cf));
}

// ------------------------------------------------------------------ Regression
function pageRegressions(main) {
  const wrap = h('div', { class: 'narrow', style: 'max-width:1440px' }); main.append(wrap); main = wrap;
  pageHead(main, 'Does more trading go with more accurate prices?', 'Regressions of each market’s daily Brier score on how much it had traded so far. Sports and crypto markets are left out.');
  const VARIANTS = [['drop last day', 'Drop each market’s last day'], ['all days', 'All days']];
  let variant = VARIANTS[0][0];
  const DATA = () => isPM()
    ? { reg: S.reg || [], cat: S.reg_cat || [], byc: S.reg_bycat || [], dur: 'duration_days' }
    : { reg: S.reg10, cat: S.reg10_cat || [], byc: S.reg10_bycat || [], dur: 'horizon_days' };
  const RG = () => DATA().reg.filter(r => (r.variant || 'all days') === variant);
  const get = (smp, spec, term) => RG().find(r => r.sample === smp && r.spec === spec && r.term === term);
  const SPECS = ['(1) month FE', '(2) + category FE + duration', '(3) month FE + contract FE', '(4) + days-to-expiry bins', '(5) log days to expiry'];
  const first = smp => RG().find(r => r.sample === smp);

  sectionHead(main, 'Setup');
  const c1 = card('Model', null, null, 'card wide');
  c1.append(
    h('div', { class: 'formula' }, tex(String.raw`\begin{aligned}
(1)\;\; \text{Brier}_{m,d} &= \beta\,\log(1+\text{CumVol}_{m,d}) + \theta\,\text{DaysToExpiry}_{m,d} + \mu_{\text{month}(d)} + \varepsilon_{m,d} \\
(2)\;\; \text{Brier}_{m,d} &= \beta\,\log(1+\text{CumVol}_{m,d}) + \theta\,\text{DaysToExpiry}_{m,d} + \lambda\,\text{Duration}_{m} + \mu_{\text{month}(d)} + \kappa_{\text{category}(m)} + \varepsilon_{m,d} \\
(3)\;\; \text{Brier}_{m,d} &= \beta\,\log(1+\text{CumVol}_{m,d}) + \theta\,\text{DaysToExpiry}_{m,d} + \mu_{\text{month}(d)} + \alpha_{m} + \varepsilon_{m,d} \\
(4)\;\; \text{Brier}_{m,d} &= \beta\,\log(1+\text{CumVol}_{m,d}) + \gamma_{\text{bin}(\text{DaysToExpiry}_{m,d})} + \mu_{\text{month}(d)} + \alpha_{m} + \varepsilon_{m,d} \\
(5)\;\; \text{Brier}_{m,d} &= \beta\,\log(1+\text{CumVol}_{m,d}) + \theta\,\log(1+\text{DaysToExpiry}_{m,d}) + \mu_{\text{month}(d)} + \alpha_{m} + \varepsilon_{m,d}
\end{aligned}`, true)),
    h('ul', { class: 'plain' },
      h('li', {}, tex(String.raw`\text{Brier}_{m,d} = (\text{Price}_{m,d} - \text{Outcome}_m)^2`), ': market ', tex('m'), ' on day ', tex('d'), isPM() ? '; price = Polymarket’s daily price of the first outcome (taken at 00:00 UTC; no bid/ask history)' : '; price = bid–ask midpoint at the day’s last hourly bar; days without a two-sided quote are dropped (an old last trade would make illiquid markets look stuck)'),
      h('li', {}, tex(String.raw`\text{CumVol}_{m,d}`), isPM() ? ': shares traded in the market before day ' : ': contracts traded in the market before day ', tex('d')),
      h('li', {}, tex(String.raw`\text{DaysToExpiry}_{m,d}`), ': days left until the market closes; ', tex(String.raw`\text{Duration}_m`), ': days from open to close'),
      h('li', {}, tex(String.raw`\mu`), ': month-year fixed effect; ', tex(String.raw`\kappa`), ': category fixed effect; ', tex(String.raw`\alpha_m`), ': contract fixed effect (compares a market with itself over time)'),
      h('li', {}, tex(String.raw`\gamma_{\text{bin}}`), ': days-to-expiry bin fixed effect, a separate baseline for each of the 20 bins in the table below. (4) is (3) with these bins in place of the straight line ', tex(String.raw`\theta\,\text{DaysToExpiry}`), ', because accuracy does not change at a constant rate as the close approaches.'),
      h('li', {}, '(5) is (3) with ', tex(String.raw`\log(1+\text{DaysToExpiry}_{m,d})`), ' in place of the straight line: each extra day matters more near the close than far from it. The +1 keeps it defined on the closing day.'),
      h('li', {}, 'OLS; standard errors clustered by event')));
  const HZ_BINS = [
    ['First week, one bin per day', '0–1, 1–2, 2–3, 3–4, 4–5, 5–6, 6–7'],
    ['Weeks 2–4, weekly', '7–14, 14–21, 21–28'],
    ['Weeks 5–8, two-week bins', '28–42, 42–56'],
    ['About monthly', '56–90, 90–120, 120–150, 150–180'],
    ['Two-month bins', '180–240, 240–300, 300–365'],
    ['Over a year', '365 or more']];
  c1.append(h('p', {}, h('b', {}, 'Days-to-expiry bins in (4)'), ' (days; each bin includes its lower end, e.g. 7–14 means 7 ≤ days < 14):'),
    h('div', { style: 'max-width:620px' }, simpleTable([{ key: 0, label: 'Range', render: r => r[0] }, { key: 1, label: 'Bins (days to expiry)', render: r => r[1] }], HZ_BINS)));
  main.append(h('div', { class: 'grid' }, c1));

  sectionHead(main, 'Results');
  const seg = h('div', { class: 'seg' }), res = h('div');
  main.append(h('div', { class: 'filters' }, h('label', {}, 'Days used'), seg, infoIcon('On a market’s last day the price usually already reflects the outcome (see the Last days tab). Dropping it removes those rows; markets open under a day mostly drop out.')), res);
  const fmt = v => Math.abs(v) < 0.001 ? v.toFixed(5) : v.toFixed(4);
  const cell = (smp, spec, term) => { const x = get(smp, spec, term); if (!x) return '–'; const p = pval(x.t); return h('span', {}, h('span', { class: p < 0.05 ? 'sig' : '' }, (x.coef > 0 ? '+' : '') + fmt(x.coef) + stars(p)), h('br'), h('span', { class: 'muted small', style: 'white-space:nowrap' }, `SE ${fmt(x.se)} · p ${p < 0.001 ? '< 0.001' : '= ' + p.toFixed(3)}`)); };
  const A = 'all', L = 'duration > 180 days';
  const coefTable = (smp, title) => {
    const f = first(smp);
    const c = card(title, f ? `${fi(f.n)} market-days, ${fi(f.contracts ?? f.markets)} markets, ${fi(f.events)} events. Average Brier ${f2(f.mean_brier)}.` : 'No results yet.');
    c.append(simpleTable([
      { key: 's', label: 'Specification', render: r => r },
      { key: 'v', label: 'β volume', num: true, render: r => cell(smp, r, 'log_cum_vol') },
      { key: 'd', label: 'θ days to expiry', num: true, render: r => r === SPECS[3] ? h('span', { class: 'muted small' }, 'bins (γ)') : r === SPECS[4] ? h('span', {}, cell(smp, r, 'log_days_to_exp'), h('div', { class: 'muted small' }, 'per unit of log(1 + days)')) : cell(smp, r, 'days_to_exp') },
      { key: 'u', label: 'λ duration', num: true, render: r => cell(smp, r, DATA().dur) }], SPECS));
    return c;
  };
  const catCard = smp => {
    const rows = DATA().cat.filter(r => r.sample === smp && (r.variant || 'all days') === variant), tot = rows.reduce((a, r) => a + r.market_days, 0);
    if (!rows.length) { const c = card('By category', 'Share of market-days (rows in the regression)'); c.append(h('p', { class: 'muted small' }, 'Not computed yet: rerun Polymarket job 04.')); return c; }
    const items = rows.map(r => ({ label: r.category, value: r.market_days / tot, sub: `${fi(r.markets)} markets, ${fi(r.market_days)} market-days` })).sort((a, b) => b.value - a.value);
    const c = card('By category', 'Share of market-days (rows in the regression)'), box = h('div', { style: 'max-width:380px' }); c.append(box);
    C.hbar(box, items, { W: 340, labelW: 140, labelChars: 22, fmtV: v => v < 0.001 ? '< 0.1%' : pct(v, v < 0.01 ? 1 : 0) });
    return c;
  };
  function draw() {
    seg.replaceChildren(...VARIANTS.map(([k, t]) => h('button', { class: k === variant ? 'on' : '', onclick: () => { variant = k; draw(); } }, t)));
    res.replaceChildren();
    if (isPM()) {
      if (!RG().length) { res.append(h('p', { class: 'note' }, 'Polymarket results not available yet.')); return; }
      res.append(h('p', { class: 'note' }, 'Polymarket: resolved yes/no markets open at least a day with some volume, started from 30 Sep 2023 (Polymarket’s trade records begin then). Price = the daily price of the first outcome (usually “Yes”) from Polymarket’s price history; it has no bid/ask, so the two-sided-quote rule used for Kalshi cannot be applied. Volume = shares traded (taker side of each fill) before day d. Duration = days from start to close.'));
    }
    res.append(h('div', { class: 'grid tc' }, coefTable(A, 'All markets'), catCard(A)));
    res.append(h('div', { class: 'grid tc' }, coefTable(L, 'Markets open more than 180 days'), catCard(L)));
    res.append(h('p', { class: 'note' }, 'Each cell: the coefficient, then its standard error (SE) and p-value. Stars: * p < 0.05, ** p < 0.01, *** p < 0.001. The p-value tests whether the coefficient is zero; it comes from t = coefficient ÷ SE (two-sided). Duration is only in spec (2).'));
    if (!isPM()) res.append(h('p', { class: 'note' }, '“Expired in 2026” gives the same numbers as “All” (every usable market closed in 2026). “Expired in 2025” has no data: only 25 settled 2025 markets remain in Kalshi’s API, none of them traded.'));
    else {
      const YRS = [2023, 2024, 2025, 2026].map(y => `expired in ${y}`).filter(y => first(y));
      const c = card('By year the market expired', 'β volume for markets that closed in each year.', null, 'card wide');
      c.append(simpleTable([
        { key: 'y', label: 'Markets that closed in', render: y => y.slice(-4) },
        { key: 'n', label: 'Market-days', num: true, render: y => fi(first(y).n) },
        { key: 'm', label: 'Markets', num: true, render: y => fi(first(y).markets) },
        ...SPECS.map((sp, i) => ({ key: 'b' + i, label: `β volume (${i + 1})`, num: true, render: y => first(y).note ? h('span', { class: 'muted small' }, 'too few events') : cell(y, sp, 'log_cum_vol') }))], YRS));
      res.append(h('div', { class: 'grid' }, c));
    }

    sectionHead(res, 'By category', 'Specs (1), (3) and (4) run separately for each category, so the volume effect can differ between them. Categories with fewer than 20 events are not estimated; with few events, “not significant” often means “not enough data”.');
    const BC = DATA().byc.filter(r => (r.variant || 'all days') === variant);
    if (!BC.length) res.append(h('p', { class: 'note' }, 'Not computed yet: rerun Polymarket job 04.'));
    const bcCell = (smp, cat, spec, term = 'log_cum_vol') => {
      const any = BC.find(r => r.sample === smp && r.category === cat && r.spec === spec);
      if (any && any.note) return h('span', { class: 'muted small' }, 'too few events');
      const x = BC.find(r => r.sample === smp && r.category === cat && r.spec === spec && r.term === term); if (!x) return '–';
      const p = pval(x.t);
      return h('span', {}, h('span', { class: p < 0.05 ? 'sig' : '' }, (x.coef > 0 ? '+' : '') + fmt(x.coef) + stars(p)), h('br'), h('span', { class: 'muted small', style: 'white-space:nowrap' }, `SE ${fmt(x.se)} · p ${p < 0.001 ? '< 0.001' : '= ' + p.toFixed(3)}`));
    };
    const bcTable = (smp, title) => {
      const cats = [...new Map(BC.filter(r => r.sample === smp).map(r => [r.category, r])).values()].sort((a, b) => b.n - a.n);
      const c = card(title, 'One row per category, largest first.', null, 'card wide');
      c.append(simpleTable([
        { key: 'category', label: 'Category', render: r => r.category },
        { key: 'events', label: 'Events', num: true, render: r => fi(r.events) },
        { key: 'n', label: 'Market-days', num: true, render: r => fi(r.n) },
        { key: 'b1', label: 'β volume (1)', num: true, render: r => bcCell(smp, r.category, SPECS[0]) },
        { key: 'b3', label: 'β volume (3)', num: true, render: r => bcCell(smp, r.category, SPECS[2]) },
        { key: 'b4', label: 'β volume (4)', num: true, render: r => bcCell(smp, r.category, SPECS[3]) },
        { key: 't1', label: 'θ days to expiry (1)', num: true, render: r => bcCell(smp, r.category, SPECS[0], 'days_to_exp') },
        { key: 't3', label: 'θ days to expiry (3)', num: true, render: r => bcCell(smp, r.category, SPECS[2], 'days_to_exp') }], cats));
      return c;
    };
    if (BC.length) res.append(h('div', { class: 'grid' }, bcTable(A, 'All markets'), bcTable(L, 'Markets open more than 180 days')));
    const tally = smp => { const xs = BC.filter(r => r.sample === smp && r.spec === SPECS[3] && r.term === 'log_cum_vol'); return [xs.filter(x => x.coef < 0 && pval(x.t) < 0.05).length, xs.length]; };
    const [ka, na] = tally(A), [kl, nl] = tally(L);
    if (BC.length) res.append(h('p', { class: 'note' }, `In spec (4), more volume goes with significantly lower Brier in ${ka} of ${na} categories across all markets, and in ${kl} of ${nl} categories among markets open more than 180 days.`));

    sectionHead(res, 'Conclusion');
    const sig = x => x && pval(x.t) < 0.05;
    const summOf = rows => { const xs = SPECS.map(sp => rows.find(r => r.spec === sp && r.term === 'log_cum_vol')).filter(Boolean); return [xs.filter(x => x.coef < 0 && sig(x)).length, xs.filter(x => x.coef > 0 && sig(x)).length, xs.length]; };
    const line = (smp, label) => { const [neg, pos, n] = summOf(RG().filter(r => r.sample === smp)), f = first(smp), b3 = get(smp, SPECS[2], 'log_cum_vol');
      const within = b3 ? `Within the same market (3), doubling cumulative volume ${b3.coef < 0 ? 'lowers' : 'raises'} Brier by about ${(Math.abs(b3.coef) * Math.LN2).toFixed(3)}${sig(b3) ? '' : ' (not significant)'}` : '';
      return `${label}: more past trading goes with significantly lower Brier in ${neg} of ${n} specifications${pos ? `, and significantly higher Brier in ${pos}` : ''}. ${within}, against an average of ${f2(f.mean_brier)} (${fi(f.events)} events).`; };
    const items = [line(A, 'All markets'), line(L, 'Markets open more than 180 days')];
    if (isPM()) {
      const kRows = S.reg10.filter(r => (r.variant || 'all days') === variant && r.sample === L), [kn, kp, kt] = summOf(kRows), kL = kRows[0];
      items.push(`Polymarket has more long markets than the Kalshi archive: ${fi(first(L).events)} events open more than 180 days here, against ${fi(kL.events)} on Kalshi, where more trading goes with significantly lower Brier in ${kn} of ${kt} specifications for long markets.`,
        'Polymarket’s price series has no bid/ask, so stale prices cannot be removed: days without trading keep the last price. That ties low volume to flat Brier and may make the volume effect look larger.');
    } else {
      const b3 = get(A, SPECS[2], 'log_cum_vol'), b4 = get(A, SPECS[3], 'log_cum_vol');
      const getV = (v, spec) => S.reg10.find(r => (r.variant || 'all days') === v && r.sample === A && r.spec === spec && r.term === 'log_cum_vol');
      const firstV = v => S.reg10.find(r => (r.variant || 'all days') === v && r.sample === A);
      const w3 = getV('all days', SPECS[2]), d3 = getV('drop last day', SPECS[2]), dropped = 1 - firstV('drop last day').n / firstV('all days').n;
      const dtx = get(A, SPECS[2], 'days_to_exp');
      items.push(`Replacing the straight-line days to expiry (3) with bins (4) changes the within-market volume effect from ${b3.coef.toFixed(4)} to ${b4.coef.toFixed(4)}${sig(b4) ? '' : ' (not significant)'}.`,
        `Dropping each market’s last day removes ${pct(dropped, 0)} of all-market rows; the within-market volume effect (3) goes from ${w3.coef.toFixed(4)} to ${d3.coef.toFixed(4)}${sig(d3) ? '' : ' (not significant)'}.`,
        `Days to expiry: within the same market (3), each extra day before expiry changes Brier by ${dtx.coef > 0 ? '+' : ''}${dtx.coef.toFixed(4)}${sig(dtx) ? '' : ' (not significant)'}.`);
    }
    items.push('Volume is not randomly assigned: it builds up as news arrives and expiry approaches, so these are associations, not causal effects.');
    const c3 = h('div', { class: 'card wide' });
    c3.append(h('ul', { class: 'plain' }, items.map(t => h('li', {}, t))));
    res.append(h('div', { class: 'grid' }, c3));
  }
  draw();
}

// ------------------------------------------------------------------ Last days
function pageTail(main) {
  const wrap = h('div', { class: 'narrow tail' }); main.append(wrap); main = wrap;
  pageHead(main, 'The last days of a market', `Is the outcome already known before a market closes, and how many days of data come from that stretch? Settled ${PNAME()} markets other than sports and crypto.`);
  const T = S.tail, row = g => T.find(r => r.group === g);
  const GROUPS = [['all', 'All markets'], ['< 1 day', 'Under 1 day'], ['1-7 days', '1–7 days'], ['7-30 days', '1–4 weeks'], ['30-180 days', '1–6 months'], ['> 180 days', 'Over 6 months']];
  const rows = GROUPS.map(([k, label]) => ({ ...row(k), label }));
  const lab = { key: 'label', label: 'Market open for', render: r => r.label };
  const n = { key: 'markets', label: 'Markets', num: true, render: r => fi(r.markets) };
  const g = h('div', { class: 'grid' }); main.append(g);
  const section = (title, sub, table, note) => { const c = card(title, sub, null, 'card wide'); c.append(table); if (note) c.append(h('p', { class: 'note' }, note)); g.append(c); };

  const PM = isPM(), L6 = row('> 180 days'), M16 = row('30-180 days');
  if (PM) section('1. Are markets resolved late?', `Often, for longer markets: ${pct(M16.close_after_expected_over_1d)} of markets open 1–6 months and ${pct(L6.close_after_expected_over_1d)} of those open over 6 months resolved more than a day after their scheduled end date.`,
    simpleTable([lab, n,
      { key: 'a', label: 'Resolved > 1 day after the scheduled end date', num: true, render: r => r.markets ? pct(r.close_after_expected_over_1d, 1) : '–' },
      { key: 'c', label: 'Resolved > 1 day before the scheduled end date', num: true, render: r => r.markets ? pct(r.close_before_expected_over_1d, 0) : '–' },
      { key: 'd', label: 'Share of market-days after the scheduled end', num: true, render: r => r.markets ? pct(r.rows_after_expected, 1) : '–' }], rows),
    'Polymarket settles through a proposal-and-challenge process, which can take days after the scheduled end; the close time used here is when the market resolved. Markets open under a day are not in the Polymarket sample.');
  else section('1. Are markets resolved late?', `${pct(row('all').close_after_expected_over_1d, 1)} of markets traded more than a day past the expected outcome time, and ${pct(row('all').settle_lag_over_1d, 1)} were paid out more than a day after trading stopped.`,
    simpleTable([lab, n,
      { key: 'a', label: 'Traded > 1 day past the expected outcome time', num: true, render: r => pct(r.close_after_expected_over_1d, 1) },
      { key: 'b', label: 'Paid out > 1 day after trading stopped', num: true, render: r => pct(r.settle_lag_over_1d, 1) },
      { key: 'c', label: 'Closed > 1 day before the scheduled date', num: true, render: r => pct(r.close_before_expected_over_1d, 0) }], rows),
    'Closing before the scheduled date is normal: the event happened early (e.g. an election was called), and the market closed then.');

  section('2. Does the last day already show the answer?', PM ? `For long markets, yes (${pct(L6.final_day_locked)} within 2¢ of the outcome); for short ones, mostly not, because Polymarket’s daily price is taken at the start of the day (00:00 UTC), before most events happen.` : `For ${pct(row('all').final_day_locked)} of markets the last-day price was within 2¢ of the outcome; last days are ${pct(row('all').rows_final_day)} of all market-days.`,
    simpleTable([lab, n,
      { key: 'a', label: 'Last-day price within 2¢ of the outcome', num: true, render: r => r.markets ? pct(r.final_day_locked, 0) : '–' },
      { key: 'b', label: 'Share of market-days that are a last day', num: true, render: r => r.markets ? pct(r.rows_final_day, r.rows_final_day < 0.01 ? 1 : 0) : '–' },
      { key: 'c', label: 'Brier, last day', num: true, render: r => f3(r.brier_final_day) },
      { key: 'd', label: 'Brier, other days', num: true, render: r => f3(r.brier_other_days) }], rows),
    PM ? 'On Polymarket the last day’s score is close to other days’ for short markets, so dropping it matters less than on Kalshi.' : 'The last day has the most past trading and a near-perfect score, so it pushes a volume-and-accuracy regression toward “more volume, more accurate”. Counts here include days priced by a last trade.');

  const LONG = [['> 180 days', 'All'], ...T.filter(r => r.group.startsWith('> 180 days: ')).map(r => [r.group, r.group.slice(12)])];
  section('3. Long markets: prices sitting at the answer for weeks', `Markets open over 6 months: a median of ${fi(L6.locked_tail_days_median)} days at the answer before ${PM ? 'resolving' : 'closing'}; ${pct(L6.locked_tail_over_7d)} of them spend more than a week there, and these days are ${pct(L6.rows_in_locked_tail)} of their market-days.`,
    simpleTable([{ key: 'label', label: 'Category', render: r => r.label }, n,
      { key: 'a', label: 'Median days at the answer before closing', num: true, render: r => fi(r.locked_tail_days_median) },
      { key: 'b', label: 'Markets with > 7 such days', num: true, render: r => pct(r.locked_tail_over_7d, 0) },
      { key: 'c', label: 'Share of rows in that stretch', num: true, render: r => pct(r.rows_in_locked_tail, 0) }], LONG.map(([k, label]) => ({ ...row(k), label }))),
    '“At the answer” means the price stayed within 2¢ of the final outcome every day until the close. This mixes questions that were effectively decided (a candidate dropped out) with long shots that sat at 1¢ throughout and lost.');

  const c = card('What this means for the regression', null, null, 'card wide');
  if (PM) c.append(h('ul', { class: 'plain' },
    h('li', {}, 'On Polymarket the bigger issue is the long stretch at the answer before long markets resolve, partly because resolution comes after the scheduled end.'),
    h('li', {}, 'A rule that does not use the outcome: drop days after each market’s scheduled end date, or measure days to expiry to the scheduled end instead of the resolution time.'),
    h('li', {}, 'Dropping the last day is still a sensible check, though fewer last days already show the answer here than on Kalshi.'),
    h('li', {}, 'Do not drop days because the price is near the outcome: that uses the answer and removes the accurate days.')));
  else c.append(h('ul', { class: 'plain' },
    h('li', {}, 'Late resolution is not a problem on Kalshi; the last day is.'),
    h('li', {}, 'Main fix: drop each market’s last day. The rule does not depend on the outcome, and markets open under a day mostly drop out.'),
    h('li', {}, 'Checks: drop the last 7 days; keep only markets open at least 7 days.'),
    h('li', {}, 'Do not drop days because the price is near the outcome: that uses the answer and removes the accurate days.')));
  g.append(c);
}

// ------------------------------------------------------------------ Rewards
function pageRewardsPM(main) {
  const I = S.inventory;
  pageHead(main, 'Polymarket’s reward programs', 'Polymarket pays market makers for keeping orders near the midpoint (liquidity rewards) and, since June 2026, pays interest on positions in some long-dated markets (holding rewards).');
  main.append(h('div', { class: 'tiles' }, tile(fi(I.markets_open), 'markets open now'), tile(fi(I.open_holding_rewards), 'of them marked for holding rewards')));
  const c = card('What we can and can’t see', null, null, 'card wide');
  c.append(h('ul', { class: 'plain' },
    h('li', {}, 'Polymarket’s API shows each open market’s current reward settings (minimum order size, maximum distance from the midpoint, holding rewards on or off).'),
    h('li', {}, 'It does not show past programs, when they started or stopped, or how much was paid. So the Kalshi analyses of reward days cannot be repeated here.'),
    h('li', {}, 'Holding rewards (3.25% a year, paid on positions held in selected long-dated markets) started on 1 June 2026. Comparing those markets with similar ones before and after that date is a direct test of an interest subsidy; it is the next step.')));
  main.append(h('div', { class: 'grid', style: 'margin-top:16px' }, c));
}

function pageCoveragePM(main) {
  const I = S.inventory;
  pageHead(main, 'What data we have, in plain terms', 'A quick guide to what the Polymarket data can and can’t show. The analyses leave out sports and crypto markets. The Data tab has the counts.');
  const c1 = card('What we have', null, null, 'card wide'); const g = h('div', { class: 'grid' }, c1); main.append(g);
  c1.append(simpleTable([{ key: 0, label: 'Data' }, { key: 1, label: 'What it tells us' }, { key: 2, label: 'How far back' }, { key: 3, label: 'Have it?', render: r => h('span', { class: 'have' }, r[3]) }], [
    ['List of markets', 'Every market’s question, start and end dates, outcome, total amount traded, and tags', `All markets, from ${I.first_start}`, '✓ Yes'],
    ['Daily price history', 'One price per day (at 00:00 UTC) for the first outcome, over the market’s whole life', 'Resolved yes/no markets open at least a day that traded', '✓ Yes'],
    ['Individual trades', 'Every fill: time, price, size, buy or sell, and the trader’s wallet', `Same markets, from 30 Sep 2023 (${I.trade_first} – ${I.trade_last})`, '✓ Yes'],
    ['Reward programs', 'Current reward settings of open markets', 'Today only', '⚠ No history'],
    ['Order book depth', 'Orders waiting at each price', '—', '✗ No'],
  ]));
  const c2 = card('What we don’t have', null, null, 'card wide'); g.append(c2);
  c2.append(simpleTable([{ key: 0, label: 'Missing' }, { key: 1, label: 'Why' }], [
    ['Bid–ask spread and order book history', 'Polymarket’s API gives price history but not past order books'],
    ['Trades before 30 Sep 2023', 'Polymarket’s trade records start then (2020–2022 trades went through an automated market maker and are only on the blockchain). Markets that started earlier are left out of the analyses.'],
    ['Reward history and payouts', 'Only current settings are public'],
    ['Prices for markets open under a day or never traded', 'Left out of the download (mostly 5- and 15-minute crypto markets)'],
    ['Hourly prices', 'Available only in 15-day windows; daily was enough for these analyses'],
  ]));
  main.append(h('p', { class: 'summary' }, 'So for every resolved yes/no Polymarket market open at least a day, we can see its daily price and every trade, but not its order book.'));
}

function pageDataPM(main) {
  const I = S.inventory, N = S.samples, r0 = (S.reg || []).find(r => r.variant === 'all days' && r.sample === 'all');
  pageHead(main, 'Data: counts and samples', 'How big each Polymarket dataset is (all markets), and how many markets each analysis uses (sports and crypto left out).');
  const c1 = card('Datasets', null, null, 'card wide'); const g = h('div', { class: 'grid' }, c1); main.append(g);
  c1.append(simpleTable([{ key: 0, label: 'Dataset' }, { key: 1, label: 'n', num: true }, { key: 2, label: 'Breakdown' }, { key: 3, label: 'Dates' }, { key: 4, label: 'Source' }], [
    ['Markets', fi(I.markets), `${fi(I.markets_traded)} ever traded · ${fi(I.markets_resolved)} resolved yes/no · ${fi(I.markets_open)} open`, `${I.first_start} – ${I.last_end}`, 'Gamma API'],
    ['Events', fi(I.events), 'groups of related markets', '', 'Gamma API'],
    ['Markets analysed', fi(I.selected), `resolved yes/no, traded, open ≥ 1 day, started from 30 Sep 2023 · ${fi(I.selected_180)} open > 180 days`, '', ''],
    ['Daily prices', fi(I.price_days), `${fi(I.price_markets)} markets`, `${I.price_first} – ${I.price_last}`, 'CLOB price history'],
    ['Trades', fi(I.trades), `${big(I.trade_shares)} shares`, `${I.trade_first} – ${I.trade_last}`, 'Data API'],
  ]));
  const ag = N.accuracy_group;
  const c2 = card('Samples used in each analysis', null, null, 'card wide'); g.append(c2);
  c2.append(simpleTable([{ key: 0, label: 'Tab' }, { key: 1, label: 'Analysis' }, { key: 2, label: 'Sample' }, { key: 3, label: 'Markets', num: true }, { key: 4, label: 'Observations', num: true }], [
    ['Horizons', 'Volume by horizon', 'All markets except sports and crypto', fi(N.horizon_markets), ''],
    ['Horizons', 'Trades by horizon', 'Markets analysed that traded', fi(N.trade_markets), fi(I.trades) + ' trades'],
    ['Accuracy', 'Brier and AUC', 'Resolved yes/no markets priced at every distance', `${fi(N.accuracy[90])} / ${fi(N.accuracy[180])} / ${fi(N.accuracy[365])}`, 'open ≥ 90 / 180 / 365 days'],
    ['Accuracy', 'By market type', 'The open-≥ 90-days sample', fi(N.accuracy[90]), Object.entries(ag).map(([k, v]) => `${k} ${fi(v)}`).join(' · ')],
    ['Accuracy', 'Calibration and returns', 'Resolved yes/no markets with a price that far out', `${fi(N.calibration[30])} / ${fi(N.calibration[90])} / ${fi(N.calibration[180])}`, 'priced 30 / 90 / 180 days out'],
    ['Regression', 'Brier on past volume', 'Markets analysed, one row per market-day', r0 ? fi(r0.markets) : '–', r0 ? fi(r0.n) + ' market-days' : ''],
  ]));
}

function pageRewards(main) {
  if (isPM()) return pageRewardsPM(main);
  const wrap = h('div', { class: 'narrow' }); main.append(wrap); main = wrap;
  const T = S.reward_totals;
  const num = (v, d) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d);
  pageHead(main, 'Do Kalshi’s liquidity rewards make markets better?', 'Kalshi pays traders to keep buy and sell orders close to the market price (“liquidity rewards”). This page asks two questions: do rewards make markets easier to trade, and do they make prices more accurate? Sections 1–2 describe all of Kalshi’s programs; the analyses in sections 3–5 leave out sports and crypto markets.');

  // 1 ── data
  sectionHead(main, '1. Data');
  const d1 = card('Sources', null, null, 'card wide');
  d1.append(simpleTable([{ key: 0, label: 'Source' }, { key: 1, label: 'What it contains' }, { key: 2, label: 'Coverage' }, { key: 3, label: 'Used for' }], [
    ['Reward programs (Kalshi API)', 'One row per program: the market, type (liquidity or volume reward), start and end time, dollars posted', `${fi(T.programs)} programs on ${fi(T.markets)} markets, ${T.first} – ${T.last}, ${usd(T.usd)} posted (all categories)`, 'Which markets were rewarded, and from when'],
    ['Daily market data (Kalshi archive)', 'Each market on each day it had any activity: best bid and ask at the close, median bid–ask spread, share of hourly snapshots with quotes on both sides, contracts traded, last trade price. A day without a row had no trade.', 'Markets still open on 14 Jul 2026 or later (plus about 4,000 that closed earlier in 2026), from the day they opened', 'The outcomes below'],
    ['Market list (Kalshi archive)', 'Series and event, open and close dates, final result (yes or no)', 'The same markets', 'Grouping markets; scoring accuracy'],
  ]));
  d1.append(h('p', { class: 'note' }, 'Liquidity rewards pay for resting orders near the best price; volume rewards pay for trading. Not in the data: who earned the rewards, how much each trader got, and how much was actually paid out.'));
  const d2 = card('Measures', null, null, 'card wide');
  d2.append(simpleTable([{ key: 0, label: 'Measure' }, { key: 1, label: 'Definition' }], [
    ['Spread', 'Median gap between the best sell and buy price that day, in cents (days with quotes on both sides)'],
    ['Two-sided quotes', 'Share of that day’s hourly snapshots with both a buy and a sell order'],
    ['Traded', 'Whether the market had at least one trade that day (every calendar day the market was open counts)'],
    ['Brier score', '(price − outcome)², with outcome = 1 if the market resolved yes; 0 is perfect, lower is better (settled markets only)'],
    ['Price moving toward the outcome', 'How much that day’s price change reduced the squared gap to the final outcome: (yesterday’s price − outcome)² − (today’s price − outcome)². Positive = the price moved toward the answer (settled markets only)'],
  ]));
  main.append(h('div', { class: 'grid' }, d1, d2));

  // 2 ── the programs
  const PK = Object.fromEntries((S.program_kinds || []).map(r => [r.kind, r]));
  sectionHead(main, '2. Kalshi’s reward programs', 'Each program puts a fixed dollar amount on one market for a set period. Kalshi runs five kinds.');
  const p1 = card('How a liquidity reward pays out', 'From Kalshi’s help center.', null, 'card wide');
  p1.append(h('ol', { class: 'plain' },
    h('li', {}, 'Kalshi sets a dollar pool for one market over a period (its rules allow up to 31 days), plus a target size (how many contracts must be resting on each side) and a discount factor.'),
    h('li', {}, 'Once a second, Kalshi takes a snapshot of the order book. Traders with resting buy or sell orders near the best price earn points: more for bigger orders, fewer for each cent further from the best price (the discount factor sets how many fewer). A snapshot counts only if resting orders reach the target size on both the yes and the no side.'),
    h('li', {}, 'At the end of the period, the pool is split in proportion to points. Orders earn points whether or not they are ever filled.')));
  p1.append(h('p', { class: 'note' }, 'Volume rewards are different: they pay for contracts traded, not for orders resting in the book.'));
  main.append(h('div', { class: 'grid' }, p1));
  if (PK.standard) {
    const dur = hr => hr < 1 ? 'under 1 hour' : hr < 24 ? `${Math.round(hr)} hour${Math.round(hr) === 1 ? '' : 's'}` : `${(hr / 24).toFixed(1)} days`;
    const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const day = s => MON[+s.slice(5, 7) - 1] + ' ' + s.slice(0, 4);
    const P = [
      ['long_dated', 'Long-dated liquidity', 'long_dated', r => `For markets far from closing: started a median ${Math.round(r.median_days_since_open)} days after the market opened, with ${Math.round(r.median_days_to_close)} days left (${pct(r.share_over_180d_left)} had more than 180 days left).`],
      ['standard', 'Standard liquidity', 'no label', r => `The original program, set market by market at any point in a market’s life (a median ${Math.round(r.median_days_since_open)} days after it opened, ${Math.round(r.median_days_to_close)} days before it closed).`],
      ['new_event', 'New-event liquidity', 'new_event', r => `Starts when a new market is listed (${pct(r.share_starting_at_open)} start in its first hour), to get quotes into it from day one. One per market.`],
      ['series_lip', 'Series liquidity', 'series_lip', r => `Covers all markets of a recurring series, such as daily or hourly questions. Most of these markets close within a day of the start (${pct(r.share_closing_within_1d)}), so programs are short.`],
      ['volume', 'Volume reward', 'type volume', () => 'Pays for contracts traded rather than for resting orders. Not part of the comparisons below.'],
    ].filter(([k]) => PK[k]);
    const p2 = card('The five kinds of program', 'All programs, all categories. Medians are per program.', null, 'card wide');
    p2.append(simpleTable([{ key: 0, label: 'Program' }, { key: 1, label: 'What it is' }, { key: 2, label: 'Ran' }, { key: 3, label: 'Programs', num: true }, { key: 4, label: 'Markets', num: true }, { key: 5, label: 'Dollars posted', num: true }, { key: 6, label: 'Median $', num: true }, { key: 7, label: 'Median length', num: true }],
      P.map(([k, name, lab, what]) => { const r = PK[k]; return [h('span', {}, h('b', {}, name), h('br'), h('span', { class: 'muted small' }, lab)), what(r), `${day(r.first_start)} – ${day(r.last_start)}`, fi(r.programs), fi(r.markets), usd(r.usd), '$' + fi(r.median_usd), dur(r.median_hours)]; })));
    p2.append(h('p', { class: 'note' }, `Kalshi’s data gives each program a label (shown under its name) but Kalshi does not publish what the four liquidity labels mean; the descriptions come from when and on which markets each kind runs. “Ran” is the first and last start date. The timing figures use only programs whose market is in our market list, which lacks most markets that closed before mid-July 2026: ${P.map(([k, name]) => `${pct(PK[k].matched_share)} of ${name.toLowerCase()}`).join(', ')} programs.`),
      h('p', { class: 'note' }, h('b', {}, 'In the comparisons below: '), '“long-dated reward” is the first row; “other liquidity reward” is the next three rows together.'));
    main.append(h('div', { class: 'grid', style: 'margin-top:16px' }, p2));
    const RM = S.reward_months, ORDER = ['Long-dated liquidity', 'Standard liquidity', 'New-event liquidity', 'Series liquidity', 'Volume reward'];
    const p3 = card('Dollars posted per month, by program', 'All categories, by the month the program started.', null, 'card wide');
    C.vbar(p3, RM.months.map(m => MON[+m.slice(5, 7) - 1] + ' ' + m.slice(2, 4)), ORDER.filter(k => RM.series[k]).map((k, i) => ({ name: k, values: RM.series[k] })), { stacked: true, fmtV: v => usd(v), H: 230, W: 900 });
    p3.append(h('p', { class: 'note' }, 'Until April 2026 the money went to standard and volume programs. New-event and long-dated programs began at the end of April (long-dated ran only until early July), and series programs in late July.'));
    main.append(h('div', { class: 'grid', style: 'margin-top:16px' }, p3));
  }

  // 3 ── who gets rewarded
  sectionHead(main, '3. Which markets get rewards', 'Markets in our market list (still open on 14 Jul 2026 or later); sports and crypto left out.');
  const R = S.reward_coverage, sh = hz => R.find(r => r.hz === hz);
  const c1 = card('Share of markets ever given a liquidity reward', 'By how far ahead of its close the market was listed.');
  C.vbar(c1, R.map(r => SHORT[r.hz]), R.map(r => r.share_liquidity_reward), { fmtV: v => pct(v), H: 210 });
  c1.append(h('p', { class: 'note' }, `Most longer markets get a reward at some point (${pct(sh('3-6m').share_liquidity_reward)} of those listed 3–6 months ahead, ${pct(sh('1-2y').share_liquidity_reward)} of those 1–2 years ahead), against ${pct(sh('<1d').share_liquidity_reward)} of markets open under a day.`));
  const c2 = card('Reward dollars per 1,000 contracts traded', 'Dollars posted, divided by contracts traded, by listing horizon.');
  C.vbar(c2, R.map(r => SHORT[r.hz]), R.map(r => r.reward_usd_per_1k_contracts), { fmtV: v => '$' + f2(v), H: 210 });
  c2.append(h('p', { class: 'note' }, 'Markets listed weeks to months ahead get the most subsidy per unit of trading.'));
  main.append(grid(c1, c2));
  const RC = (S.reward_cov_cat || []).filter(r => r.markets >= 500);
  if (RC.length) {
    const lab = r => `${r.category} (${fi(r.markets)})`, by = k => [...RC].sort((a, b) => b[k] - a[k]);
    const cat = n => RC.find(r => r.category === n), rare = ['Commodities', 'Financials', 'Climate and Weather'].map(cat).filter(Boolean).map(r => r.share_liquidity_reward);
    const c4 = card('Share of markets ever given a liquidity reward, by category', 'Number of markets in brackets; categories with at least 500 markets.');
    C.hbar(c4, by('share_liquidity_reward').map(r => ({ label: lab(r), value: r.share_liquidity_reward })), { W: 480, labelW: 210, labelChars: 34, fmtV: v => pct(v) });
    c4.append(h('p', { class: 'note' }, `Commodities, financials and weather, mostly short daily price and temperature brackets, are rarely rewarded (${pct(Math.min(...rare))}–${pct(Math.max(...rare))}). Most economics, politics, company and election markets are.`));
    const top = by('reward_usd_per_1k_contracts'), dol = by('share_of_reward_usd');
    const c5 = card('Reward dollars per 1,000 contracts traded, by category', 'Dollars posted, divided by contracts traded.');
    C.hbar(c5, top.map(r => ({ label: lab(r), value: r.reward_usd_per_1k_contracts })), { W: 480, labelW: 210, labelChars: 34, fmtV: v => '$' + f2(v) });
    c5.append(h('p', { class: 'note' }, `${top[0].category} and ${top[1].category.toLowerCase()} get the most per contract traded. In total dollars, ${dol[0].category.toLowerCase()} and ${dol[1].category.toLowerCase()} get the most (${pct(dol[0].share_of_reward_usd)} and ${pct(dol[1].share_of_reward_usd)} of all reward dollars here).`));
    main.append(h('div', { class: 'grid', style: 'margin-top:16px' }, c4, c5));
  }
  const O = S.orderbook_focus;
  const c3 = card('Long markets are quoted, but rarely traded', `Open economics, finance and tech markets on ${S.open_snapshot.time.slice(0, 10)}, by time left until they close (one snapshot of the order book).`, null, 'card wide');
  c3.append(simpleTable([{ key: 'label', label: 'Time left' }, { key: 'markets', label: 'Markets', num: true, render: r => fi(r.markets) }, { key: 'two_sided', label: 'Have buy and sell quotes', num: true, render: r => pct(r.two_sided) }, { key: 'spread_med', label: 'Median spread', num: true, render: r => cents(r.spread_med) }, { key: 'traded_24h', label: 'Traded in last 24h', num: true, render: r => pct(r.traded_24h) }], O));
  main.append(h('div', { class: 'grid', style: 'margin-top:16px' }, c3));

  // 4 ── comparison A: reward days vs other days
  const E = Object.fromEntries([...S.reward_effects, ...S.info_effects.filter(r => r.outcome === 'info_gain')].map(r => [r.outcome + '|' + r.reward, r]));
  sectionHead(main, '4. First comparison: the same market on reward days vs its other days', `${fi(S.samples.panel.markets)} markets listed at least 60 days before their close, open between 15 Mar and 31 Aug 2026, that traded at least once (${fi(S.samples.panel.market_days)} market-days; each market’s last two days dropped). Each market is compared with itself, so differences between markets drop out.`);
  const a1 = card('Method', null, null, 'card wide');
  a1.append(
    h('div', { class: 'formula' }, tex(String.raw`\text{Outcome}_{m,d} = \beta_1\,\text{LongDated}_{m,d} + \beta_2\,\text{OtherReward}_{m,d} + \textstyle\sum_b \gamma_b\,\mathbf{1}[\text{DaysToClose}_{m,d} \in b] + \alpha_m + \delta_d + \varepsilon_{m,d}`, true)),
    h('ul', { class: 'plain' },
      h('li', {}, tex(String.raw`\text{LongDated}_{m,d}`), ', ', tex(String.raw`\text{OtherReward}_{m,d}`), ': 1 if market ', tex('m'), ' had that kind of liquidity reward running on day ', tex('d'), ' (Kalshi’s long-dated program, or any other liquidity reward)'),
      h('li', {}, tex(String.raw`\alpha_m`), ': a constant per market; ', tex(String.raw`\delta_d`), ': a constant per calendar day (news that hits all markets); ', tex(String.raw`\gamma_b`), ': a constant per bin of days left (0–7, 7–30, 30–90, 90–180, 180–365, 365+)'),
      h('li', {}, 'Least squares; standard errors clustered by series.')));
  const fr = (v, k) => S.fresh.find(r => r.variant.startsWith(v) && r.reward === k);
  const TR = { rw_long_dated: fr('trade price', 'rw_long_dated'), rw_liquidity: fr('trade price', 'rw_liquidity') };
  const effc = (r, scale, unit, d) => {
    if (!r) return '–';
    const p = pval(r.t);
    return h('span', {}, h('span', { class: p < 0.05 ? 'sig' : '' }, num(r.coef * scale, d) + unit + stars(p)), h('br'), h('span', { class: 'muted small' }, `SE ${(r.se * scale).toFixed(d)}${unit}, p ${p < 0.001 ? '< 0.001' : p.toFixed(3)}`));
  };
  const OUT = [
    ['Spread', k => E['spread_med|' + k], r => cents(r.mean_y), 100, '¢', 1],
    ['Two-sided quotes', k => E['two_sided_share|' + k], r => pct(r.mean_y), 100, ' pts', 1],
    ['Traded', k => E['traded|' + k], r => pct(r.mean_y), 100, ' pts', 1],
    [`Price moving toward the outcome, price = midpoint, else last trade (${fi(S.samples.settled_panel.markets)} settled markets)`, k => E['info_gain|' + k], r => r.mean_y.toFixed(4), 1, '', 4],
    [`Price moving toward the outcome, trade prices only (${fi(TR.rw_long_dated.markets)} settled markets)`, k => TR[k], r => r.mean_y.toFixed(4), 1, '', 4],
  ];
  const a2 = card('Results: change on reward days', 'Compared with the same market’s days without a reward.', null, 'card wide');
  a2.append(simpleTable([{ key: 0, label: 'Measure' }, { key: 1, label: 'Average over all market-days', num: true, tip: 'The plain average of the measure over every market-day in the sample, reward days included. Shown only for scale; it is not estimated by the regression.' }, { key: 2, label: h('span', {}, tex(String.raw`\beta_1`), ' (long-dated reward)'), num: true }, { key: 3, label: h('span', {}, tex(String.raw`\beta_2`), ' (other liquidity reward)'), num: true }],
    OUT.map(([lab, get, base, scale, unit, d]) => [lab, get('rw_long_dated') ? base(get('rw_long_dated')) : '–', effc(get('rw_long_dated'), scale, unit, d), effc(get('rw_liquidity'), scale, unit, d)])));
  a2.append(
    h('p', { class: 'note' }, 'Each β cell: the estimate, then its standard error (SE) and p-value. Stars: * p < 0.05, ** p < 0.01, *** p < 0.001; bold = significant at 5%.'),
    h('p', { class: 'note' }, 'Reading: on reward days spreads are much tighter, quotes on both sides are more common, and many more markets trade.'),
    h('p', { class: 'note' }, `Why “price moving toward the outcome” has two rows: the first row takes the midpoint between the best buy and sell order as the day’s price. Rewards narrow the spread, and a narrower spread by itself moves the midpoint closer to where the market really is. That can look like the price learning about the outcome when nobody learned anything. The second row uses only actual trade prices, on days when the market traded both that day and the day before, so a narrower spread cannot move the price by itself. With trade prices, the long-dated reward’s effect is about zero (p ${pval(TR.rw_long_dated.t).toFixed(2)}), so its effect in the first row was likely just the tighter spread. Other liquidity rewards still show prices moving toward the outcome (p ${pval(TR.rw_liquidity.t).toFixed(2)}).`),
    h('p', { class: 'note' }, 'Limitation: Kalshi decides when rewards run, possibly when markets are about to get busy, so the next comparison adds a control group.'));
  main.append(h('div', { class: 'grid', style: 'margin-top:4px' }, a1, a2));

  // 5 ── comparison B: before vs after the first reward, against never-rewarded markets
  const RE = (S.reward_es || []).filter(r => r.sample === 'all' && r.term), M = S.reward_es_meta || {};
  if (RE.length) {
    const get = (y, term) => RE.find(r => r.outcome === y && r.term === term);
    const nStacks = Math.max(...RE.map(r => r.stacks || 0)), nCtrl = Math.max(...RE.map(r => r.control_markets || 0));
    const bp = get('brier', 'post'), nSettled = bp.stacks;
    const pfmt = p => p < 0.001 ? '< 0.001' : p.toFixed(3);
    sectionHead(main, '5. Second comparison: after a market’s first reward, against similar markets with no reward');
    const g1 = card('Why and how', null, null, 'card wide');
    g1.append(
      h('p', {}, 'Section 4 has a weakness: Kalshi chooses when to reward a market, possibly right before the market would have improved anyway. So here we ask: after a market’s first reward, does it improve more than similar markets that got no reward in the same weeks?'),
      h('ol', { class: 'plain' },
        h('li', {}, h('b', {}, 'Rewarded markets. '), `The market’s first reward was a liquidity reward, starting between Oct 2025 and Sep 2026. The market had been listed for at least 14 days before it and had at least 7 days left. ${fi(nStacks)} markets${M.treated_candidates ? ` (of ${fi(M.treated_candidates)} that qualify; the rest have no control)` : ''}.`),
        h('li', {}, h('b', {}, 'Controls. '), `For each rewarded market, up to 10 markets from the same series (the same recurring question, e.g. other CPI months or thresholds) that never had a reward and were trading at the same time. We pick those whose price in weeks −4 to −2 was about as far from 50¢ as the rewarded market’s, so both start out about equally uncertain. ${fi(nCtrl)} control markets in total.`),
        h('li', {}, h('b', {}, 'Window. '), 'From 4 weeks before the first reward day to 8 weeks after; week 0 is the first week of the reward. Every calendar day counts (a day with no activity counts as a day without a trade). Each market’s last day is dropped.'),
        h('li', {}, h('b', {}, 'Comparison. '), 'Each week, the gap between the rewarded market and its controls, minus that gap in week −1. News that affects both cancels out.')));
    main.append(h('div', { class: 'grid' }, g1));

    const X = S.reward_es_example;
    if (X) {
      const T = X.treated, MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const dt = s => `${+s.slice(8, 10)} ${MON[+s.slice(5, 7) - 1]} ${s.slice(0, 4)}`;
      const dig = y => y === 'spread' ? 1 : 4, unit = y => y === 'spread' ? '¢' : '';
      const BA = y => {
        const r = X[y].before_after.rewarded, c = X[y].before_after.controls, f = v => v.toFixed(dig(y)) + unit(y), ch = v => num(v, dig(y)) + unit(y);
        return [['Rewarded market', f(r[0]), f(r[1]), ch(r[1] - r[0])], ['Controls (average)', f(c[0]), f(c[1]), ch(c[1] - c[0])],
          [h('b', {}, 'Difference = effect of the reward'), '', '', h('b', {}, ch((r[1] - r[0]) - (c[1] - c[0])))]];
      };
      const exTable = (y, label) => simpleTable([{ key: 0, label }, { key: 1, label: '4 weeks before', num: true }, { key: 2, label: '8 weeks after', num: true }, { key: 3, label: 'Change', num: true }], BA(y));
      const exChart = (y, title, fmtV) => {
        const c = card(title, 'Weekly average; week 0 = first reward week.');
        C.line(c, X[y].weeks.map(w => (w > 0 ? '+' : '') + w), [{ name: 'Rewarded market', values: X[y].rewarded }, { name: 'Controls (average)', values: X[y].controls }], { fmtV, fmtX: x => 'week ' + x, H: 170 });
        return c;
      };
      const sp = X.spread.before_after, move = (a, b) => Math.abs(b - a) < 0.05 ? 'barely changed' : `${b > a ? 'widened' : 'narrowed'} by ${Math.abs(b - a).toFixed(1)}¢`;
      const ex1 = card(`A real example: ${T.title}`, null, null, 'card wide');
      ex1.append(
        h('p', {}, h('b', {}, 'Rewarded market: '), `“${T.title}” Its first reward started on ${dt(T.t0)}, and Kalshi posted ${usd(T.reward_usd)} in rewards on it over the next 8 weeks. It resolved ${T.result} on ${dt(T.close)}.`),
        h('p', {}, h('b', {}, 'Controls: '), `${X.controls.length} markets from the same series that never had a reward and were trading at the same time:`),
        h('ul', { class: 'plain' }, X.controls.map(c => h('li', {}, `“${c.event}”: ${c.sub} (resolved ${c.result})`))),
        h('div', { class: 'grid', style: 'margin-top:8px' }, h('div', { style: 'min-width:0' }, exTable('spread', 'Spread')), h('div', { style: 'min-width:0' }, exTable('brier', 'Brier score'))),
        h('p', { class: 'note' }, `Reading: over the same weeks the controls’ spreads ${move(sp.controls[0], sp.controls[1])} and the rewarded market’s ${move(sp.rewarded[0], sp.rewarded[1])}, so the reward’s effect on its spread is ${num(X.change.spread, 1)}¢; its effect on the Brier score is ${num(X.change.brier, 4)}. The full analysis does this for all ${fi(nStacks)} rewarded markets at once, week by week.`),
        h('p', { class: 'note' }, `How this example was picked: ${X.candidates} rewarded markets have spreads on most days and at least 3 settled controls; ${X.eligible} of them also have controls with a similar starting price and a steady spread before the reward. This is the one whose changes are closest to the median of those ${X.eligible} (spread ${num(X.median_change.spread, 1)}¢, Brier ${num(X.median_change.brier, 4)}). Most rewarded markets look like this: their Brier score barely moves. The average Brier change (${num(X.mean_change.brier, 3)}) is pulled by a few markets that started far from the outcome.`));
      main.append(h('div', { class: 'grid', style: 'margin-top:16px' }, ex1));
      main.append(h('div', { class: 'grid', style: 'margin-top:16px' }, exChart('spread', 'Example: spread', v => v.toFixed(1) + '¢'), exChart('brier', 'Example: Brier score', v => v.toFixed(3))));
    }

    const g3 = card('How to read the charts');
    g3.append(h('ul', { class: 'plain' },
      h('li', {}, 'Week −1 is 0 by design.'),
      h('li', {}, 'Weeks −4 to −2 near 0: the two groups moved together before the reward, so the controls are a fair comparison.'),
      h('li', {}, 'From week 0 on, the distance from 0 is the effect of the reward.'),
      h('li', {}, 'The shaded band is the 95% confidence range. Where it does not cover 0, the effect is significant.')));
    const g4 = card('The regression behind the charts');
    g4.append(h('div', { class: 'formula' }, tex(String.raw`y_{m,d} = \textstyle\sum_{w \neq -1} \delta_w \,\text{Rewarded}_m\,\mathbf{1}[\text{week}(d) = w] + \alpha_{m} + \gamma_{d} + \varepsilon_{m,d}`, true)),
      h('ul', { class: 'plain' },
        h('li', {}, tex('y_{m,d}'), ': the measure for market ', tex('m'), ' on day ', tex('d'), '; ', tex(String.raw`\text{Rewarded}_m`), ' = 1 for the rewarded market, 0 for its controls'),
        h('li', {}, tex(String.raw`\delta_w`), ': the effect in week ', tex('w'), ' (the points in the charts)'),
        h('li', {}, tex(String.raw`\alpha_m`), ': a constant per market; ', tex(String.raw`\gamma_d`), ': a constant per calendar day'),
        h('li', {}, 'Each rewarded market and its controls form one group, with α and γ estimated within the group (a “stacked event study”). Standard errors clustered by series. The 8-week average replaces the weekly terms with one after-reward term, compared with all 4 weeks before.')));
    main.append(h('div', { class: 'grid', style: 'margin-top:16px' }, g3, g4));

    const WK = [-4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7];
    const weekRows = rows => w => w === -1 ? { coef: 0, se: 0 } : rows.find(r => r.term === `w${w}`);
    const preAvg = rows => ['w-4', 'w-3', 'w-2'].map(t => rows.find(r => r.term === t).coef).reduce((a, b) => a + b, 0) / 3;
    const band = at => ({ lo: WK.map(w => at(w) ? at(w).coef - 1.96 * at(w).se : null), hi: WK.map(w => at(w) ? at(w).coef + 1.96 * at(w).se : null) });
    const avgLine = (r, fmtV, what = 'compared with the 4 weeks before') => { const p = pval(r.t); return h('p', { class: 'note' }, h('b', {}, 'Average over the 8 weeks after: '), `${(r.coef > 0 ? '+' : '') + fmtV(r.coef)}${stars(p)}, ${what} (SE ${fmtV(r.se)}, p ${pfmt(p)}; ${fi(r.stacks)} rewarded markets).`); };
    const esCard = (y, title, sub, fmtV, note) => {
      const rows = RE.filter(r => r.outcome === y), at = weekRows(rows), c = card(title, sub);
      C.line(c, WK.map(w => (w > 0 ? '+' : '') + w), [{ name: 'rewarded minus controls', values: WK.map(w => at(w) ? at(w).coef : null) }], { fmtV, fmtX: x => 'week ' + x, H: 190, band: band(at) });
      c.append(h('p', { class: 'note' }, note(rows, w => rows.find(r => r.term === `w${w}`))));
      const post = rows.find(r => r.term === 'post');
      if (post) c.append(avgLine(post, fmtV));
      return c;
    };
    const bPre = bp.mean_treated_pre, bPreC = bp.mean_control_pre;
    main.append(h('div', { class: 'grid', style: 'margin-top:16px' },
      esCard('spread', 'Spread', 'Rewarded minus controls, in cents. Below 0 = narrower spread.', v => v.toFixed(1) + '¢',
        (rows, w) => { const pe = get('spread', 'post_ex_w-1'); return `In the first week, spreads fall ${Math.abs(w(0).coef).toFixed(1)}¢ more than the controls’, and are still ${Math.abs(w(7).coef).toFixed(1)}¢ lower in week 7. Week −1 was unusually wide (weeks −4 to −2 sit about ${Math.abs(preAvg(rows)).toFixed(1)}¢ below it). Measured from weeks −4 to −2 only, the first-week drop is ${Math.abs(w(0).coef - preAvg(rows)).toFixed(1)}¢ and the 8-week average ${Math.abs(pe.coef).toFixed(1)}¢ (SE ${pe.se.toFixed(1)}¢).`; }),
      esCard('traded', 'Traded', 'Rewarded minus controls, percentage points. Above 0 = more likely to trade on a given day.', v => (v * 100).toFixed(1) + ' pts',
        (rows, w) => `In the first week, rewarded markets are ${(w(0).coef * 100).toFixed(0)} points more likely to trade on a given day; by week 2 the gap is down to ${(w(2).coef * 100).toFixed(0)} points.`),
      esCard('brier', 'Brier score', `Rewarded minus controls. Below 0 = more accurate price. Only the ${fi(nSettled)} rewarded markets that have settled.`, v => v.toFixed(3),
        (rows, w) => `Flat before the reward, then falling to about ${Math.min(...[0, 1, 2, 3, 4, 5, 6, 7].map(k => w(k).coef)).toFixed(3)} by week 7. Caution: rewarded markets start out much less certain than their controls (average Brier ${bPre.toFixed(3)} vs ${bPreC.toFixed(3)} before the reward), and uncertain markets have more room to improve as the outcome nears. The check below looks at this.`)));

    const U = S.reward_es_uncertain || [], uR = U.filter(r => r.version === 'uncertain'), uP = U.filter(r => r.version === 'placebo_uncertain');
    if (uR.length && uP.length) {
      const atR = weekRows(uR), atP = weekRows(uP), postR = uR.find(r => r.term === 'post'), postP = uP.find(r => r.term === 'post');
      const fmtB = v => v.toFixed(3), u1 = card('Check: do uncertain markets get more accurate anyway?', 'Only markets that start out uncertain: average Brier score of at least 0.05 in weeks −4 to −2.', null, 'card wide');
      u1.append(h('ul', { class: 'plain', style: 'margin-bottom:18px' },
        h('li', {}, h('b', {}, 'Y-axis: '), 'Brier score minus the controls’ Brier score, relative to week −1. Below 0 = became more accurate than the controls.'),
        h('li', {}, h('b', {}, 'Solid line: '), `real rewarded markets against their never-rewarded controls (${fi(postR.stacks)} markets). Shaded band = 95% range.`),
        h('li', {}, h('b', {}, 'Dashed line: '), `never-rewarded markets given a fake reward date, taken from a real one in their series, against other never-rewarded markets (${fi(postP.stacks)} markets). Nothing happened to them, so any drop is improvement that would happen anyway.`)));
      C.line(u1, WK.map(w => (w > 0 ? '+' : '') + w), [{ name: 'Real rewards', values: WK.map(w => atR(w) ? atR(w).coef : null) }, { name: 'Fake reward dates', values: WK.map(w => atP(w) ? atP(w).coef : null), dash: '5 4' }],
        { fmtV: fmtB, fmtX: x => 'week ' + x, H: 210, W: 900, band: band(atR), ylabel: 'Brier gap vs controls' });
      const pp = pval(postP.t), pr = pval(postR.t);
      u1.append(h('p', { class: 'note' }, `Reading: with real rewards, Brier falls ${Math.abs(postR.coef).toFixed(3)} more than the controls’ over 8 weeks (p ${pfmt(pr)}), starting in week 0. With fake dates the average is ${num(postP.coef, 3)} (p ${pfmt(pp)}): flat at first, but falling too from week 3, and by week 7 the two lines meet (${num(atR(7).coef, 3)} real, ${num(atP(7).coef, 3)} fake). So the early drop looks like a reward effect; the later drop is likely uncertain markets moving toward the answer anyway.`));
      main.append(h('div', { class: 'grid', style: 'margin-top:16px' }, u1));
    }

    const V = S.reward_es_versions || [];
    const VER = [
      ['price_ffill', 'Main version', 'Same-series controls with a similar distance from 50¢ (the charts above)', 'the main version'],
      ['random', 'How controls are picked', 'At random', 'random controls'],
      ['series_matched', 'How controls are picked', 'Most similar trading volume', 'volume-matched controls'],
      ['brier_matched', 'How controls are picked', 'Most similar starting Brier score', 'Brier-matched controls'],
      ['event_price', 'Where controls come from', 'Same event only (other thresholds of the same question)', 'same-event controls'],
      ['event_matched', 'Where controls come from', 'Same event only, most similar trading volume', 'same-event volume-matched controls'],
      ['mid', 'Which days get a Brier score', 'Only days with quotes on both sides (midpoint price)', 'two-sided days only'],
      ['pre56', 'Length of the before-period', '8 weeks instead of 4', 'the 8-week before-period'],
      ['uncertain', 'Only markets that start out uncertain', 'Real rewards', 'uncertain markets'],
      ['placebo_uncertain', 'Only markets that start out uncertain', 'Fake reward dates on never-rewarded markets', ''],
      ['placebo', 'Placebo check', 'Never-rewarded markets given fake reward dates (should show nothing)', ''],
    ].filter(([k]) => V.some(r => r.version === k));
    const vv = (ver, o) => V.find(r => r.version === ver && r.outcome === o && r.term === 'post');
    const vcell = (ver, o, f) => { const r = vv(ver, o); if (!r || r.coef == null) return '–'; const p = pval(r.t); return h('span', {}, h('span', { class: p < 0.05 ? 'sig' : '' }, f(r.coef) + stars(p)), h('br'), h('span', { class: 'muted small' }, `SE ${f(r.se).replace(/^\+/, '')}`)); };
    const b2 = card('Does the answer depend on choices we made?', 'Each row changes one thing from the main version and reruns the comparison. Cells: the average effect over the 8 weeks after. Bold = significant at 5% (* p < 0.05, ** p < 0.01, *** p < 0.001).', null, 'card wide');
    b2.append(simpleTable([{ key: 0, label: 'What changes' }, { key: 1, label: 'Version' }, { key: 2, label: 'Spread', num: true }, { key: 3, label: 'Traded', num: true }, { key: 4, label: 'Brier', num: true }],
      VER.map(([k, choice, what], i) => [i > 0 && VER[i - 1][1] === choice ? '' : h('b', {}, choice), what, vcell(k, 'spread', v => num(v, 1) + '¢'), vcell(k, 'traded', v => num(v * 100, 1) + ' pts'), vcell(k, 'brier', v => num(v, 3))])));
    const real = VER.filter(([k]) => !k.startsWith('placebo') && k !== 'uncertain').map(([k]) => vv(k, 'brier')).filter(Boolean);
    const nsig = real.filter(r => pval(r.t) < 0.05).length;
    b2.append(h('p', { class: 'note' }, `Reading: narrower spreads and more trading appear in every version. Same-event controls halve the spread effect, probably because traders chasing a reward also quote the neighbouring thresholds. The Brier effect is similar in every version (${Math.max(...real.map(r => r.coef)).toFixed(3)} to ${Math.min(...real.map(r => r.coef)).toFixed(3)}; significant in ${nsig} of ${real.length}), but see the check above: matching on the starting Brier score does not remove the gap in certainty, because almost all available controls are near-certain. The plain placebo shows nothing, as it should.`));
    main.append(h('div', { class: 'grid', style: 'margin-top:16px' }, b2));

    // 6 ── summary
    const sp0 = get('spread', 'w0'), spPre = preAvg(RE.filter(r => r.outcome === 'spread')), spPost = get('spread', 'post'), spEx = get('spread', 'post_ex_w-1'), tr0 = get('traded', 'w0'), tr2 = get('traded', 'w2');
    const pl = vv('placebo', 'brier'), uR6 = vv('uncertain', 'brier'), uP6 = vv('placebo_uncertain', 'brier');
    const long = (S.reward_es || []).find(r => r.sample === '> 180 days left' && r.outcome === 'brier' && r.term === 'post');
    const cost = M.reward_usd_settled;
    sectionHead(main, '6. What this shows');
    const s1 = card('Summary', null, null, 'card wide');
    s1.append(h('ul', { class: 'plain' },
      h('li', {}, `Rewards make markets easier to trade. In the first week after a market’s first reward, its spread falls ${Math.abs(sp0.coef - spPre).toFixed(1)}–${Math.abs(sp0.coef).toFixed(1)}¢ more than in comparable never-rewarded markets, and ${Math.min(Math.abs(spEx.coef), Math.abs(spPost.coef)).toFixed(1)}–${Math.max(Math.abs(spEx.coef), Math.abs(spPost.coef)).toFixed(1)}¢ on average over 8 weeks (the range depends on which weeks before the reward it is measured from). It is ${(tr0.coef * 100).toFixed(0)} percentage points more likely to trade in the first week, falling to ${(tr2.coef * 100).toFixed(0)} points by week 2. This holds in every version, and the placebo shows nothing.`),
      h('li', {}, `Accuracy: on average, rewarded markets’ Brier score falls ${Math.abs(bp.coef).toFixed(3)} more than their controls’ over 8 weeks (p ${pfmt(pval(bp.t))}). But the gain comes mostly from a few markets that started far from the outcome, and rewarded markets start out much less certain than their controls. Among markets that start out uncertain, those with fake reward dates also improve later on (${uP6 ? num(uP6.coef, 3) : '–'} vs ${uR6 ? num(uR6.coef, 3) : '–'} with real rewards). So we cannot yet separate a reward effect on accuracy from uncertain markets converging toward the answer.`),
      cost ? h('li', {}, `Cost: Kalshi posted about ${usd(cost.mean)} per rewarded market (median ${usd(cost.median)}) in programs that started in the 8 weeks after the first reward, for the ${fi(cost.markets)} settled markets behind the Brier estimate. Even if the whole Brier gain were due to the reward, that is about ${usd(cost.mean / (Math.abs(bp.coef) * 100))} per market per 0.01 of Brier improvement (dollars posted, not paid).`) : null,
      h('li', {}, `Long horizons: only ${long ? fi(long.stacks) : 'a few'} of the ${fi(nSettled)} settled rewarded markets had more than 6 months left when the reward started, too few to say anything about long-horizon markets.`)));
    main.append(h('div', { class: 'grid' }, s1));
  }
}

// ------------------------------------------------------------------ What we have
function pageCoverage(main) {
  if (isPM()) return pageCoveragePM(main);
  pageHead(main, 'What data we have, in plain terms', 'A quick guide to what the Kalshi data can and can’t show. The analyses leave out sports and crypto markets. The Data tab has the technical details.');
  const c1 = card('What we have', null, null, 'card wide'); const g = h('div', { class: 'grid' }, c1); main.append(g);
  c1.append(simpleTable([{ key: 0, label: 'Data' }, { key: 1, label: 'What it tells us' }, { key: 2, label: 'How far back' }, { key: 3, label: 'Have it?', render: r => h('span', { class: 'have' }, r[3]) }], [
    ['List of markets', 'Each market’s question, open and close dates, outcome, and total amount traded over its life', 'Markets still open on 14 Jul 2026 or later (plus about 4,000 that closed earlier in 2026)', '⚠ Recent markets only'],
    ['Hourly price history', 'For every hour: the price, the best buy and sell offers, how much traded, and how many contracts people held', 'From the day each market opened (as early as mid-2023)', '✓ Yes'],
    ['Individual trades', 'Every single trade: exact time, price, size, and whether the buyer took YES or NO', 'Only 15 Jul – 21 Sep 2026', '⚠ Only ~70 days'],
    ['Reward programs', 'Which markets Kalshi paid people to trade or quote in, when, and how much', 'Sep 2025 – Sep 2026', '✓ Yes'],
    ['Order book depth', 'How many contracts are waiting to be bought or sold at each price', 'Only one snapshot, 23 Sep 2026', '⚠ One day only'],
  ]));
  const c2 = card('What we don’t have', null, null, 'card wide'); g.append(c2);
  c2.append(simpleTable([{ key: 0, label: 'Missing' }, { key: 1, label: 'Why' }], [
    ['Order book history', 'Kalshi only shows the current book, not past ones'],
    ['Individual trades before mid-July 2026', 'Kalshi deletes trades after about 70 days'],
    ['Most markets that closed before mid-July 2026', 'The archive keeps only about 4,000 of them; it seems to cover markets still open when it started, like the trades'],
    ['Who traded', 'Kalshi never makes this public'],
    ['Anything after 21 Sep 2026', 'The download stopped then; it needs a catch-up run before late November'],
  ]));
  main.append(h('p', { class: 'summary' }, 'So for any market still open in mid-July 2026 or later, we can see its whole life hour by hour, just not trade by trade before mid-July.'));
}

// ------------------------------------------------------------------ Data
function pageData(main) {
  if (isPM()) return pageDataPM(main);
  const I = S.inventory, N = S.samples;
  pageHead(main, 'Data: counts and samples', 'How big each dataset is (all markets), and how many markets each analysis uses (sports and crypto left out). The What we have tab explains the data in plain terms.');
  const c1 = card('Datasets', null, null, 'card wide'); const g = h('div', { class: 'grid' }, c1); main.append(g);
  const TIP = {
    'Markets (non-combo)': ['One yes/no contract you can trade', 'e.g. “Will Q2 2026 GDP grow more than 4.0%?”', 'Each has open and close dates, an outcome, and total volume'],
    'Combo markets': ['Parlay-style bets: several outcomes bundled into one contract', 'Pays $1 only if every part happens', 'Mostly sports; the typical one is open about 7 hours'],
    'Events': ['One occurrence of a recurring question', 'e.g. the Q2 2026 GDP release', 'Usually holds several markets at different thresholds'],
    'Series': ['The recurring question itself', 'e.g. “US GDP growth”, every quarter', 'Holds many events over time'],
    'Price bars': ['An hourly snapshot of each market: traded price, best bid and ask, volume, open interest', 'Every minute instead for markets open 2 days or less', 'Kept locally as one row per market per day'],
    'Trades': ['Every individual trade: time, price, size, and which side the buyer took', 'Kalshi only keeps the last ~70 days'],
    'Reward programs': ['Money Kalshi posts to pay traders in a market over a set period', 'Liquidity rewards pay for keeping orders near the best price; volume rewards pay for trading'],
    'Open markets': ['Every market open on 23 Sep 2026, with its prices at that moment'],
    'Order books': ['All waiting buy and sell orders at each price, for one market at one moment', 'Taken once, on 23 Sep 2026'],
  };
  c1.append(simpleTable([{ key: 0, label: 'Dataset', render: r => h('span', { style: 'white-space:nowrap' }, r[0], TIP[r[0]] ? infoIcon(TIP[r[0]]) : null) }, { key: 1, label: 'n', num: true }, { key: 2, label: 'Breakdown' }, { key: 3, label: 'Dates' }, { key: 4, label: 'Source' }], [
    ['Markets (non-combo)', fi(I.markets), `${fi(I.markets_traded)} ever traded · ${fi(I.markets_settled)} settled · ${fi(I.markets_open)} open`, `${pct(I.markets_close_2026)} close in 2026`, 'archive'],
    ['Combo markets', fi(I.combos), 'left out of the analyses', '', 'archive'],
    ['Events', fi(I.events), '', '', 'archive'],
    ['Series', fi(I.series), '', '', 'archive'],
    ['Price bars', fi(I.bars), `${fi(I.bar_markets)} markets · ${fi(I.bar_days)} market-days`, `${I.bar_first} – ${I.bar_last}`, 'archive'],
    ['Trades', fi(I.trades), `${big(I.trade_contracts)} contracts`, `${I.trade_first} – ${I.trade_last}`, 'archive'],
    ['Reward programs', fi(S.reward_totals.programs), `${fi(S.reward_totals.markets)} markets · ${usd(S.reward_totals.usd)} posted`, `${S.reward_totals.first} – ${S.reward_totals.last}`, 'Kalshi API'],
    ['Open markets', fi(S.open_snapshot.markets), `${fi(S.open_snapshot.over_1y)} close more than a year out`, S.open_snapshot.time.slice(0, 10), 'Kalshi API'],
    ['Order books', fi(I.orderbooks), `${fi(I.orderbooks - 3000)} long-horizon econ/tech markets + 3,000 random others`, S.open_snapshot.time.slice(0, 10), 'Kalshi API'],
  ]));
  const ag = N.accuracy_group;
  const c2 = card('Samples used in each analysis', null, null, 'card wide'); g.append(c2);
  c2.append(simpleTable([{ key: 0, label: 'Tab' }, { key: 1, label: 'Analysis' }, { key: 2, label: 'Sample' }, { key: 3, label: 'Markets', num: true }, { key: 4, label: 'Observations', num: true }], [
    ['Horizons', 'Volume by listing horizon', 'Non-combo markets except sports and crypto', fi(N.horizon_markets), ''],
    ['Horizons', 'Trade tape by horizon', 'Non-combo markets that traded 15 Jul – 21 Sep', fi(N.trade_markets), fi(I.trades) + ' trades (all markets)'],
    ['Accuracy', 'Brier and AUC', 'Settled yes/no markets priced at every distance', `${fi(N.accuracy[90])} / ${fi(N.accuracy[180])} / ${fi(N.accuracy[365])}`, 'lived ≥ 90 / 180 / 365 days'],
    ['Accuracy', 'AUC by group', 'The lived-≥ 90-days sample', fi(N.accuracy[90]), Object.entries(ag).map(([k, v]) => `${k} ${fi(v)}`).join(' · ')],
    ['Accuracy', 'Calibration and returns', 'Settled yes/no markets with a price that far out', `${fi(N.calibration[30])} / ${fi(N.calibration[90])} / ${fi(N.calibration[180])}`, 'priced 30 / 90 / 180 days out'],
    ['Rewards', 'Coverage by horizon and category', 'Markets in the market list (still open on 14 Jul 2026 or later)', fi(N.coverage_markets), ''],
    ['Rewards', 'Reward days vs other days', 'Listed ≥ 60 days ahead, traded, open 15 Mar – 31 Aug 2026 (every calendar day)', fi(N.panel.markets), fi(N.panel.market_days) + ' market-days'],
    ['Rewards', 'Price moving toward the outcome', 'Those that have since settled yes/no (days with a candle row)', fi(N.settled_panel.markets), fi(N.settled_panel.market_days) + ' market-days'],
    ['Rewards', 'Before and after the first reward', 'Rewarded markets with at least one never-rewarded control in their series', fi(S.reward_es_meta.all ? Math.max(...S.reward_es.filter(r => r.sample === 'all').map(r => r.stacks || 0)) : null), S.reward_es_meta.reward_usd_settled ? `${fi(S.reward_es_meta.reward_usd_settled.markets)} settled` : ''],
  ]));
}

// ------------------------------------------------------------------ Notes
function pageNotes(main) {
  const wrap = h('div', { class: 'narrow' }); main.append(wrap); main = wrap;
  pageHead(main, 'Notes: the Brier-on-volume regression', 'What the regression on the Regression tab assumes, what it tests, and what to watch for.');
  const g = h('div', { class: 'grid' }); main.append(g);
  const section = (title, ...kids) => { const c = card(title, null, null, 'card wide'); c.append(...kids); g.append(c); };
  const ul = (...items) => h('ul', { class: 'plain' }, items.map(x => h('li', {}, ...[x].flat())));
  const fx = src => h('div', { class: 'formula' }, tex(src, true));

  const defs = rows => simpleTable([
    { key: 's', label: 'Symbol', render: r => h('span', { style: 'white-space:nowrap' }, tex(r[0])) },
    { key: 'm', label: 'Meaning', render: r => h('span', {}, ...[r[1]].flat()) }], rows);

  section('The model',
    fx(String.raw`\text{Brier}_{m,d} = \beta\,\text{LogVol}_{m,d} + \theta\,\text{DaysToExpiry}_{m,d} + \lambda\,\text{Duration}_m + \underbrace{\mu_{\text{month}(d)}}_{\text{month FE}} + \underbrace{\kappa_{\text{category}(m)}}_{\text{category FE}} + \underbrace{\alpha_m}_{\text{contract FE}} + \varepsilon_{m,d}`),
    h('p', {}, 'Each specification keeps only some of these terms: (1) volume, days to expiry and month FE; (2) adds duration and category FE; (3) volume, days to expiry, month FE and contract FE; (4) is (3) with a separate baseline for each of 20 days-to-expiry bins (0–1, 1–2, …, 6–7, 7–14, 14–21, 21–28, 28–42, 42–56, 56–90, 90–120, 120–150, 150–180, 180–240, 240–300, 300–365, 365+ days) instead of the straight-line θ; (5) is (3) with θ on log(1 + days to expiry). One row of data is one market on one day.'),
    defs([
      ['m', 'A market (one yes/no contract).'],
      ['d', 'A calendar day on which the market has a price.'],
      [String.raw`\text{Price}_{m,d}`, 'The market’s price on day d, read as a probability between 0 and 1.'],
      [String.raw`\text{Outcome}_m`, '1 if the market resolved Yes, 0 if No.'],
      [String.raw`\text{Brier}_{m,d}`, [tex(String.raw`(\text{Price}_{m,d} - \text{Outcome}_m)^2`), '. 0 is a perfect forecast, 0.25 is always saying 50%. Lower is better.']],
      [String.raw`\text{CumVol}_{m,d}`, 'Total volume traded in the market before day d (contracts on Kalshi, shares on Polymarket).'],
      [String.raw`\text{LogVol}_{m,d}`, [tex(String.raw`\log(1 + \text{CumVol}_{m,d})`), '. The +1 keeps it defined on days with no past trading.']],
      [String.raw`\text{DaysToExpiry}_{m,d}`, 'Days from day d until the market closes.'],
      [String.raw`\text{Duration}_m`, 'Days from the market’s open to its close (spec 2 only).'],
      [String.raw`\beta`, 'Change in Brier when LogVol rises by 1. This is the number of interest.'],
      [String.raw`\theta`, 'Change in Brier for one more day to expiry.'],
      [String.raw`\lambda`, 'Change in Brier for one more day of market duration.'],
      [String.raw`\mu_{\text{month}(d)}`, 'Month fixed effect: the baseline for the calendar month that day d falls in.'],
      [String.raw`\kappa_{\text{category}(m)}`, 'Category fixed effect: the baseline for the market’s category (sports, politics, …).'],
      [String.raw`\alpha_m`, 'Contract fixed effect: the baseline for this particular market.'],
      [String.raw`\varepsilon_{m,d}`, 'Error: the part of Brier the model does not explain.']]),
    h('p', {}, 'Standard errors are clustered by event: days of the same market, and markets in the same event, are not independent observations.'));

  section('Fixed effects',
    h('p', {}, 'A fixed effect is one baseline number per group, estimated from the data. Written out for months:'),
    fx(String.raw`\mu_{\text{month}(d)} = \sum_{k} \mu_k \cdot \mathbf{1}[\text{month}(d) = k]`),
    defs([
      ['k', 'A calendar month in the data (e.g. March 2026).'],
      [String.raw`\mu_k`, 'The baseline for month k: how much higher or lower Brier is for every market that month, once volume and days to expiry are accounted for. If prices were generally worse in March 2026, its μ is positive (say +0.02) and every market-day in March gets that added.'],
      [String.raw`\mathbf{1}[\text{month}(d) = k]`, '1 if day d falls in month k, otherwise 0. So the sum just picks out the one μ for day d’s month.'],
      [String.raw`\kappa_c`, 'Same idea per category c: one number shared by every market in that category.'],
      [String.raw`\alpha_m`, 'Same idea per market m: one number shared by all of that market’s days (how hard that particular question is).']]),
    h('p', {}, h('b', {}, 'In short: '), tex(String.raw`\beta`), ' and ', tex(String.raw`\theta`), ' are estimated first, without ever working out the fixed effects. The fixed effects could be recovered afterwards, but we do not need them, so the code never computes them.'),
    h('p', {}, 'The steps, for spec (1), which has only the month fixed effect:'),
    h('p', {}, h('b', {}, 'Step 1. '), 'The model:'),
    fx(String.raw`\text{Brier}_{m,d} = \beta\,\text{LogVol}_{m,d} + \theta\,\text{DaysToExpiry}_{m,d} + \mu_{\text{month}(d)} + \varepsilon_{m,d}`),
    h('p', {}, h('b', {}, 'Step 2. '), 'Average it over all market-days in month ', tex('k'), '. ', tex(String.raw`\mu_k`), ' is the same for all of them, so its average is still ', tex(String.raw`\mu_k`), ':'),
    fx(String.raw`\overline{\text{Brier}}_k = \beta\,\overline{\text{LogVol}}_k + \theta\,\overline{\text{DaysToExpiry}}_k + \mu_k + \bar{\varepsilon}_k, \qquad \text{where } \overline{\text{Brier}}_k = \frac{1}{n_k}\sum_{(m,d)\,\in\,k} \text{Brier}_{m,d}`),
    h('p', {}, h('b', {}, 'Step 3. '), 'For a market-day in month ', tex('k'), ', subtract step 2 from step 1. ', tex(String.raw`\mu_k - \mu_k = 0`), ', so the fixed effect is gone:'),
    fx(String.raw`\text{Brier}_{m,d} - \overline{\text{Brier}}_k = \beta\,(\text{LogVol}_{m,d} - \overline{\text{LogVol}}_k) + \theta\,(\text{DaysToExpiry}_{m,d} - \overline{\text{DaysToExpiry}}_k) + (\varepsilon_{m,d} - \bar{\varepsilon}_k)`),
    h('p', {}, h('b', {}, 'Step 4. '), 'Estimate ', tex(String.raw`\beta`), ' and ', tex(String.raw`\theta`), ' from step 3 by ordinary least squares: Brier minus its month average, regressed on volume and days to expiry minus their month averages. No ', tex(String.raw`\mu`), ' is involved. This is what the code does.'),
    h('p', {}, h('b', {}, 'Step 5 (optional, skipped). '), 'With the estimates ', tex(String.raw`\hat\beta, \hat\theta`), ' in hand, each month’s fixed effect is its average Brier after removing what volume and days to expiry explain:'),
    fx(String.raw`\hat\mu_k = \frac{1}{n_k}\sum_{(m,d)\,\in\,k} \big(\text{Brier}_{m,d} - \hat\beta\,\text{LogVol}_{m,d} - \hat\theta\,\text{DaysToExpiry}_{m,d}\big)`),
    defs([
      [String.raw`n_k`, 'Number of market-days in month k.'],
      [String.raw`(m,d) \in k`, 'All market-days whose day d falls in month k.'],
      [String.raw`\overline{\text{Brier}}_k`, 'Average Brier over those market-days. A bar means “average over the group”; the same goes for the other barred terms.'],
      [String.raw`\hat\beta,\ \hat\theta,\ \hat\mu_k`, 'The values estimated from the data (a hat means “estimated”).']]),
    ul(
      'Example. March: average Brier 0.20, average LogVol 5. A March market-day with LogVol 7 and Brier 0.15 enters step 4 as “+2 volume, −0.05 Brier”. April: averages 0.10 and 6. An April market-day with LogVol 6.5 and Brier 0.08 enters as “+0.5 volume, −0.02 Brier”. That March was a hard month never enters.',
      ['Contract fixed effect ', tex(String.raw`\alpha_m`), ': the same steps, averaging over all days of market ', tex('m'), ' instead of all market-days in month ', tex('k'), '. Anything else fixed for a market cancels too, which is why duration and category cannot be in spec (3). Example: market A averages Brier 0.05 and its days at 0.06, 0.05, 0.04 enter as +0.01, 0, −0.01; market B averages 0.28 and its days at 0.30, 0.28, 0.26 enter as +0.02, 0, −0.02. That B is the harder question never enters.'],
      ['Category fixed effect ', tex(String.raw`\kappa_c`), ': the same, averaging over all market-days in category ', tex('c'), '.'],
      'Two fixed effects together (spec 3: month and contract): month averages and market averages are subtracted in turn, repeating until nothing changes, then step 4.',
      'This gives exactly the same β and θ as putting one 0/1 column per month (and per market) into an ordinary regression. The subtraction is a shortcut that avoids hundreds of thousands of extra columns.'));

  section('What it tests',
    ul(
      ['Null hypothesis ', tex(String.raw`\beta = 0`), ': at the same distance from expiry and in the same month, days with more past trading are no more and no less accurate.'],
      [tex(String.raw`\beta < 0`), ': more trading goes with lower Brier, i.e. more accurate prices. Doubling volume changes Brier by about ', tex(String.raw`0.69\,\beta`), '.'],
      'Specs (1) and (2) mostly compare different markets. Spec (3) asks whether the same market gets more accurate as its trading builds up.'));

  section('Assumptions',
    ul(
      'Functional form: Brier is linear in log volume and in days to expiry. Days to expiry is clearly not linear (Brier drops fast near the close).',
      'No omitted factor that moves both volume and accuracy. This is the main one, and the reason the results are associations rather than causal effects.',
      'Errors independent across events, with enough events for clustering to work. Subsets with few events (e.g. markets open > 180 days) are weaker.',
      'Equal error variance is not needed: clustered standard errors allow for it.'));

  section('What to be careful of',
    ul(
      'Volume is endogenous. News moves the price toward the truth and brings a burst of trading at the same time. Close races (prices near 50¢) attract trading and have a high Brier by construction.',
      'In spec (3), volume only rises and days to expiry only falls within a market, so the two are separated only by the shape of volume growth. The volume estimate there is fragile.',
      'Market age: cumulative volume also stands in for how old the market is. Spec (2) controls for age through duration and days to expiry; spec (1) does not.',
      'Stale prices: an illiquid market’s last trade can be days old, so its Brier stays flat. That ties low volume to flat Brier mechanically, which is why days without a two-sided quote are dropped.',
      'Weighting: each market-day is one row, so long markets count far more than short ones. A check is to weight each market equally.',
      'Multi-outcome events: long-shot candidates trade little and score a low Brier easily, which pushes β up. Contract fixed effects remove this; specs (1) and (2) do not.',
      'Bad controls: do not control for the price, or anything volume itself changes. That removes part of the effect being measured.',
      'Selection: only resolved markets are used, and “expired in year X” picks markets by end date, so each subset has a different mix.',
      'Large samples: with millions of rows, tiny effects come out significant. Judge size against the average Brier, and remember there are many regressions (five specifications, several samples and categories), so a few significant results can appear by chance.',
      'Kalshi vs Polymarket: volume levels differ across platforms, so compare signs and relative sizes rather than raw coefficients.'));
}

function route() {
  const path = (location.hash.slice(2) || 'overview');
  S = isPM() ? Object.assign({}, S_ALL, S_ALL.pm, { pm: S_ALL.pm }) : S_ALL;
  document.querySelectorAll('header nav a').forEach(a => a.classList.toggle('active', a.getAttribute('href') === '#/' + path));
  const ps = $('#plat-seg');
  ps.replaceChildren(...[['kalshi', 'Kalshi'], ['polymarket', 'Polymarket']].map(([k, t]) => h('button', { class: k === PLAT ? 'on' : '', disabled: k === 'polymarket' && !S_ALL.pm ? '' : null, onclick: () => { PLAT = k; try { localStorage.setItem('plat', k); } catch (e) { } route(); } }, t)));
  $('#hdr-note').textContent = isPM() ? `data to ${S.inventory.price_last} · built ${S_ALL.built_at.slice(0, 10)}` : `data to 21 Sep 2026 · built ${S_ALL.built_at.slice(0, 10)}`;
  const main = $('#main'); main.replaceChildren(); window.scrollTo(0, 0);
  const P = { overview: pageOverview, horizons: pageHorizons, accuracy: pageAccuracy, regressions: pageRegressions, tail: pageTail, rewards: pageRewards, coverage: pageCoverage, data: pageData, notes: pageNotes };
  try { (P[path] || pageOverview)(main); } catch (e) { main.append(h('pre', {}, String(e.stack || e))); }
}
fetch('data/site.json').then(r => r.json()).then(j => { S_ALL = j; window.addEventListener('hashchange', route); route(); }).catch(e => { $('#main').replaceChildren(h('pre', {}, 'Could not load data/site.json. Run: python website/build_site.py\n' + e)); });
