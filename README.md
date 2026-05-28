# A-Stock Info — AI-Driven Investment Research Platform v3.0

> A股投资信息采集与AI推演平台

---

## Technical Stack / 技术栈

| Layer 层次 | Technology 技术 |
|-----------|----------------|
| **AI Prediction / AI推演** | Kronos-small (NeoQuasar), PyTorch, Monte Carlo Sampling |
| **Backend / 后端** | Python 3.12, FastAPI, SQLAlchemy 2.0, APScheduler |
| **Data Sources / 数据源** | Sina 新浪, BaoStock, AKShare, easyquotation (multi-source failover) |
| **Database / 数据库** | SQLite (dev) / PostgreSQL (prod) |
| **Cache / 缓存** | Redis (optional, degrades to in-memory) |
| **Frontend / 前端** | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, ECharts |
| **Deploy / 部署** | Docker Compose |

## Features / 功能

- **Real-time Quotes / 实时行情**: 四大指数 + 全市场个股快照
- **K-line Charts / K线图表**: 日/周/月/分钟K线，前复权/后复权
- **AI Prediction / AI推演**: Kronos 模型 + 线性回归 + 均线交叉 三模型投票，蒙特卡洛采样置信区间，滚动窗口回测
- **Technical Indicators / 技术指标**: MA, RSI, MACD, Bollinger Bands, Volume Ratio, ATR
- **Financial Analysis / 财务分析**: 季报/年报趋势，暴雷风险检测，超预期判断
- **Announcement Classification / 公告分类**: 重大违法、股东减持、重大利好
- **Watchlist / 自选股**: 分组管理，持仓盈亏
- **Alert Rules / 告警规则**: 价格/涨跌幅/量比触发，Bark推送

---

## Quick Start / 快速启动

### Prerequisites / 环境要求

- Python 3.12+
- Node.js 18+
- (Optional) Redis for caching

### Backend / 后端

```bash
cd a-stock-info/backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend / 前端

```bash
cd a-stock-info/frontend
npm install
npm run dev
```

Frontend proxies `/api` to `localhost:8001` by default. 前端默认代理 `/api` 到 `localhost:8001`.

### Docker / Docker部署

```bash
docker compose up -d
```

---

## Project Structure / 项目结构

```
a-stock-info/
├── backend/
│   ├── main.py              # FastAPI entry
│   ├── config.py             # Settings
│   ├── database.py           # SQLAlchemy engine
│   ├── models/               # ORM models (7 tables)
│   ├── schemas/              # Pydantic schemas
│   ├── routers/              # API routes
│   ├── services/             # Business logic
│   ├── crawlers/             # Data collectors
│   ├── datasources/          # Multi-source failover layer
│   ├── predictors/           # AI prediction engine
│   │   ├── kronos_model/     # Kronos model core
│   │   ├── kronos_predictor.py
│   │   ├── indicators.py     # Technical indicators
│   │   └── backtest.py       # Rolling window backtest
│   ├── scheduler.py          # APScheduler jobs
│   └── cache.py              # Redis/memory cache
├── frontend/
│   └── src/
│       ├── api/              # Axios client
│       ├── components/       # Reusable components
│       ├── hooks/            # TanStack Query hooks
│       ├── pages/            # Page components
│       ├── store/            # Zustand state
│       └── utils/            # Format helpers
└── tests/
```

## API / 接口

Base URL: `/api/v1`

| Endpoint | Description 描述 |
|----------|-----------------|
| `GET /stocks` | Search stocks / 股票搜索 |
| `GET /stocks/{code}/quote` | Real-time quote / 实时行情 |
| `GET /stocks/{code}/kline` | K-line history / K线历史 |
| `GET /stocks/{code}/predict` | AI prediction / AI推演 |
| `GET /stocks/{code}/financials` | Financial data / 财务数据 |
| `GET /market/overview` | Market overview / 大盘概况 |
| `GET /market/sectors` | Sector heatmap / 板块热力图 |
| `GET /news` | Financial news / 财经新闻 |
| `GET/POST/PUT/DELETE /watchlist` | Watchlist CRUD / 自选股 |
| `GET/POST/PUT/DELETE /alerts` | Alert rules / 告警规则 |
| `GET /system/status` | System health / 系统状态 |

---

## Disclaimer / 免责声明

AI predictions are for reference only and do not constitute investment advice.

AI推演仅供参考，不构成投资建议。

---

**Version**: 3.0  |  **License**: MIT
