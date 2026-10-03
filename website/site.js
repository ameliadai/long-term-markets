const $ = (s, r = document) => r.querySelector(s);
const h = (tag, attrs = {}, ...kids) => { const e = document.createElement(tag); for (const k in attrs) { if (attrs[k] == null || attrs[k] === false) continue; if (k === 'class') e.className = attrs[k]; else if (k.startsWith('on')) e.addEventListener(k.slice(2), attrs[k]); else e.setAttribute(k, attrs[k]); } for (const k of kids.flat()) if (k != null) e.appendChild(typeof k === 'string' || typeof k === 'number' ? document.createTextNode(k) : k); return e; };
const fi = v => v == null ? '–' : Math.round(v).toLocaleString();
const f2 = v => v == null ? '–' : (+v).toFixed(2), f3 = v => v == null ? '–' : (+v).toFixed(3);
const pct = (v, d = 0) => v == null ? '–' : (v * 100).toFixed(d) + '%';
const cents = v => v == null ? '–' : (v * 100).toFixed(1).replace(/\.0$/, '') + '¢';
const usd = v => v == null ? '–' : v >= 1e6 ? '$' + (v / 1e6).toFixed(1) + 'M' : v >= 1e3 ? '$' + (v / 1e3).toFixed(0) + 'K' : '$' + (+v).toFixed(v < 10 ? 2 : 0);
const big = v => v == null ? '–' : v >= 1e9 ? (v / 1e9).toFixed(1) + 'B' : v >= 1e6 ? (v / 1e6).toFixed(1) + 'M' : v >= 1e3 ? (v / 1e3).toFixed(0) + 'K' : (+v).toFixed(0);
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
    ['rewards', 'Rewards', PM ? 'What can and can’t be seen about Polymarket’s reward programs.' : 'The programs Kalshi pays for liquidity and trading, which markets get them, and what changes on reward days.'],
    ['coverage', 'What we have', 'The data available, in plain terms, and what is missing.'],
    ['data', 'Data', 'Dataset sizes and the sample behind each analysis.'],
    ['notes', 'Notes', 'How the regression works: assumptions, fixed effects, and what to be careful of.'],
  ];
  main.append(h('ul', { class: 'findings' }, tabs.map(([href, name, text]) => h('li', {}, h('a', { href: '#/' + href }, h('b', {}, name)), ' — ' + text))));
  main.append(h('p', { class: 'muted small', style: 'margin-top:14px' }, PM
    ? `Polymarket: resolved yes/no markets open at least a day that started from 30 Sep 2023; data to ${S.inventory.price_last}. Sports and crypto markets are left out.`
    : 'Kalshi: markets closing in 2026 or later; combo (parlay) markets excluded; data to 21 Sep 2026. Sports and crypto markets are left out.'));
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
    const stars = bands.map(b => { const x = S.liq_equal_sig.find(r => r.measure === k && r.band === b); return !x ? '' : x.p < 0.01 ? '**' : x.p < 0.05 ? '*' : ''; });
    C.vbar(right, blab, ['less liquid half', 'more liquid half'].map(hf => ({ name: hf, values: bands.map(b => S.liq_equal.find(r => r.measure === k && r.band === b && r.half === hf)?.brier ?? null) })), { fmtV: f3, H: 190, marks: stars, sublabels: bands.map(b => 'n=' + fi(S.liq_equal.filter(r => r.measure === k && r.band === b).reduce((a, r) => a + r.markets, 0))) });
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
  const pval = t => { const z = Math.abs(t) / Math.SQRT2, k = 1 / (1 + 0.3275911 * z); return k * (0.254829592 + k * (-0.284496736 + k * (1.421413741 + k * (-1.453152027 + k * 1.061405429)))) * Math.exp(-z * z); };
  const stars = p => p < 0.001 ? '***' : p < 0.01 ? '**' : p < 0.05 ? '*' : '';
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
  const T = S.reward_totals, M = S.reward_months;
  pageHead(main, 'Kalshi’s reward programs', 'Kalshi pays traders to keep orders near the best price (liquidity rewards) or to trade (volume rewards), market by market.');
  main.append(h('div', { class: 'tiles' },
    tile(usd(T.usd), 'posted in rewards', 'all categories, Sep 2025 – Sep 2026'),
    tile(fi(T.markets), 'markets rewarded'),
    tile(fi(M.programs[M.programs.length - 1]), 'programs started in Sep 2026', `vs ${fi(M.programs[0])} in Sep 2025`),
    tile(usd(T.by_kind['Long-dated liquidity']), 'dedicated long-dated program', '29 Apr – ~11 Jul 2026')));

  const cd = card('What the reward data contains', `Kalshi’s public list of reward programs: one row per program, ${fi(T.programs)} programs starting ${T.first} – ${T.last}, ${usd(T.usd)} posted in total.`, null, 'card wide');
  cd.append(simpleTable([{ key: 0, label: 'Field' }, { key: 1, label: 'Meaning' }], [
    ['Market', 'Which market the reward is for'],
    ['Type', 'Liquidity (pays for keeping orders near the best price) or volume (pays for trading)'],
    ['Program kind', 'Standard, long-dated, new-event, or series-wide'],
    ['Start and end time', 'When the reward ran'],
    ['Reward amount', 'Dollars posted for that period'],
    ['Paid out', 'Yes or no: whether the program has paid out yet'],
    ['Target size, discount factor', 'Settings for how orders are scored (minimum order size; how fast credit falls off away from the best price)'],
  ]), h('p', { class: 'note' }, 'Not in the data: who earned the rewards, how much each trader got, the actual amount paid (only whether it was paid), and any programs before Sep 2025.'));
  main.append(h('div', { class: 'grid', style: 'margin:16px 0' }, cd));

  const R = S.reward_coverage;
  const c1 = card('Share of markets rewarded', 'Markets other than sports and crypto, by how far ahead they were listed.');
  C.vbar(c1, R.map(r => SHORT[r.hz]), R.map(r => r.share_liquidity_reward), { fmtV: v => pct(v), H: 230 });
  const c2 = card('Reward $ per 1,000 contracts traded', 'Reward dollars posted per 1,000 contracts traded, by how far ahead the market was listed.');
  C.vbar(c2, R.map(r => SHORT[r.hz]), R.map(r => r.reward_usd_per_1k_contracts), { fmtV: v => '$' + f2(v), H: 230 });
  main.append(grid(c1, c2));

  const O = S.orderbook_focus;
  const c3 = card('Quoted, but rarely traded', `Open econ, finance and tech markets on ${S.open_snapshot.time.slice(0, 10)}, by time left until close.`, null, 'card wide');
  c3.append(simpleTable([{ key: 'label', label: 'Time left' }, { key: 'markets', label: 'Markets', num: true, render: r => fi(r.markets) }, { key: 'two_sided', label: 'Have buy and sell quotes', num: true, render: r => pct(r.two_sided) }, { key: 'spread_med', label: 'Median spread', num: true, render: r => cents(r.spread_med) }, { key: 'traded_24h', label: 'Traded in last 24h', num: true, render: r => pct(r.traded_24h) }], O));
  main.append(h('div', { class: 'grid', style: 'margin-top:16px' }, c3));

  sectionHead(main, 'What changes on reward days', `The same market on reward days vs its other days (${fi(S.samples.panel.markets)} markets, Mar–Aug 2026). Bold = clearly different from zero.`);
  const lab = { two_sided_share: 'Has buy and sell quotes (share of hours)', spread_med: 'Median spread', traded: 'Traded that day', log_volume: 'Volume (log)', info_gain: 'Price moved toward the final outcome' };
  const eff = r => r ? h('span', { class: Math.abs(r.t) > 2 ? 'sig' : '' }, (r.coef > 0 ? '+' : '') + (r.outcome === 'spread_med' ? (r.coef * 100).toFixed(1) + '¢' : r.outcome === 'info_gain' ? r.coef.toFixed(4) : r.outcome === 'log_volume' ? f2(r.coef) : (r.coef * 100).toFixed(0) + ' pts')) : '–';
  const rows = {}; [...S.reward_effects, ...S.info_effects.filter(r => r.outcome === 'info_gain')].forEach(r => { (rows[r.outcome] ||= { outcome: r.outcome, mean_y: r.mean_y })[r.reward] = r; });
  const base = r => r.outcome === 'spread_med' ? cents(r.mean_y) : r.outcome === 'info_gain' ? r.mean_y.toFixed(4) : r.outcome === 'log_volume' ? f2(r.mean_y) : pct(r.mean_y);
  const c4 = card('Change on reward days', 'The last row asks whether rewards bring information, not just activity. Part of that effect is mechanical (tighter quotes make the price a better reading).', null, 'card wide');
  c4.append(simpleTable([{ key: 'outcome', label: 'Outcome', render: r => lab[r.outcome] }, { key: 'mean_y', label: 'Typical day', num: true, render: base }, { key: 'ld', label: 'Long-dated reward', num: true, render: r => eff(r.rw_long_dated) }, { key: 'lip', label: 'Other liquidity reward', num: true, render: r => eff(r.rw_liquidity) }], Object.values(rows)));
  main.append(h('div', { class: 'grid' }, c4));
  const how = card('How the numbers above are calculated', null, null, 'card wide');
  how.append(
    h('p', { class: 'expl' }, 'Each estimate compares a market’s reward days with its own non-reward days, net of day-wide shocks and time to close.'),
    h('div', { class: 'formula' }, tex(String.raw`\text{Outcome}_{m,d} = \beta_1\,\text{LongDated}_{m,d} + \beta_2\,\text{OtherLiquidity}_{m,d} + \sum_{b}\gamma_b\,\mathbf{1}\!\left[\text{DaysToClose}_{m,d}\in b\right] + \alpha_m + \delta_d + \varepsilon_{m,d}`, true)),
    h('ul', { class: 'plain' },
      h('li', {}, tex(String.raw`\text{Outcome}_{m,d}`), ': the row’s measure for market ', tex('m'), ' on day ', tex('d'), ' (e.g. its median spread that day)'),
      h('li', {}, tex(String.raw`\text{LongDated}_{m,d}`), ': 1 if the market had a long-dated reward that day, else 0'),
      h('li', {}, tex(String.raw`\text{OtherLiquidity}_{m,d}`), ': 1 if it had any other liquidity reward that day, else 0'),
      h('li', {}, tex(String.raw`\text{DaysToClose}_{m,d}`), ': days left until the market closes, in bins ', tex('b'), ' (0–7, 7–30, 30–90, 90–180, 180–365, 365+); ', tex(String.raw`\gamma_b`), ' is one constant per bin'),
      h('li', {}, tex(String.raw`\alpha_m`), ': one constant per market (market fixed effect); ', tex(String.raw`\delta_d`), ': one constant per calendar day (day fixed effect); ', tex(String.raw`\varepsilon_{m,d}`), ': error'),
      h('li', {}, 'Columns: long-dated reward = ', tex(String.raw`\hat\beta_1`), ', other liquidity reward = ', tex(String.raw`\hat\beta_2`), ', typical day = average of ', tex(String.raw`\text{Outcome}_{m,d}`)),
      h('li', {}, 'OLS, SEs clustered by series; bold = |t| > 2')),
    (() => { const e = S.reward_effects.find(r => r.reward === 'rw_long_dated' && r.outcome === 'spread_med'); return h('p', { class: 'expl' }, `Example: on long-dated reward days the median spread is ${(Math.abs(e.coef) * 100).toFixed(1)}¢ ${e.coef < 0 ? 'lower' : 'higher'} than on the same market’s other days (typical: ${(e.mean_y * 100).toFixed(1)}¢). Kalshi chooses where rewards run, so these are associations, not causal effects.`); })());
  main.append(h('div', { class: 'grid', style: 'margin-top:16px' }, how));

  const ES = S.event_study;
  const c5 = card('Long-dated program: median spread by week', 'Week 0 = a market’s first reward week. Spreads drop to 1¢, then settle around 3¢ (partly because markets are closer to close).', null, 'card wide');
  C.line(c5, ES.map(r => (r.week > 0 ? '+' : '') + r.week), [{ name: 'median spread', values: ES.map(r => r.spread) }], { fmtV: cents, ymin: 0, fmtX: x => 'week ' + x, W: 900, H: 220 });
  main.append(h('div', { class: 'grid', style: 'margin-top:16px' }, c5));
}

