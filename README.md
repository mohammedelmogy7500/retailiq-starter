# RetailIQ — Business Intelligence & Sales Forecasting

A full-stack portfolio starter: **React + TypeScript + FastAPI**. It includes sales analytics, product and customer segmentation, profit-aware dashboards, and a transparent time-series revenue forecast baseline.

**The included data is synthetic** and is designed for development, testing, and demos. It must not be presented as real company performance.

## What is already implemented

- **Sales KPIs**: historical revenue, available product profit, profit margin, order count, identifiable customer count, average order value, and latest-month revenue growth.
- **Monthly analytics**: trend chart, product ranking, revenue by customer segment, and product profitability table.
- **Customer intelligence**: transparent heuristic RFM buckets (Champions / At Risk / Loyal / Potential / Regular).
- **Forecast**: three next-month revenue estimates. Seasonal-naive baseline for 15+ completed months; otherwise 3-month moving average. A holdout backtest reports MAE and sMAPE where history allows.
- **CSV analysis**: upload and analyze supported CSVs without persisting their contents to the backend. API calls analyze their own payload (no cross-user global upload state).
- **Tests**: health, demo, formula correctness, Superstore profit handling, UCI cancellations and profit missingness, and bad schema.

## Repository structure

```text
retailiq-starter/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── analytics.py          # CSV normalization, KPIs, RFM, forecast
│   │   └── main.py               # FastAPI endpoints
│   ├── data/
│   │   ├── generate_demo.py      # Deterministic demo-data generator
│   │   └── sample_sales.csv      # Synthetic sample transactions
│   ├── tests/
│   │   └── test_api.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx               # Dashboard, upload, charts
│   │   ├── types.ts
│   │   ├── styles.css
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   ├── .env.example
│   └── index.html
├── LICENSE
└── README.md
```

## Local setup (Windows PowerShell)

Prerequisites: Python 3.10+ and Node.js 20+ (which includes npm). If `npm` is not recognized, install Node.js LTS from https://nodejs.org, then reopen the terminal.

### Terminal 1: backend

```powershell
cd retailiq-starter\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`. Swagger API docs are at `http://localhost:8000/docs`.

### Terminal 2: frontend

```powershell
cd retailiq-starter\frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

**macOS / Linux:** replace the Windows activate command with `source .venv/bin/activate`. Run with `python3` as appropriate.

### Tests

```powershell
cd retailiq-starter\backend
python -m pytest -q tests
```

### Regenerate synthetic data

```powershell
cd retailiq-starter\backend
python data/generate_demo.py
```

## Upload your data

Use the **Upload CSV** button. Supported column schemas (case-insensitive; spaces and underscores are ignored):

1. **RetailIQ canonical**:
   `order_id, order_date, customer_id, product_id, product_name, category, segment, region, quantity, unit_price, unit_cost, discount_pct`
   - `discount_pct` is optional and is a number in `[0,1]` (e.g. `0.2` for 20%).
   - Row revenue = quantity × unit price × (1 − discount_pct).
   - Row gross profit = revenue − quantity × unit cost.
   - Default unit of currency: USD; configurable currency support is planned.
2. **Sample Superstore**:
   `Order ID, Order Date, Customer ID, Product ID, Product Name, Category, Segment, Region, Quantity, Sales, Profit`, plus other optional columns.
   - Uses source **Sales** and **Profit** as already reported. Discounts are **not** applied a second time.
   - Currency: USD.
3. **UCI Online Retail**:
   `InvoiceNo, InvoiceDate, StockCode, Description, Quantity, UnitPrice, CustomerID, Country`.
   - Cancellations (InvoiceNo beginning with `C`) and non-positive quantities/prices are excluded from positive-sales analysis.
   - Revenue = quantity × UnitPrice. **Profit is unavailable** because UCI doesn't supply cost or profit.
   - Currency: GBP.

**Upload constraints:** up to 8 MB and 300,000 rows in this starter. Files are processed in memory per request and not saved. Unknown customers are excluded from identifiable customer counts and RFM. Returns are **excluded**, not reconciled as net revenue. For true net-revenue reporting, next build a returns/reconciliation module with credit-note matching and accounting policy.

## Dataset suggestions and source attribution

- [Tableau — finding good datasets / Superstore](https://help.tableau.com/current/pro/desktop/en-gb/find_good_datasets.htm). Superstore is a Tableau sample data source with profit, product hierarchy, dates, and geography. Obtain a CSV version of the sample `Orders` sheet if you want to upload it here. Verify the sample's terms before republishing it.
- [UCI Online Retail (dataset 352)](https://archive.ics.uci.edu/dataset/352/online+retail). Real transactions from 2010-12-01 through 2011-12-09, with invoice, product, date, quantity, UnitPrice, customer, and country. No cost/profit columns. Old data isn't evidence of current retail patterns.

The package ships only our **synthetic dataset**, not copies of these external datasets.

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/demo` | Analyze included synthetic dataset |
| POST | `/api/analyze` | Multipart form-data file `file` with `.csv` extension, returns analysis JSON |

