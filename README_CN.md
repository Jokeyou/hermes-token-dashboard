# Hermes Token Dashboard

[Hermes Agent](https://hermes-agent.nousresearch.com) 本地 Token 用量可视化面板 — 零配置，零外部 Python 依赖。

读取 `~/.hermes/state.db`，提供暗色主题仪表盘，包含 GitHub 风格热力图、趋势图、模型分布和费用分析。

## 快速开始

```bash
python3 dashboard.py
```

自动打开浏览器访问 `http://127.0.0.1:8768`，`Ctrl+C` 停止。

**自定义端口：**
```bash
python3 dashboard.py --port 9999
PORT=9999 python3 dashboard.py
```

## 环境要求

- Python 3.7+（仅标准库，无需 pip 安装）
- Hermes Agent 已安装（`~/.hermes/state.db` 存在）
- 现代浏览器（Chart.js 通过 CDN 加载）

## 功能模块

| 模块 | 说明 |
|------|------|
| 📊 核心指标卡片 | 总会话数、Token 总量、费用、缓存命中、日均用量 |
| 🗺 用量热力图 | 26 周 GitHub 风格日历热力图，深浅绿按日 Token 量着色 |
| 📈 每日趋势图 | Input vs Output 折线图（最近 90 天） |
| 🎯 模型分布图 | 各模型 Token 用量甜甜圈图 |
| 💾 I/O 比例图 | 每日 Input/Output 比值柱状图 |
| 💵 费用趋势图 | 每日预估费用柱状图 |
| 📋 会话列表 | 最近 50 条会话（模型/Token/费用/消息数） |

## 实现原理

- **后端**：Python `http.server` 提供两个端点：
  - `/` → 仪表盘 HTML（Chart.js 浏览器端渲染）
  - `/api/data` → 从 `~/.hermes/state.db` 实时查询的 JSON 统计数据
- **数据源**：Hermes state.db 的 `sessions` 表（逐会话记录 input/output/cache/cost）
- **图表**：Chart.js v4 CDN 加载，客户端渲染
- **数据不出本地** — 全部在本地完成

## 数据字段说明

从 Hermes `state.db` 的 `sessions` 表中提取以下字段：

| 字段 | 说明 |
|------|------|
| `input_tokens` | 输入 Token 数（含上下文） |
| `output_tokens` | 输出 Token 数 |
| `cache_read_tokens` | 缓存命中读取的 Token 数 |
| `cache_write_tokens` | 新写入缓存的 Token 数 |
| `reasoning_tokens` | 推理 Token 数（如 DeepSeek-R1） |
| `estimated_cost_usd` | 预估费用（美元） |
| `model` | 使用的模型名称 |
| `started_at` | 会话开始时间 |

注意：`messages` 表虽有 `token_count` 字段，但不区分 input/output，因此本工具所有统计均基于 `sessions` 表。

## 项目结构

```
hermes-token-dashboard/
├── dashboard.py    # 单文件应用（服务端 + SQL 查询 + HTML 模板）
├── README.md       # English
├── README_CN.md    # 中文
```

## 设计灵感

布局和热力图设计借鉴 [TokenTracker](https://github.com/mm7894215/TokenTracker)，但精简为只监控 Hermes Agent 一个工具。

## License

MIT