// ------------------------------------------------------------------ What we have
function pageCoverage(main) {
  if (isPM()) return pageCoveragePM(main);
  pageHead(main, 'What data we have, in plain terms', 'A quick guide to what the Kalshi data can and can’t show. The analyses leave out sports and crypto markets. The Data tab has the technical details.');
  const c1 = card('What we have', null, null, 'card wide'); const g = h('div', { class: 'grid' }, c1); main.append(g);
  c1.append(simpleTable([{ key: 0, label: 'Data' }, { key: 1, label: 'What it tells us' }, { key: 2, label: 'How far back' }, { key: 3, label: 'Have it?', render: r => h('span', { class: 'have' }, r[3]) }], [
    ['List of markets', 'Each market’s question, open and close dates, outcome, and total amount traded over its life', 'Markets closing in 2026 or later (plus a few older ones)', '✓ Yes'],
    ['Hourly price history', 'For every hour: the price, the best buy and sell offers, how much traded, and how many contracts people held', 'From the day each market opened (as early as mid-2023)', '✓ Yes'],
    ['Individual trades', 'Every single trade: exact time, price, size, and whether the buyer took YES or NO', 'Only 15 Jul – 21 Sep 2026', '⚠ Only ~70 days'],
    ['Reward programs', 'Which markets Kalshi paid people to trade or quote in, when, and how much', 'Sep 2025 – Sep 2026', '✓ Yes'],
    ['Order book depth', 'How many contracts are waiting to be bought or sold at each price', 'Only one snapshot, 23 Sep 2026', '⚠ One day only'],
  ]));
  const c2 = card('What we don’t have', null, null, 'card wide'); g.append(c2);
  c2.append(simpleTable([{ key: 0, label: 'Missing' }, { key: 1, label: 'Why' }], [
    ['Order book history', 'Kalshi only shows the current book, not past ones'],
    ['Individual trades before mid-July 2026', 'Kalshi deletes trades after about 70 days'],
    ['Markets that closed before 2026', 'Kalshi no longer lists them'],
    ['Who traded', 'Kalshi never makes this public'],
    ['Anything after 21 Sep 2026', 'The download stopped then; it needs a catch-up run before late November'],
  ]));
  main.append(h('p', { class: 'summary' }, 'So for any market closing in 2026 or later, we can see its whole life hour by hour, just not trade by trade before mid-July.'));
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
    ['Accuracy', 'AUC by group', 'The lived-≥ 90-days sample', fi(N.accuracy[90]), `Econ/Fin ${ag['Econ/Fin']} · Politics ${ag.Politics} · Sports ${ag.Sports} · Tech ${ag['Tech/AI/Co']} · Other ${ag.Other}`],
    ['Accuracy', 'Calibration and returns', 'Settled yes/no markets with a price that far out', `${fi(N.calibration[30])} / ${fi(N.calibration[90])} / ${fi(N.calibration[180])}`, 'priced 30 / 90 / 180 days out'],
    ['Rewards', 'Coverage by horizon', 'Markets closing in 2026 or later', fi(N.coverage_markets), ''],
    ['Rewards', 'Reward-day effects', 'Lived ≥ 60 days, traded, open 15 Mar – 31 Aug 2026', fi(N.panel.markets), fi(N.panel.market_days) + ' market-days'],
    ['Rewards', 'Information vs activity', 'Those that have since settled yes/no', fi(N.settled_panel.markets), fi(N.settled_panel.market_days) + ' market-days'],
    ['Rewards', 'Long-dated program by week', 'Panel markets with a long-dated reward', fi(N.event_study_markets), ''],
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
