# 📊 Hermes Token Dashboard

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/Jokeyou/hermes-token-dashboard/pulls)

> **零依赖 · 零配置 · 一键启动的 AI Token 用量看板。**
>
> 让每一次对话的成本，清清楚楚。

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

## 🤝 一起开发！

> **让 AI 使用成本透明化，从本地工具开始。**

欢迎对数据可视化、Python 或 AI 工具链感兴趣的朋友参与：

| 方向 | 做什么 |
|------|--------|
| 📊 **可视化** | 新图表类型、导出报告（PDF/PNG） |
| 🔧 **后端** | 支持更多 Agent 框架（Claude Code、OpenAI）、多数据库适配 |
| 🎨 **前端** | Chart.js 主题优化、移动端适配 |
| 📝 **文档** | 多语言翻译、部署教程 |

```bash
git checkout -b feature/your-feature
git commit -m 'feat: add your feature'
git push origin feature/your-feature
```

## 📄 License

MIT © [Jokeyou](https://github.com/Jokeyou)

---

**⭐ 觉得有用就点个 Star！**