Example:

```bash
curl -X POST -F 'file=@backend/data/sample_sales.csv' http://localhost:8000/api/analyze
```

## Definitions and limitations

- **Revenue**: positive transaction sales only; canonical sample discounts are applied before revenue calculation.
- **Product profit**: for canonical records, discounted revenue minus entered unit product costs; for Superstore, the source-reported line `Profit`. These definitions may differ. Our calculation does **not** deduct marketing, payroll, taxes, or overhead. It is not necessarily accounting gross profit or net profit.
- **Margin**: available product profit / revenue; negative gross profit is preserved where supplied by the source.
- **Average order value**: total positive sales revenue / unique order IDs.
- **Month-over-month growth**: last available month's revenue vs the previous month, where the denominator is nonzero. A dataset ending mid-month can make this misleading; a stronger production version needs explicit data watermark/close calendars.
- **Forecast**: seasonal-naive (same calendar month a year ago) if 15+ completed months of data; otherwise a 3-month moving average. A month matching the server's current calendar month is excluded as incomplete. Missing historical calendar months are treated as zero sales, which must be reviewed in real data.
- **Backtest**: predict the last 3 complete historic months using only earlier months, then calculate MAE and sMAPE. This is a small illustrative holdout, not comprehensive model validation, and doesn't provide calibrated prediction intervals.
- **Customer RFM**: recency, unique-order frequency, and monetary spending ranked within the current dataset, with heuristic segments; it's not a trained ML clustering model.
- **Single analysis response**: uploaded data is processed in one request and is not stored. For a production multi-tenant SaaS, use authentication, per-user dataset storage, rate limits, malware/file scanning, more stringent limits, auditing, and asynchronous jobs.
- **Privacy**: customer IDs may be sensitive if real; avoid uploading personal data to public instances without appropriate safeguards.

## Deployment approach (future phase)

- Frontend: static React build (`npm run build`) on Vercel or Cloudflare Pages.
- Backend: Python-supported host running `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set `CORS_ORIGINS` to your deployed frontend URL. Free-tier resource quotas and availability change; validate before deploying.
- Database: Supabase/PostgreSQL for authorized user accounts and persisted dataset metadata, with object storage for uploads. This MVP deliberately does not write to any database or use hosted storage.
- Set `VITE_API_BASE_URL` on frontend to the deployed API URL. Set it to blank for local development (Vite proxy).

## Next development milestones

1. **Phase 2:** data-quality report, upload column mapping, returns reconciliation, filtering by date/region/category.
2. **Phase 3:** persist datasets with authentication and tenant isolation, PostgreSQL tables, async ETL.
3. **Phase 4:** upgrade forecasting to monthly SARIMA/ETS and gradient-boosted feature model; rolling-origin backtesting, SMAPE/MASE/WAPE, model selection, prediction intervals.
4. **Phase 5:** profitability drivers and customer cohorts, product lifecycle patterns, basket-level recommendations; exportable reports.
5. **Phase 6:** CI tests, deployment, performance benchmarking, monitoring, professional case-study README with real verified results.

## Resume-ready description (after adding your own results)

> Built a React + FastAPI retail intelligence dashboard that ingests transaction CSVs, validates revenue/profit metrics, segments customers using RFM analysis, and forecasts monthly sales with leakage-aware backtesting. Developed responsive visualizations, dataset-specific parsing, API tests, and configurable local/deployment architecture.

**Do not claim forecast accuracy, percentage improvements, or business impact without measuring them on the chosen real dataset.**
