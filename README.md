# Hermes Token Dashboard

Local token usage visualization for [Hermes Agent](https://hermes-agent.nousresearch.com) — zero-config, zero external Python dependencies.

Reads `~/.hermes/state.db` and serves a dark-themed dashboard with GitHub-style heatmap, trend charts, model breakdown, and cost analysis.

![screenshot](https://img.shields.io/badge/status-working-brightgreen)

## Quick Start

```bash
python3 dashboard.py
```

Opens automatically at `http://127.0.0.1:8768`. Press `Ctrl+C` to stop.

**Custom port:**
```bash
python3 dashboard.py --port 9999
PORT=9999 python3 dashboard.py
```

## Requirements

- Python 3.7+ (stdlib only — no pip install needed)
- Hermes Agent installed (`~/.hermes/state.db` must exist)
- Modern browser (Chart.js loaded via CDN)

## What You Get

| Module | Description |
|--------|-------------|
| 📊 Stats Cards | Total sessions, tokens, cost, cache hits, daily average |
| 🗺 Activity Heatmap | GitHub-style 26-week grid, color-coded by daily token volume |
| 📈 Trend Chart | Input vs Output line chart (last 90 days) |
| 🎯 Model Distribution | Doughnut chart of token usage by model |
| 💾 I/O Ratio | Bar chart of daily input/output ratio |
| 💵 Cost Trend | Bar chart of daily estimated cost |
| 📋 Sessions Table | Last 50 sessions with model, tokens, cost, message count |

## How It Works

- **Backend**: Python `http.server` serves two endpoints:
  - `/` → dashboard HTML (Chart.js rendered in browser)
  - `/api/data` → JSON stats queried live from `~/.hermes/state.db`
- **Data source**: `sessions` table in Hermes state.db (input/output/cache/cost per session)
- **Charts**: Chart.js v4 loaded from CDN, rendered client-side
- **No data leaves your machine** — everything is local

## Project Structure

```
hermes-token-dashboard/
├── dashboard.py    # single-file app (server + queries + HTML template)
├── README.md
```

## Inspiration

Layout and heatmap design inspired by [TokenTracker](https://github.com/mm7894215/TokenTracker) — stripped down to focus exclusively on Hermes Agent.

## License

MIT
