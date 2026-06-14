#!/usr/bin/env python3
"""
Hermes Token Dashboard — local token usage visualization for Hermes Agent.

Reads ~/.hermes/state.db (SQLite) and serves a dark-themed dashboard with:
- GitHub-style activity heatmap
- Daily input/output trend charts
- Model distribution doughnut
- Cost trend, I/O ratio, recent sessions table

Zero external Python dependencies — stdlib only (http.server + sqlite3 + json).
Charts rendered via Chart.js CDN (loaded in browser).

Usage:
    python3 dashboard.py                  # default port 8768
    python3 dashboard.py --port 9999      # custom port
    PORT=9999 python3 dashboard.py        # via env var

Inspired by TokenTracker (github.com/mm7894215/TokenTracker).
"""

import http.server
import json
import os
import sqlite3
import sys
import webbrowser
from datetime import datetime
from urllib.parse import urlparse

# ── Configuration ────────────────────────────────────────────────────────────
DB_PATH = os.path.expanduser("~/.hermes/state.db")
HOST = "127.0.0.1"
DEFAULT_PORT = 8768


def get_port():
    """Resolve port: CLI arg > env var > default."""
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            return int(sys.argv[i + 1])
        if arg.startswith("--port="):
            return int(arg.split("=")[1])
    return int(os.environ.get("PORT", DEFAULT_PORT))


PORT = get_port()


