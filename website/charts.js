// Minimal SVG chart helpers. No dependencies.
const C = (() => {
  const NS = 'http://www.w3.org/2000/svg';
  const SERIES = ['var(--s1)', 'var(--s2)', 'var(--s3)', 'var(--s4)', 'var(--s5)', 'var(--s6)', 'var(--s7)', 'var(--s8)'];
  const tip = document.getElementById('tooltip');
  function el(tag, attrs = {}, parent) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
  function txt(parent, x, y, s, attrs = {}) { const t = el('text', { x, y, ...attrs }, parent); t.textContent = s; return t; }
  function showTip(evt, html) { tip.style.display = 'block'; tip.replaceChildren(html); const w = tip.offsetWidth, h = tip.offsetHeight; let x = evt.clientX + 14, y = evt.clientY + 14; if (x + w > innerWidth - 8) x = evt.clientX - w - 14; if (y + h > innerHeight - 8) y = evt.clientY - h - 14; tip.style.left = x + 'px'; tip.style.top = y + 'px'; }
  function hideTip() { tip.style.display = 'none'; }
  function tipHtml(title, rows) { const d = document.createElement('div'); const b = document.createElement('b'); b.textContent = title; d.appendChild(b); for (const r of rows) { const row = document.createElement('div'); row.className = 'row'; if (r.color) { const i = document.createElement('i'); i.style.background = r.color; row.appendChild(i); } const v = document.createElement('span'); v.textContent = r.value; v.style.fontWeight = '600'; row.appendChild(v); const l = document.createElement('span'); l.textContent = r.label; l.style.color = 'var(--text2)'; row.appendChild(l); d.appendChild(row); } return d; }
  const fmt = (v, d = 3) => v == null || Number.isNaN(v) ? '–' : (Math.abs(v) >= 1000 ? Math.round(v).toLocaleString() : (+v).toFixed(d).replace(/\.?0+$/, ''));
  const fmtInt = v => v == null ? '–' : Math.round(v).toLocaleString();
  function ticks(min, max, n = 5) { const span = max - min || 1; const step0 = span / n; const p = Math.pow(10, Math.floor(Math.log10(step0))); const step = [1, 2, 2.5, 5, 10].map(m => m * p).find(s => span / s <= n) || p * 10; const out = []; for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(+v.toFixed(10)); return out; }
  function frame(container, W, H, m) { const svg = el('svg', { viewBox: `0 0 ${W} ${H}` }); container.appendChild(svg); const g = el('g', { transform: `translate(${m.l},${m.t})` }, svg); return { svg, g, w: W - m.l - m.r, h: H - m.t - m.b }; }
  function yAxis(g, w, h, y, tk, fmtF = fmt) { const gr = el('g', { class: 'grid' }, g); for (const t of tk) { el('line', { x1: 0, x2: w, y1: y(t), y2: y(t) }, gr); txt(g, -6, y(t) + 4, fmtF(t), { 'text-anchor': 'end' }); } }
  function legend(container, names, kind = 'line', colors = []) { const d = document.createElement('div'); d.className = 'legend'; names.forEach((n, i) => { const s = document.createElement('span'); const i2 = document.createElement('i'); i2.className = kind === 'rect' ? 'rect' : ''; i2.style.background = colors[i] || SERIES[i % 8]; s.appendChild(i2); s.appendChild(document.createTextNode(n)); d.appendChild(s); }); container.appendChild(d); }

  // Horizontal bar chart: items [{label, value, sub?}], optional onClick
  function hbar(container, items, { color = SERIES[0], W = 460, fmtV = fmtInt, onClick, maxItems = 30, labelW = 150, labelChars = 24, refLine = null, refLabel = '' } = {}) {
    items = items.slice(0, maxItems); const rowH = 20, m = { l: labelW, r: 60, t: 4, b: 4 }; const H = items.length * rowH + m.t + m.b;
    const { g, w } = frame(container, W, H, m); const max = Math.max(...items.map(i => i.value), refLine || 0, 1e-9);
    items.forEach((it, i) => { const y = i * rowH; const bw = Math.max(2, it.value / max * w); const r = el('rect', { x: 0, y: y + 3, width: bw, height: rowH - 6, rx: 3, fill: it.color || color }, g); if (onClick) r.style.cursor = 'pointer'; txt(g, -6, y + 14, it.label.length > labelChars ? it.label.slice(0, labelChars - 1) + '…' : it.label, { 'text-anchor': 'end' }); txt(g, bw + 4, y + 14, fmtV(it.value)); const hit = el('rect', { x: -m.l, y, width: w + m.l + m.r, height: rowH, fill: 'transparent' }, g); hit.addEventListener('pointermove', e => showTip(e, tipHtml(it.label, [{ value: fmtV(it.value), label: it.sub || '', color: it.color || color }]))); hit.addEventListener('pointerleave', hideTip); if (onClick) { hit.style.cursor = 'pointer'; hit.addEventListener('click', () => onClick(it)); } });
    if (refLine != null) { const x = refLine / max * w; el('line', { x1: x, x2: x, y1: 0, y2: items.length * rowH, stroke: 'var(--text)', 'stroke-width': 1.5, 'stroke-dasharray': '5 4', 'pointer-events': 'none' }, g); if (refLabel) txt(g, x - 5, 14, refLabel, { 'text-anchor': 'end', 'font-size': 10 }); }
  }
  // Vertical bars / histogram: labels[], values[] (or series: [{name, values}])
  function vbar(container, labels, series, { W = 460, H = 220, fmtV = fmtInt, ylabel, rotate = false, stacked = false, onClick, marks, sublabels } = {}) {
    if (!Array.isArray(series) || typeof series[0] !== 'object') series = [{ name: '', values: series }];
    const m = { l: 44, r: 8, t: 8, b: rotate ? 90 : sublabels ? 38 : 24 }; const { g, w, h } = frame(container, W, H, m); const n = labels.length; const bwAll = w / n;
    let max = 0; if (stacked) { for (let i = 0; i < n; i++) max = Math.max(max, series.reduce((a, s) => a + (s.values[i] || 0), 0)); } else series.forEach(s => s.values.forEach(v => { if (v > max) max = v; })); if (!max) max = 1;
    const tk = ticks(0, max, 4); const top = Math.max(max, tk[tk.length - 1] || 0); const y = v => h - v / top * h; yAxis(g, w, h, y, tk, fmtV);
    const nS = series.length; const gap = Math.max(2, bwAll * (nS > 1 && !stacked ? 0.2 : 0.32)); for (let i = 0; i < n; i++) { let acc = 0; series.forEach((s, si) => { const v = s.values[i] || 0; let x, bw, y0, y1; if (stacked) { x = i * bwAll + gap / 2; bw = bwAll - gap; y1 = y(acc); y0 = y(acc + v); acc += v; } else { bw = (bwAll - gap) / nS; x = i * bwAll + gap / 2 + si * bw; y0 = y(v); y1 = h; } const r = el('rect', { x, y: y0, width: Math.max(bw - (stacked ? 0 : 1), 1), height: Math.max(0, y1 - y0), fill: s.color || SERIES[si % 8], rx: 2 }, g); if (onClick) r.style.cursor = 'pointer'; }); if (marks && marks[i]) { const top = Math.max(...series.map(s => s.values[i] || 0)); txt(g, i * bwAll + bwAll / 2, y(top) - 5, marks[i], { 'text-anchor': 'middle', 'font-size': 13, 'font-weight': 700 }); } const hit = el('rect', { x: i * bwAll, y: 0, width: bwAll, height: h, fill: 'transparent' }, g); hit.addEventListener('pointermove', e => showTip(e, tipHtml(labels[i], series.map((s, si) => ({ value: fmtV(s.values[i] || 0), label: s.name, color: s.color || SERIES[si % 8] }))))); hit.addEventListener('pointerleave', hideTip); if (onClick) { hit.style.cursor = 'pointer'; hit.addEventListener('click', () => onClick(labels[i], i)); } }
    const every = Math.ceil(n / (rotate ? 40 : 12)); labels.forEach((l, i) => { if (i % every) return; const x = i * bwAll + bwAll / 2; if (rotate) txt(g, x, h + 8, l, { 'text-anchor': 'end', transform: `rotate(-45 ${x} ${h + 8})` }); else txt(g, x, h + 14, l, { 'text-anchor': 'middle' }); if (sublabels && sublabels[i]) txt(g, x, h + 28, sublabels[i], { 'text-anchor': 'middle', 'font-size': 10, fill: 'var(--muted)' }); });
    if (ylabel) txt(g, -m.l + 4, -m.t + 2, ylabel, { 'font-size': 10 });
    if (nS > 1) legend(container, series.map(s => s.name), 'rect', series.map(s => s.color));
  }
  // Line chart: xs (numbers or date strings), series [{name, values}] ; crosshair tooltip
  function line(container, xs, series, { W = 460, H = 220, fmtV = v => fmt(v, 3), fmtX = x => String(x), ylabel, ymin, ymax, band } = {}) {
    const m = { l: 48, r: 12, t: 8, b: 24 }; const { svg, g, w, h } = frame(container, W, H, m); const n = xs.length;
    let lo = ymin ?? Infinity, hi = ymax ?? -Infinity; if (ymin == null || ymax == null) series.forEach(s => s.values.forEach(v => { if (v == null) return; if (ymin == null && v < lo) lo = v; if (ymax == null && v > hi) hi = v; })); if (lo === Infinity) { lo = 0; hi = 1; } if (lo === hi) hi = lo + 1;
    const tk = ticks(lo, hi, 4); lo = Math.min(lo, tk[0]); hi = Math.max(hi, tk[tk.length - 1]); const y = v => h - (v - lo) / (hi - lo) * h; const x = i => n > 1 ? i / (n - 1) * w : w / 2; yAxis(g, w, h, y, tk, fmtV);
    if (band) { const d = 'M' + band.lo.map((v, i) => `${x(i)},${y(v)}`).join('L') + 'L' + band.hi.map((v, i) => `${x(n - 1 - i)},${y(band.hi[n - 1 - i])}`).join('L') + 'Z'; el('path', { d, fill: band.color || SERIES[0], opacity: .12 }, g); }
    series.forEach((s, si) => { let d = '', pen = false; s.values.forEach((v, i) => { if (v == null) { pen = false; return; } d += (pen ? 'L' : 'M') + x(i) + ',' + y(v); pen = true; }); el('path', { d, fill: 'none', stroke: s.color || SERIES[si % 8], 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-dasharray': s.dash || 'none' }, g); });
    const every = Math.ceil(n / 8); xs.forEach((l, i) => { if (i % every) return; txt(g, x(i), h + 14, fmtX(l), { 'text-anchor': 'middle' }); });
    const cross = el('line', { y1: 0, y2: h, stroke: 'var(--text2)', 'stroke-dasharray': '3 3', visibility: 'hidden' }, g); const dots = series.map((s, si) => el('circle', { r: 4, fill: s.color || SERIES[si % 8], stroke: 'var(--surface)', 'stroke-width': 2, visibility: 'hidden' }, g));
    const hit = el('rect', { x: 0, y: 0, width: w, height: h, fill: 'transparent' }, g);
    hit.addEventListener('pointermove', e => { const pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY; const p = pt.matrixTransform(g.getScreenCTM().inverse()); const i = Math.max(0, Math.min(n - 1, Math.round(p.x / w * (n - 1)))); cross.setAttribute('x1', x(i)); cross.setAttribute('x2', x(i)); cross.setAttribute('visibility', 'visible'); series.forEach((s, si) => { const v = s.values[i]; if (v == null) dots[si].setAttribute('visibility', 'hidden'); else { dots[si].setAttribute('cx', x(i)); dots[si].setAttribute('cy', y(v)); dots[si].setAttribute('visibility', 'visible'); } }); showTip(e, tipHtml(fmtX(xs[i]), series.map((s, si) => ({ value: fmtV(s.values[i]), label: s.name, color: s.color || SERIES[si % 8] })))); });
    hit.addEventListener('pointerleave', () => { hideTip(); cross.setAttribute('visibility', 'hidden'); dots.forEach(d => d.setAttribute('visibility', 'hidden')); });
    if (ylabel) txt(g, -m.l + 4, -m.t + 2, ylabel, { 'font-size': 10 });
    if (series.length > 1) legend(container, series.map(s => s.name), 'line', series.map(s => s.color));
  }
  // Scatter: pts [{x,y,label,color?,r?,sub?}] ; nearest-point tooltip
  function scatter(container, pts, { W = 460, H = 300, xlabel, ylabel, fmtX = v => fmt(v, 3), fmtY = v => fmt(v, 3), diag = false, onClick, xmin, xmax, ymin, ymax, labelTop = 0 } = {}) {
    const m = { l: 48, r: 12, t: 8, b: 30 }; const { svg, g, w, h } = frame(container, W, H, m);
    const xsv = pts.map(p => p.x), ysv = pts.map(p => p.y); const x0 = xmin ?? Math.min(...xsv), x1 = xmax ?? Math.max(...xsv), y0 = ymin ?? Math.min(...ysv), y1 = ymax ?? Math.max(...ysv);
    const tx = ticks(x0, x1, 5), ty = ticks(y0, y1, 4); const lx = Math.min(x0, tx[0]), hx = Math.max(x1, tx[tx.length - 1]), ly = Math.min(y0, ty[0]), hy = Math.max(y1, ty[ty.length - 1]);
    const X = v => (v - lx) / (hx - lx || 1) * w, Y = v => h - (v - ly) / (hy - ly || 1) * h; yAxis(g, w, h, Y, ty, fmtY); const gr = el('g', { class: 'grid' }, g); tx.forEach(t => { el('line', { x1: X(t), x2: X(t), y1: 0, y2: h }, gr); txt(g, X(t), h + 14, fmtX(t), { 'text-anchor': 'middle' }); });
    if (diag) { const a = Math.max(lx, ly), b = Math.min(hx, hy); el('line', { x1: X(a), y1: Y(a), x2: X(b), y2: Y(b), stroke: 'var(--muted)', 'stroke-dasharray': '4 4' }, g); }
    pts.forEach((p, i) => { const c = el('circle', { cx: X(p.x), cy: Y(p.y), r: p.r || 5, fill: p.color || SERIES[0], 'fill-opacity': .8, stroke: 'var(--surface)', 'stroke-width': 1 }, g); if (onClick) c.style.cursor = 'pointer'; if (i < labelTop) txt(g, X(p.x) + 6, Y(p.y) - 6, p.label, { 'font-size': 10 }); });
    const hit = el('rect', { x: 0, y: 0, width: w, height: h, fill: 'transparent' }, g); const ring = el('circle', { r: 9, fill: 'none', stroke: 'var(--text)', 'stroke-width': 1.5, visibility: 'hidden' }, g); let cur = null;
    function nearest(e) { const pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY; const q = pt.matrixTransform(g.getScreenCTM().inverse()); let best = null, bd = 1e9; pts.forEach(p => { const d = (X(p.x) - q.x) ** 2 + (Y(p.y) - q.y) ** 2; if (d < bd) { bd = d; best = p; } }); return bd < 30 * 30 ? best : null; }
    hit.addEventListener('pointermove', e => { const p = nearest(e); cur = p; if (!p) { hideTip(); ring.setAttribute('visibility', 'hidden'); return; } ring.setAttribute('cx', X(p.x)); ring.setAttribute('cy', Y(p.y)); ring.setAttribute('visibility', 'visible'); showTip(e, tipHtml(p.label, [{ value: fmtX(p.x), label: xlabel || 'x' }, { value: fmtY(p.y), label: ylabel || 'y' }, ...(p.sub ? [{ value: p.sub, label: '' }] : [])])); });
    hit.addEventListener('pointerleave', () => { hideTip(); ring.setAttribute('visibility', 'hidden'); }); if (onClick) { hit.style.cursor = 'pointer'; hit.addEventListener('click', () => cur && onClick(cur)); }
    if (xlabel) txt(g, w, h + 26, xlabel, { 'text-anchor': 'end', 'font-size': 10 }); if (ylabel) txt(g, -m.l + 4, -m.t + 2, ylabel, { 'font-size': 10 });
  }
  // Calibration: series [{name, bins:[{mean_pred, mean_y, n}]}]
  function calibration(container, series, { W = 460, H = 300, hist = false, nb = 10 } = {}) {
    const HS = hist ? 104 : 0; const m = { l: 48, r: 12, t: 8, b: 30 + HS }; const { svg, g, w, h } = frame(container, W, H + HS, m);
    if (hist) {  // count strip under the reliability curve: one bar per bin per series, linear height, counts labelled
      const top = h + 44, sh = 52, bw = w / nb, gap = 3, nS = series.length, one = (bw - 2 * gap) / nS;
      const maxC = Math.max(1, ...series.flatMap(s => s.bins.map(b => b.n))); const H2 = n => n / maxC * sh;
      txt(g, w, top + sh + 13, 'forecasts per bin', { 'text-anchor': 'end', 'font-size': 10 });
      el('line', { x1: 0, x2: w, y1: top + sh, y2: top + sh, stroke: 'var(--border)' }, g);
      series.forEach((s, si) => { const col = s.color || SERIES[si % 8]; const byBin = Object.fromEntries(s.bins.map(b => [b.bin, b.n]));
        for (let i = 0; i < nb; i++) { const n = byBin[i] || 0; const x = i * bw + gap + si * one, hh = H2(n);
          const r = el('rect', { x, y: top + sh - hh, width: Math.max(one - 1, 1), height: hh, fill: col, 'fill-opacity': si === 0 ? .75 : .35, rx: 1 }, g);
          if (si === 0 && n > 0) txt(g, x + one / 2, top + sh - hh - 3, n >= 1000 ? (n / 1000).toFixed(n >= 10000 ? 0 : 1) + 'k' : String(n), { 'text-anchor': 'middle', 'font-size': 9 });
          r.addEventListener('pointermove', e => showTip(e, tipHtml(`${(i / nb).toFixed(1)}–${((i + 1) / nb).toFixed(1)}`, [{ value: fmtInt(n), label: `${s.name} forecasts`, color: col }]))); r.addEventListener('pointerleave', hideTip); } });
    } const X = v => v * w, Y = v => h - v * h; const tk = [0, .2, .4, .6, .8, 1]; yAxis(g, w, h, Y, tk, v => fmt(v, 1)); tk.forEach(t => txt(g, X(t), h + 14, fmt(t, 1), { 'text-anchor': 'middle' }));
    el('line', { x1: 0, y1: h, x2: w, y2: 0, stroke: 'var(--muted)', 'stroke-dasharray': '4 4' }, g);
    const maxN = Math.max(...series.flatMap(s => s.bins.map(b => b.n)), 1);
    series.forEach((s, si) => { const col = s.color || SERIES[si % 8]; const b = s.bins.filter(b => b.n > 0); el('path', { d: b.map((p, i) => (i ? 'L' : 'M') + X(p.mean_pred) + ',' + Y(p.mean_y)).join(''), fill: 'none', stroke: col, 'stroke-width': 2 }, g); b.forEach(p => { const c = el('circle', { cx: X(p.mean_pred), cy: Y(p.mean_y), r: 3 + 6 * Math.sqrt(p.n / maxN), fill: col, 'fill-opacity': .6, stroke: 'var(--surface)', 'stroke-width': 1.5 }, g); c.addEventListener('pointermove', e => showTip(e, tipHtml(s.name, [{ value: fmt(p.mean_pred, 3), label: 'mean predicted', color: col }, { value: fmt(p.mean_y, 3), label: 'observed freq' }, { value: fmtInt(p.n), label: 'n' }]))); c.addEventListener('pointerleave', hideTip); }); });
    txt(g, w, h + 26, 'predicted probability', { 'text-anchor': 'end', 'font-size': 10 }); txt(g, -m.l + 4, -m.t + 2, 'observed frequency', { 'font-size': 10 });
    if (series.length > 1) { const d = document.createElement('div'); d.className = 'legend'; series.forEach((s, si) => { const sp = document.createElement('span'); const i2 = document.createElement('i'); i2.style.background = s.color || SERIES[si % 8]; sp.appendChild(i2); sp.appendChild(document.createTextNode(s.name)); d.appendChild(sp); }); container.appendChild(d); }
  }
  // Time series with real time axis: series [{name, pts:[{t:Date, v}]}], step lines. Optional vertical markers.
  function timeline(container, series, { W = 900, H = 260, ymin = 0, ymax = 1, markers = [], step = true, fmtV = v => fmt(v, 3) } = {}) {
    const m = { l: 44, r: 12, t: 8, b: 26 }; const { svg, g, w, h } = frame(container, W, H, m); const all = series.flatMap(s => s.pts.map(p => +p.t)).concat(markers.map(k => +k.t)); if (!all.length) return; const t0 = Math.min(...all), t1 = Math.max(...all); const span = (t1 - t0) || 1;
    const X = t => (+t - t0) / span * w, Y = v => h - (v - ymin) / (ymax - ymin) * h; const tk = ticks(ymin, ymax, 4); yAxis(g, w, h, Y, tk, fmtV);
    const nT = 6; const fmtT = span < 3 * 86400e3 ? t => new Date(t).toISOString().slice(5, 16).replace('T', ' ') : t => new Date(t).toISOString().slice(0, 10); for (let i = 0; i <= nT; i++) { const t = t0 + span * i / nT; txt(g, X(t), h + 14, fmtT(t), { 'text-anchor': i === 0 ? 'start' : i === nT ? 'end' : 'middle', 'font-size': 10 }); }
    markers.forEach(k => { el('line', { x1: X(k.t), x2: X(k.t), y1: 0, y2: h, stroke: k.color || 'var(--muted)', 'stroke-dasharray': '3 3' }, g); txt(g, X(k.t) + 3, 10, k.label, { 'font-size': 10 }); });
    series.forEach((s, si) => { const col = s.color || SERIES[si % 8]; s.pts.forEach(p => { const c = el('circle', { cx: X(p.t), cy: Y(p.v), r: s.r || 4, fill: col, 'fill-opacity': .85, stroke: 'var(--surface)', 'stroke-width': 1.5 }, g); const hit = el('circle', { cx: X(p.t), cy: Y(p.v), r: 10, fill: 'transparent' }, g); hit.addEventListener('pointermove', e => showTip(e, tipHtml(p.label || s.name, [{ value: fmtV(p.v), label: s.name, color: col }, { value: new Date(p.t).toISOString().replace('T', ' ').slice(0, 16), label: 'UTC' }, ...(p.sub ? [{ value: p.sub, label: '' }] : [])]))); hit.addEventListener('pointerleave', hideTip); if (p.onClick) { hit.style.cursor = 'pointer'; hit.addEventListener('click', p.onClick); } }); });
    series.forEach((s, si) => { const col = s.color || SERIES[si % 8]; if (!s.noline && s.pts.length === 1 && s.line) { el('line', { x1: 0, x2: w, y1: Y(s.pts[0].v), y2: Y(s.pts[0].v), stroke: col, 'stroke-width': 1.5, 'stroke-dasharray': '6 4', 'pointer-events': 'none' }, g); } else if (!s.noline && (s.pts.length > 1 || s.line)) { let d = ''; s.pts.forEach((p, i) => { if (i === 0) d += `M${X(p.t)},${Y(p.v)}`; else d += step ? `H${X(p.t)}V${Y(p.v)}` : `L${X(p.t)},${Y(p.v)}`; }); el('path', { d, fill: 'none', stroke: col, 'stroke-width': s.width || 2.5, opacity: s.opacity ?? 1, 'pointer-events': 'none' }, g); } });
    legend(container, series.map(s => s.name));
  }
  // XY lines with per-series x arrays: series [{name, pts:[[x,y],...], color?}]; tooltip = nearest point per series
  function xyline(container, series, { W = 560, H = 240, xlabel = 'step', fmtV = v => fmt(v, 4), ymin, ymax, refY = null, refLabel = '' } = {}) {
    series = series.filter(s => s.pts && s.pts.length); if (!series.length) { const p = document.createElement('div'); p.className = 'muted small'; p.textContent = 'no data'; container.appendChild(p); return; }
    const m = { l: 56, r: 12, t: 8, b: 28 }; const { svg, g, w, h } = frame(container, W, H, m);
    const xs = series.flatMap(s => s.pts.map(p => p[0])), ys = series.flatMap(s => s.pts.map(p => p[1])).concat(refY != null ? [refY] : []);
    const x0 = Math.min(...xs), x1 = Math.max(...xs); let lo = ymin ?? Math.min(...ys), hi = ymax ?? Math.max(...ys); if (lo === hi) hi = lo + 1; const pad = (hi - lo) * 0.06; if (ymin == null) lo -= pad; if (ymax == null) hi += pad;
    const X = v => (v - x0) / (x1 - x0 || 1) * w, Y = v => h - (v - lo) / (hi - lo) * h; yAxis(g, w, h, Y, ticks(lo, hi, 4).filter(t => t >= lo && t <= hi), v => fmt(v, 3));
    ticks(x0, x1, 6).forEach(t => txt(g, X(t), h + 14, fmtInt(t), { 'text-anchor': 'middle' })); txt(g, w, h + 26, xlabel, { 'text-anchor': 'end', 'font-size': 10 });
    if (refY != null) { el('line', { x1: 0, x2: w, y1: Y(refY), y2: Y(refY), stroke: 'var(--muted)', 'stroke-dasharray': '4 4' }, g); txt(g, w - 2, Y(refY) - 4, refLabel, { 'text-anchor': 'end', 'font-size': 10 }); }
    series.forEach((s, si) => { const col = s.color || SERIES[si % 8]; el('path', { d: s.pts.map((p, i) => (i ? 'L' : 'M') + X(p[0]) + ',' + Y(p[1])).join(''), fill: 'none', stroke: col, 'stroke-width': 2, 'stroke-linejoin': 'round' }, g); if (s.pts.length < 40) s.pts.forEach(p => el('circle', { cx: X(p[0]), cy: Y(p[1]), r: 2.5, fill: col }, g)); });
    const cross = el('line', { y1: 0, y2: h, stroke: 'var(--text2)', 'stroke-dasharray': '3 3', visibility: 'hidden' }, g); const dots = series.map((s, si) => el('circle', { r: 4, fill: s.color || SERIES[si % 8], stroke: 'var(--surface)', 'stroke-width': 2, visibility: 'hidden' }, g));
    const hit = el('rect', { x: 0, y: 0, width: w, height: h, fill: 'transparent' }, g);
    hit.addEventListener('pointermove', e => { const pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY; const q = pt.matrixTransform(g.getScreenCTM().inverse()); const xv = x0 + q.x / w * (x1 - x0); cross.setAttribute('x1', q.x); cross.setAttribute('x2', q.x); cross.setAttribute('visibility', 'visible');
      const rows = series.map((s, si) => { let best = s.pts[0]; for (const p of s.pts) if (Math.abs(p[0] - xv) < Math.abs(best[0] - xv)) best = p; dots[si].setAttribute('cx', X(best[0])); dots[si].setAttribute('cy', Y(best[1])); dots[si].setAttribute('visibility', 'visible'); return { value: fmtV(best[1]), label: `${s.name} @ ${best[0]}`, color: s.color || SERIES[si % 8] }; }); showTip(e, tipHtml(`${xlabel} ${Math.round(xv)}`, rows)); });
    hit.addEventListener('pointerleave', () => { hideTip(); cross.setAttribute('visibility', 'hidden'); dots.forEach(d => d.setAttribute('visibility', 'hidden')); });
    if (series.length > 1) { const d = document.createElement('div'); d.className = 'legend'; series.forEach((s, si) => { const sp = document.createElement('span'); const i2 = document.createElement('i'); i2.style.background = s.color || SERIES[si % 8]; sp.appendChild(i2); sp.appendChild(document.createTextNode(s.name)); d.appendChild(sp); }); container.appendChild(d); }
  }
  // Dot strip aligned under a vbar: groups[i] = values in [0,1]; y axis 0-100¢
  function strip(container, labels, groups, { W = 460, H = 150, tips = [] } = {}) {
    const m = { l: 44, r: 8, t: 6, b: 6 }; const { g, w, h } = frame(container, W, H, m); const n = labels.length; const bwAll = w / n;
    const y = v => h - v * h; yAxis(g, w, h, y, [0, .5, 1], v => Math.round(v * 100) + '¢');
    let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    groups.forEach((vals, i) => { const cx = i * bwAll + bwAll / 2, spread = bwAll * 0.32;
      vals.forEach(v => el('circle', { cx: cx + (rnd() * 2 - 1) * spread, cy: y(v), r: 1.6, fill: SERIES[0], 'fill-opacity': .22 }, g));
      const hit = el('rect', { x: i * bwAll, y: 0, width: bwAll, height: h, fill: 'transparent' }, g);
      hit.addEventListener('pointermove', e => showTip(e, tipHtml(labels[i], tips[i] || []))); hit.addEventListener('pointerleave', hideTip); });
  }
  // Lines at vbar-group centres (aligns with a vbar of the same W): series [{name, values, color?}], marks[i] text above point i
  function binLine(container, labels, series, { W = 460, H = 220, fmtV = v => fmt(v, 3), ymin = 0, marks = [] } = {}) {
    const m = { l: 44, r: 8, t: 14, b: 8 }; const { svg, g, w, h } = frame(container, W, H, m); const n = labels.length, bw = w / n;
    const vals = series.flatMap(s => s.values).filter(v => v != null); const tk = ticks(ymin, Math.max(...vals), 4); const top = Math.max(...vals, tk[tk.length - 1]);
    const y = v => h - (v - ymin) / (top - ymin) * h, x = i => i * bw + bw / 2; yAxis(g, w, h, y, tk, fmtV);
    series.forEach((s, si) => { const col = s.color || SERIES[si % 8]; let d = '', pen = false; s.values.forEach((v, i) => { if (v == null) { pen = false; return; } d += (pen ? 'L' : 'M') + x(i) + ',' + y(v); pen = true; }); el('path', { d, fill: 'none', stroke: col, 'stroke-width': 2, 'stroke-linejoin': 'round' }, g); s.values.forEach((v, i) => { if (v != null) el('circle', { cx: x(i), cy: y(v), r: 4, fill: col, stroke: 'var(--surface)', 'stroke-width': 2 }, g); }); });
    marks.forEach((mk, i) => { if (!mk) return; const tv = Math.max(...series.map(s => s.values[i] ?? 0)); txt(g, x(i), y(tv) - 9, mk, { 'text-anchor': 'middle', 'font-size': 13, 'font-weight': 700 }); });
    for (let i = 0; i < n; i++) { const hit = el('rect', { x: i * bw, y: 0, width: bw, height: h, fill: 'transparent' }, g); hit.addEventListener('pointermove', e => showTip(e, tipHtml(labels[i], series.map((s, si) => ({ value: fmtV(s.values[i]), label: s.name, color: s.color || SERIES[si % 8] }))))); hit.addEventListener('pointerleave', hideTip); }
    if (series.length > 1) legend(container, series.map(s => s.name), 'line', series.map(s => s.color));
  }
  return { binLine, strip, xyline, hbar, vbar, line, scatter, calibration, timeline, legend, fmt, fmtInt, SERIES, showTip, hideTip, tipHtml };
})();
