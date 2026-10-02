# Website

Static site for the long-horizon markets project. A switch in the header shows the same tabs for
Kalshi or Polymarket.

```bash
python website/build_site.py                  # kalshi/results, polymarket/results -> website/data/site.json
cd website && python3 -m http.server 8767     # open http://localhost:8767
```

Re-run `build_site.py` after the analysis scripts change their outputs; the page reads only
`data/site.json`. To publish, serve this folder as is (for Netlify, `netlify.toml` at the repo root
sets `publish = "website"`).