# ── HTML template (single file, Chart.js CDN) ────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hermes Token Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #0d1117;
    --card: #161b22;
    --border: #30363d;
    --text: #c9d1d9;
    --muted: #8b949e;
    --accent: #58a6ff;
    --green: #3fb950;
    --orange: #d2991d;
    --red: #f85149;
    --heatmap-0: #161b22;
    --heatmap-1: #0e4429;
    --heatmap-2: #006d32;
    --heatmap-3: #26a641;
    --heatmap-4: #39d353;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    line-height: 1.5;
    min-height: 100vh;
  }
  .container { max-width: 1200px; margin: 0 auto; padding: 24px 20px; }

  .header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 28px; padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
  }
  .header h1 { font-size: 22px; font-weight: 600; color: #f0f6fc; }
  .header .badge { font-size: 12px; color: var(--muted); background: var(--card);
    padding: 4px 10px; border-radius: 12px; border: 1px solid var(--border); }
  .refresh-btn {
    background: var(--card); border: 1px solid var(--border); color: var(--text);
    padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px;
    transition: background .15s;
  }
  .refresh-btn:hover { background: #1f2937; }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 14px;
    margin-bottom: 28px;
  }
  .stat-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px 18px;
  }
  .stat-card .label { font-size: 12px; color: var(--muted); margin-bottom: 4px; text-transform: uppercase; letter-spacing: .5px; }
  .stat-card .value { font-size: 26px; font-weight: 700; color: #f0f6fc; }
  .stat-card .sub { font-size: 12px; color: var(--muted); margin-top: 2px; }
  .stat-card.accent .value { color: var(--accent); }
  .stat-card.green .value { color: var(--green); }

  .charts-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin-bottom: 28px;
  }
  @media (max-width: 768px) { .charts-grid { grid-template-columns: 1fr; } }

  .chart-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
  }
  .chart-card.full { grid-column: 1 / -1; }
  .chart-card h2 { font-size: 14px; color: var(--muted); margin-bottom: 12px; font-weight: 500; }
  .chart-card canvas { width: 100% !important; height: 280px !important; }

  .heatmap-grid { display: flex; gap: 3px; }
  .heatmap-week { display: flex; flex-direction: column; gap: 3px; }
  .heatmap-cell {
    width: 13px; height: 13px; border-radius: 2px;
    background: var(--heatmap-0);
  }
  .heatmap-cell.l1 { background: var(--heatmap-1); }
  .heatmap-cell.l2 { background: var(--heatmap-2); }
  .heatmap-cell.l3 { background: var(--heatmap-3); }
  .heatmap-cell.l4 { background: var(--heatmap-4); }
  .heatmap-legend {
    display: flex; align-items: center; gap: 4px; margin-top: 8px;
    font-size: 11px; color: var(--muted); justify-content: flex-end;
  }
  .heatmap-legend .swatch { width: 11px; height: 11px; border-radius: 2px; }

  .session-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .session-table th {
    text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border);
    color: var(--muted); font-weight: 500; font-size: 12px;
  }
  .session-table td {
    padding: 8px 10px; border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  .session-table tr:hover td { background: rgba(255,255,255,.02); }
  .model-tag {
    display: inline-block; padding: 2px 7px; border-radius: 4px;
    font-size: 11px; background: rgba(88,166,255,.12); color: var(--accent);
  }
  .cost { color: var(--green); font-variant-numeric: tabular-nums; }
  .no-data {
    text-align: center; padding: 40px; color: var(--muted); font-size: 14px;
  }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <h1>🦞 Hermes Token Dashboard</h1>
    </div>
    <div style="display:flex;align-items:center;gap:12px;">
      <span class="badge" id="updateTime">Loading...</span>
      <button class="refresh-btn" onclick="loadData()">⟳ Refresh</button>
    </div>
  </div>

  <div class="stats-grid" id="statsGrid"></div>

  <div class="chart-card full">
    <h2>📊 Token Activity Heatmap (GitHub Style)</h2>
    <div id="heatmap"></div>
  </div>

  <div class="charts-grid">
    <div class="chart-card">
      <h2>📈 Daily Token Trend</h2>
      <canvas id="trendChart"></canvas>
    </div>
    <div class="chart-card">
      <h2>🎯 Model Distribution</h2>
      <canvas id="modelChart"></canvas>
    </div>
  </div>

  <div class="charts-grid">
    <div class="chart-card">
      <h2>💾 Input/Output Ratio</h2>
      <canvas id="ioChart"></canvas>
    </div>
    <div class="chart-card">
      <h2>💵 Daily Cost Trend</h2>
      <canvas id="costChart"></canvas>
    </div>
  </div>

  <div class="chart-card full">
    <h2>📋 Recent Sessions</h2>
    <div style="overflow-x:auto;">
      <table class="session-table" id="sessionTable"></table>
    </div>
  </div>
</div>

<script>
let trendCtx, modelCtx, ioCtx, costCtx;
let trendChart, modelChart, ioChart, costChart;

function fmt(n) {
  if (n == null) return '—';
  if (n >= 1_000_000) return (n/1_000_000).toFixed(2) + 'M';
  if (n >= 1_000) return (n/1_000).toFixed(1) + 'K';
  return n.toLocaleString();
}

function fmtCost(n) {
  if (n == null || n === 0) return '$0.00';
  return '$' + n.toFixed(4);
}

async function loadData() {
  const resp = await fetch('/api/data');
  const data = await resp.json();
  document.getElementById('updateTime').textContent = 'Updated: ' + data.generated_at;

  renderStats(data);
  renderHeatmap(data);
  renderTrend(data);
  renderModel(data);
  renderIO(data);
  renderCost(data);
  renderSessions(data);
}

function renderStats(d) {
  const s = d.summary;
  const cards = [
    { label: 'Total Sessions', value: s.total_sessions, sub: s.active_days + ' active days', cls: '' },
    { label: 'Total Tokens', value: fmt(s.total_tokens), sub: 'Input ' + fmt(s.total_input) + ' / Output ' + fmt(s.total_output), cls: 'accent' },
    { label: 'Est. Cost', value: fmtCost(s.total_cost), sub: '', cls: 'green' },
    { label: 'Cache Read', value: fmt(s.total_cache_read), sub: 'Cache Write ' + fmt(s.total_cache_write), cls: '' },
    { label: 'Daily Avg', value: fmt(s.avg_daily_tokens), sub: Math.round(s.avg_daily_tokens / 1000) + 'K/day', cls: '' },
  ];
  document.getElementById('statsGrid').innerHTML = cards.map(c =>
    `<div class="stat-card ${c.cls}"><div class="label">${c.label}</div><div class="value">${c.value}</div><div class="sub">${c.sub}</div></div>`
  ).join('');
}

function renderHeatmap(d) {
  const hd = d.heatmap_data;
  if (!hd.dates.length) {
    document.getElementById('heatmap').innerHTML = '<div class="no-data">No heatmap data yet</div>';
    return;
  }

  const dates = hd.dates;
  const values = hd.values;
  const maxVal = Math.max(1, ...values);

  const valMap = {};
  dates.forEach((dt, i) => { valMap[dt] = values[i]; });

  const now = new Date();
  const endDate = new Date(now);
  endDate.setDate(endDate.getDate() - endDate.getDay());
  const startDate = new Date(endDate);
  startDate.setDate(startDate.getDate() - 26 * 7 + 1);

  const weeks = [];
  const cur = new Date(startDate);
  while (cur <= endDate) {
    const week = [];
    for (let d = 0; d < 7; d++) {
      const ds = cur.toISOString().slice(0, 10);
      week.push({ date: ds, value: valMap[ds] || 0 });
      cur.setDate(cur.getDate() + 1);
    }
    weeks.push(week);
  }

  function colorLevel(v) {
    if (v === 0) return '';
    const pct = v / maxVal;
    if (pct < 0.25) return 'l1';
    if (pct < 0.5) return 'l2';
    if (pct < 0.75) return 'l3';
    return 'l4';
  }

  const dayLabels = ['', 'Mon', '', 'Wed', '', 'Fri', ''];
  let gridHtml = '<div style="display:flex;align-items:flex-start;">';
  gridHtml += '<div style="display:flex;flex-direction:column;gap:3px;margin-right:6px;font-size:10px;color:var(--muted);padding-top:2px;">';
  dayLabels.forEach(l => { gridHtml += `<div style="height:13px;line-height:13px;">${l}</div>`; });
  gridHtml += '</div>';
  gridHtml += '<div class="heatmap-grid">';
  weeks.forEach(week => {
    gridHtml += '<div class="heatmap-week">';
    week.forEach(day => {
      const title = `${day.date}: ${fmt(day.value)} tokens`;
      gridHtml += `<div class="heatmap-cell ${colorLevel(day.value)}" title="${title}"></div>`;
    });
    gridHtml += '</div>';
  });
  gridHtml += '</div></div>';

  gridHtml += `<div class="heatmap-legend">
    Less <span class="swatch" style="background:var(--heatmap-0)"></span>
    <span class="swatch" style="background:var(--heatmap-1)"></span>
    <span class="swatch" style="background:var(--heatmap-2)"></span>
    <span class="swatch" style="background:var(--heatmap-3)"></span>
    <span class="swatch" style="background:var(--heatmap-4)"></span> More
  </div>`;

  document.getElementById('heatmap').innerHTML = gridHtml;
}

function renderTrend(d) {
  const td = d.trend_data;
  if (trendChart) trendChart.destroy();
  trendChart = new Chart(trendCtx, {
    type: 'line',
    data: {
      labels: td.labels,
      datasets: [
        { label: 'Input', data: td.input, borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,.08)', fill: true, tension: .3, pointRadius: 3 },
        { label: 'Output', data: td.output, borderColor: '#3fb950', backgroundColor: 'rgba(63,185,80,.08)', fill: true, tension: .3, pointRadius: 3 },
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#8b949e', usePointStyle: true, boxWidth: 8 } } },
      scales: {
        x: { ticks: { color: '#484f58', maxTicksLimit: 14 }, grid: { color: '#21262d' } },
        y: { ticks: { color: '#484f58', callback: v => fmt(v) }, grid: { color: '#21262d' }, beginAtZero: true }
      }
    }
  });
}

function renderModel(d) {
  const md = d.model_data;
  if (modelChart) modelChart.destroy();
  const colors = ['#58a6ff','#3fb950','#d2991d','#f85149','#bc8cff','#f778ba','#79c0ff'];
  modelChart = new Chart(modelCtx, {
    type: 'doughnut',
    data: {
      labels: md.labels,
      datasets: [{
        data: md.values, backgroundColor: colors.slice(0, md.labels.length),
        borderColor: '#161b22', borderWidth: 2
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#8b949e', padding: 16, usePointStyle: true, boxWidth: 8 } },
        tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${fmt(ctx.raw)} tokens` } }
      }
    }
  });
}

function renderIO(d) {
  const td = d.trend_data;
  if (ioChart) ioChart.destroy();
  const ratios = td.input.map((v, i) => {
    const out = td.output[i] || 1;
    return v / out;
  });
  ioChart = new Chart(ioCtx, {
    type: 'bar',
    data: {
      labels: td.labels,
      datasets: [
        { label: 'Input/Output Ratio', data: ratios, backgroundColor: '#58a6ff', borderRadius: 3 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#484f58', maxTicksLimit: 14 }, grid: { display: false } },
        y: { ticks: { color: '#484f58' }, grid: { color: '#21262d' }, beginAtZero: true }
      }
    }
  });
}

function renderCost(d) {
  const td = d.trend_data;
  if (costChart) costChart.destroy();
  costChart = new Chart(costCtx, {
    type: 'bar',
    data: {
      labels: td.labels,
      datasets: [
        { label: 'Daily Cost', data: td.cost, backgroundColor: td.cost.map(v => v > 0.01 ? '#3fb950' : '#d2991d'), borderRadius: 3 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ' ' + fmtCost(ctx.raw) } }
      },
      scales: {
        x: { ticks: { color: '#484f58', maxTicksLimit: 14 }, grid: { display: false } },
        y: { ticks: { color: '#484f58', callback: v => '$' + v.toFixed(3) }, grid: { color: '#21262d' }, beginAtZero: true }
      }
    }
  });
}

function renderSessions(d) {
  const rows = d.recent_sessions;
  if (!rows.length) {
    document.getElementById('sessionTable').innerHTML = '<tr><td colspan="7" class="no-data">No sessions yet</td></tr>';
    return;
  }
  const header = `<tr><th>Time</th><th>Model</th><th>Input</th><th>Output</th><th>Cache Read</th><th>Cost</th><th>Messages</th></tr>`;
  const body = rows.map(r => `<tr>
    <td>${r.time}</td>
    <td><span class="model-tag">${r.model}</span></td>
    <td>${fmt(r.input_tokens)}</td>
    <td>${fmt(r.output_tokens)}</td>
    <td>${fmt(r.cache_read)}</td>
    <td class="cost">${fmtCost(r.cost)}</td>
    <td>${r.msg_count}</td>
  </tr>`).join('');
  document.getElementById('sessionTable').innerHTML = header + body;
}

window.onload = () => {
  trendCtx = document.getElementById('trendChart').getContext('2d');
  modelCtx = document.getElementById('modelChart').getContext('2d');
  ioCtx = document.getElementById('ioChart').getContext('2d');
  costCtx = document.getElementById('costChart').getContext('2d');
  loadData();
};
</script>
</body>
</html>"""


# ── Data Queries ─────────────────────────────────────────────────────────────
def query_db():
    """Query state.db and return all stats as a dict."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Summary
    cur.execute("""
        SELECT
            COUNT(*) as total_sessions,
            COALESCE(SUM(input_tokens), 0) as total_input,
            COALESCE(SUM(output_tokens), 0) as total_output,
            COALESCE(SUM(cache_read_tokens), 0) as total_cache_read,
            COALESCE(SUM(cache_write_tokens), 0) as total_cache_write,
            COALESCE(SUM(reasoning_tokens), 0) as total_reasoning,
            COALESCE(SUM(estimated_cost_usd), 0) as total_cost,
            COUNT(DISTINCT date(started_at, 'unixepoch', 'localtime')) as active_days
        FROM sessions
        WHERE input_tokens > 0
    """)
    summary = dict(cur.fetchone())
    summary["total_tokens"] = summary["total_input"] + summary["total_output"]
    summary["avg_daily_tokens"] = (
        summary["total_tokens"] / summary["active_days"]
        if summary["active_days"] > 0 else 0
    )

    # 2. Daily trend (last 90 days)
    cur.execute("""
        SELECT
            date(started_at, 'unixepoch', 'localtime') as day,
            COALESCE(SUM(input_tokens), 0) as input_tokens,
            COALESCE(SUM(output_tokens), 0) as output_tokens,
            COALESCE(SUM(estimated_cost_usd), 0) as cost,
            COUNT(*) as session_count
        FROM sessions
        WHERE input_tokens > 0
        GROUP BY day
        ORDER BY day
        LIMIT 90
    """)
    trend_rows = cur.fetchall()
    trend_data = {
        "labels": [r["day"] for r in trend_rows],
        "input": [r["input_tokens"] for r in trend_rows],
        "output": [r["output_tokens"] for r in trend_rows],
        "cost": [round(r["cost"], 6) for r in trend_rows],
        "sessions": [r["session_count"] for r in trend_rows],
    }

    # 3. Model breakdown
    cur.execute("""
        SELECT
            model,
            COALESCE(SUM(input_tokens + output_tokens), 0) as total_tokens,
            COUNT(*) as session_count
        FROM sessions
        WHERE input_tokens > 0
        GROUP BY model
        ORDER BY total_tokens DESC
    """)
    model_rows = cur.fetchall()
    model_data = {
        "labels": [r["model"] or "unknown" for r in model_rows],
        "values": [r["total_tokens"] for r in model_rows],
        "counts": [r["session_count"] for r in model_rows],
    }

    # 4. Heatmap data
    cur.execute("""
        SELECT
            date(started_at, 'unixepoch', 'localtime') as day,
            COALESCE(SUM(input_tokens + output_tokens), 0) as total_tokens
        FROM sessions
        WHERE input_tokens > 0
        GROUP BY day
        ORDER BY day
    """)
    heat_rows = cur.fetchall()
    heatmap_data = {
        "dates": [r["day"] for r in heat_rows],
        "values": [r["total_tokens"] for r in heat_rows],
    }

    # 5. Recent sessions (last 50)
    cur.execute("""
        SELECT
            id,
            model,
            input_tokens,
            output_tokens,
            cache_read_tokens,
            estimated_cost_usd,
            message_count,
            datetime(started_at, 'unixepoch', 'localtime') as start_time
        FROM sessions
        ORDER BY started_at DESC
        LIMIT 50
    """)
    session_rows = cur.fetchall()
    recent_sessions = [{
        "id": r["id"],
        "model": r["model"] or "unknown",
        "time": r["start_time"][:16] if r["start_time"] else "—",
        "input_tokens": r["input_tokens"],
        "output_tokens": r["output_tokens"],
        "cache_read": r["cache_read_tokens"],
        "cost": round(r["estimated_cost_usd"], 6) if r["estimated_cost_usd"] else 0,
        "msg_count": r["message_count"],
    } for r in session_rows]

    conn.close()

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "trend_data": trend_data,
        "model_data": model_data,
        "heatmap_data": heatmap_data,
        "recent_sessions": recent_sessions,
    }


# ── HTTP Server ──────────────────────────────────────────────────────────────
class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/data":
            data = query_db()
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
            return

        # Default: serve HTML
        body = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        if "/api/data" in str(args):
            print(f"  📊 Data refresh — {args[0]}")


def main():
    print(f"🦞 Hermes Token Dashboard")
    print(f"   Database: {DB_PATH}")
    print(f"   Starting: http://{HOST}:{PORT}")
    print()

    server = http.server.HTTPServer((HOST, PORT), DashboardHandler)
    webbrowser.open(f"http://{HOST}:{PORT}")
    print(f"   ✅ Browser opened — Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n   👋 Shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
