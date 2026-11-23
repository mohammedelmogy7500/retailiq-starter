import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, BarChart3,
  Check, CircleHelp, DollarSign, FileUp,
  Layers3, LoaderCircle, Package, RefreshCw, ShoppingBag, Sparkles,
  Target, TrendingUp, Users, Wallet, AlertTriangle,
} from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, BarChart, Bar, CartesianGrid,
  XAxis, YAxis, Tooltip, LineChart, Line, PieChart, Pie, Cell,
} from 'recharts';
import type { DatasetResponse } from './types';

const API = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
const PALETTE = ['#a38af8', '#30cfa8', '#69aefa', '#f2bc6f', '#fb8298', '#bde2a5'];

function shortMonth(s: string) {
  const [y, m] = s.split('-');
  return new Date(Number(y), Number(m) - 1, 1).toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
}
function currency(v: number | null | undefined, code: string, compact = false) {
  if (v === null || v === undefined) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: code, notation: compact ? 'compact' : 'standard',
    maximumFractionDigits: compact ? 1 : 2,
  }).format(v);
}
function numeric(v: number | null | undefined) {
  return v == null ? '—' : new Intl.NumberFormat('en-US').format(v);
}
const signed = (n: number | null | undefined) => n == null ? '—' : `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`;

function InfoTile({ icon: Icon, label, value, foot, accent = 'purple', trend }: {
  icon: typeof DollarSign; label: string; value: string; foot: string; accent?: string; trend?: number | null;
}) {
  return <div className="kpi-card">
    <div className="tile-head"><span className={`tile-icon ${accent}`}><Icon size={17} /></span><span className="tile-label">{label}</span></div>
    <div className="tile-value">{value}</div>
    <div className="tile-foot">{trend != null && <span className={trend >= 0 ? 'positive' : 'negative'}>
      {trend >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}{signed(trend)}
    </span>}{foot}</div>
  </div>;
}
function Panel({ title, subtitle, accessory, children, className = '' }: {
  title: string; subtitle?: string; accessory?: ReactNode;
  children: ReactNode; className?: string;
}) {
  return <section className={`panel ${className}`}>
    <div className="panel-header"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{accessory}</div>
    {children}
  </section>;
}
function MoneyTooltip({ active, payload, label, code }: {
  active?: boolean; payload?: { name: string; value: number; color: string }[];
  label?: string; code: string;
}) {
  if (!active || !payload?.length) return null;
  return <div className="tooltip"><span className="tooltip-date">{label?.includes('-') ? shortMonth(label) : label}</span>
    {payload.filter(x => x.value != null).map((p, i) => <div key={i} className="tooltip-val">
      <span className="tooltip-dot" style={{ background: p.color }} />{p.name}: <b>{currency(p.value, code)}</b>
    </div>)}</div>;
}

function App() {
  const [data, setData] = useState<DatasetResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const input = useRef<HTMLInputElement | null>(null);

  async function loadDemo() {
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API}/api/demo`);
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      setData(await res.json() as DatasetResponse);
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not load dataset'); }
    finally { setLoading(false); }
  }
  useEffect(() => { void loadDemo(); }, []);

  async function upload(file?: File) {
    if (!file) return;
    setUploading(true); setError('');
    try {
      const body = new FormData(); body.append('file', file);
      const response = await fetch(`${API}/api/analyze`, { method: 'POST', body });
      const obj = await response.json();
      if (!response.ok) throw new Error(obj.detail ?? `HTTP ${response.status}`);
      setData(obj as DatasetResponse);
    } catch (e) { setError(e instanceof Error ? e.message : 'Upload failed'); }
    finally { setUploading(false); if (input.current) input.current.value = ''; }
  }

  const timeline = useMemo(() => {
    if (!data) return [];
    const history = data.monthly_sales.slice(-7);
    const points = history.map(p => ({ month: p.month, Actual: p.revenue, Forecast: null as number | null }));
    if (points.length && data.forecast.months.length) points[points.length - 1].Forecast = points[points.length - 1].Actual;
    return [...points, ...data.forecast.months.map(p => ({ month: p.month, Actual: null as number | null, Forecast: p.prediction }))];
  }, [data]);

  const code = data?.metadata.currency ?? 'USD';
  const smallMoney = (v: number | null | undefined) => currency(v, code, true);
  const formatMoney = (v: number | null | undefined) => currency(v, code);

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><BarChart3 size={23} strokeWidth={2.4} /></div><div><strong>retail<span>IQ</span></strong><small>INTELLIGENCE PLATFORM</small></div></div>
      <div className="side-section-label">WORKSPACE</div>
      <nav className="nav">
        <a className="active" href="#overview"><Layers3 size={18} /> Overview <span className="nav-badge">01</span></a>
        <a href="#revenue"><Activity size={18} /> Sales Analytics</a>
        <a href="#forecast"><TrendingUp size={18} /> Forecasting</a>
        <a href="#products"><Package size={18} /> Products</a>
        <a href="#customers"><Users size={18} /> Customers</a>
      </nav>
      <div className="side-section-label side-more">DATASET</div>
      <div className="dataset-side"><div className="dataset-icon"><ShoppingBag size={19} /></div><div><b>{data?.metadata.source ?? 'Demo Retail'}</b><small>Active data source</small></div><Check size={15} className="dataset-ok" /></div>
      <div className="sidebar-bottom"><div className="help-icon"><CircleHelp size={18} /></div><div><b>Built for business clarity.</b><p>Insights grounded in transaction data.</p></div></div>
    </aside>
    <main id="overview" className="main-content">
      <header className="topbar"><div className="breadcrumb">Workspace <span>/</span> <b>Overview</b></div><div className="top-actions"><span className="status"><span /> API Connected</span><button className="btn-icon" type="button" title="Reload demo data" onClick={() => void loadDemo()}><RefreshCw size={17} /></button></div></header>
      <div className="page-content">
        <div className="heading-row"><div><div className="eyebrow"><Sparkles size={14} /> YOUR BUSINESS AT A GLANCE</div><h1>Sales Intelligence <span>Overview</span></h1><p>Make better decisions with a clear view of your sales, customers, and future revenue.</p></div><div className="heading-actions">
          <input type="file" ref={input} accept=".csv,text/csv" hidden onChange={e => void upload(e.target.files?.[0])} />
          <button className="btn btn-outline" onClick={() => input.current?.click()} disabled={uploading || loading}><FileUp size={17}/>{uploading ? 'Analyzing…' : 'Upload CSV'}</button>
          <button className="btn btn-primary" onClick={() => void loadDemo()} disabled={loading}><RefreshCw size={16}/> Demo data</button>
        </div></div>
        {error && <div className="error-banner"><AlertTriangle size={17}/><span>{error}. Check that the FastAPI server is running at localhost:8000.</span></div>}
        {loading && <div className="loading"><LoaderCircle className="spin" size={32}/> Loading your analytics dashboard…</div>}
        {data && !loading && <>
          <div className="dataset-alert"><span className="live-dot"/><span><b>{data.metadata.source}</b> &nbsp;·&nbsp; {data.metadata.first_date} to {data.metadata.last_date} &nbsp;·&nbsp; {numeric(data.metadata.valid_rows)} transaction lines</span><span className="dataset-pill">{data.metadata.currency}</span></div>
          {data.metadata.warning && <div className="warning"><AlertTriangle size={16}/>{data.metadata.warning}</div>}
          {data.metadata.excluded_rows > 0 && <div className="note">{numeric(data.metadata.excluded_rows)} non-positive, cancelled or invalid transaction lines excluded from the positive-sales view. Returns are not netted into revenue in this MVP.</div>}
          <div className="kpi-grid">
            <InfoTile icon={DollarSign} label="Total revenue" value={smallMoney(data.kpis.total_revenue)} foot="Historical net sales" accent="purple" trend={data.kpis.latest_month_growth_pct}/>
            <InfoTile icon={Wallet} label="Product profit" value={smallMoney(data.kpis.total_profit)} foot={data.metadata.profit_available ? 'From unit costs or source profits' : 'Requires cost or profit data'} accent="green" />
            <InfoTile icon={Target} label="Profit margin" value={data.kpis.profit_margin_pct == null ? '—' : `${data.kpis.profit_margin_pct.toFixed(1)}%`} foot="Gross profit / revenue" accent="blue" />
            <InfoTile icon={ShoppingBag} label="Orders" value={numeric(data.kpis.orders)} foot={`${numeric(data.kpis.customers)} identifiable customers`} accent="orange"/>
          </div>
          <div className="overview-grid">
            <Panel title="Revenue performance" subtitle="Monthly sales over the latest 18 months" className="revenue-panel" accessory={<span className="subtle-pill"><Activity size={13}/> Historical</span>}>
              <div id="revenue" className="chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data.monthly_sales.slice(-18)} margin={{ top: 15, right: 5, bottom: 0, left: 0 }}>
                <defs><linearGradient id="saleGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#9f85f8" stopOpacity={.32}/><stop offset="95%" stopColor="#9f85f8" stopOpacity={0}/></linearGradient></defs>
                <CartesianGrid stroke="#253045" strokeDasharray="4 5" vertical={false}/><XAxis dataKey="month" tickFormatter={shortMonth} tick={{ fill: '#8f9cb1', fontSize: 11 }} tickLine={false} axisLine={false} minTickGap={22}/><YAxis tickFormatter={n => smallMoney(n)} tick={{ fill: '#8f9cb1', fontSize: 11 }} tickLine={false} axisLine={false} width={67}/>
                <Tooltip content={<MoneyTooltip code={code}/>} /><Area dataKey="revenue" type="monotone" stroke="#a48bf8" strokeWidth={2.7} fill="url(#saleGradient)" name="Revenue" activeDot={{ r: 5, fill: '#c5b2ff' }}/>
              </AreaChart></ResponsiveContainer></div>
            </Panel>
            <Panel title="Customer mix" subtitle="Revenue distribution by segment" className="mix-panel">
              <div className="donut-wrap"><div className="donut-chart"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data.segments} dataKey="revenue" nameKey="segment" cx="50%" cy="50%" innerRadius={66} outerRadius={95} paddingAngle={3} stroke="none">
                {data.segments.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]}/>)}</Pie><Tooltip content={<MoneyTooltip code={code}/>} /></PieChart></ResponsiveContainer>
                <div className="donut-center"><small>TOTAL SALES</small><strong>{smallMoney(data.kpis.total_revenue)}</strong></div>
              </div></div><div className="segment-legend">{data.segments.slice(0, 5).map((s, i) => <div key={s.segment}><span className="legend-label"><i style={{ background: PALETTE[i % PALETTE.length] }}/>{s.segment}</span><strong>{s.share_pct?.toFixed(1)}%</strong></div>)}</div>
            </Panel>
          </div>
          <div className="two-col">
            <Panel title="Revenue forecast" subtitle="Next 3 months · time-series baseline" className="forecast-panel" accessory={<span className="subtle-pill violet"><Sparkles size={13}/> Estimate</span>}>
              <div id="forecast" className="chart forecast-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={timeline} margin={{ top: 15, right: 5, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="#253045" strokeDasharray="4 5" vertical={false} /><XAxis dataKey="month" tickFormatter={shortMonth} tick={{ fill: '#8f9cb1', fontSize: 11 }} tickLine={false} axisLine={false}/><YAxis tickFormatter={n => smallMoney(n)} tick={{ fill: '#8f9cb1', fontSize: 11 }} tickLine={false} axisLine={false} width={67}/>
                <Tooltip content={<MoneyTooltip code={code}/>} /><Line type="monotone" dataKey="Actual" stroke="#30cfa8" strokeWidth={2.5} dot={{ r: 3, fill: '#30cfa8' }} connectNulls={false}/><Line type="monotone" dataKey="Forecast" stroke="#aa8ff9" strokeDasharray="6 4" strokeWidth={2.5} dot={{ r: 3, fill: '#aa8ff9' }} connectNulls={false}/>
              </LineChart></ResponsiveContainer></div>
              <div className="forecast-summary"><div className="forecast-stat"><span>Forecast method</span><b>{data.forecast.method}</b></div><div className="forecast-stat"><span>Holdout MAE</span><b>{formatMoney(data.forecast.backtest_mae)}</b></div><div className="forecast-stat"><span>Holdout sMAPE</span><b>{data.forecast.backtest_smape_pct == null ? '—' : `${data.forecast.backtest_smape_pct}%`}</b></div></div>
              <p className="method-note">{data.forecast.note}</p>
            </Panel>
            <Panel title="Top products" subtitle={`Top 7 ranked by ${data.product_ranked_by}`} className="products-panel">
              <div id="products" className="chart product-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.top_products.slice(0, 7).map(p => ({...p, label: p.product_name.length > 17 ? `${p.product_name.slice(0, 17)}…` : p.product_name}))} layout="vertical" margin={{ top: 12, right: 8, left: 5, bottom: 0 }}>
                <CartesianGrid stroke="#253045" strokeDasharray="4 5" horizontal={false} /><XAxis type="number" tickFormatter={n => smallMoney(n)} tick={{ fill: '#8f9cb1', fontSize: 11 }} tickLine={false} axisLine={false} /><YAxis dataKey="label" type="category" tick={{ fill: '#c4ccda', fontSize: 11 }} tickLine={false} axisLine={false} width={130} />
                <Tooltip content={<MoneyTooltip code={code} />} /><Bar dataKey={data.product_ranked_by} fill="#a38af8" radius={[0, 5, 5, 0]} barSize={15} name={data.product_ranked_by}/>
              </BarChart></ResponsiveContainer></div>
            </Panel>
          </div>
          <div className="two-col bottom-col">
            <Panel title="Product profitability" subtitle="Performance by product and margin" accessory={<span className="subtle-pill">Top {Math.min(data.top_products.length, 6)}</span>}>
              <div className="table-scroll"><table><thead><tr><th>Product</th><th>Revenue</th><th>Profit</th><th>Margin</th></tr></thead><tbody>
                {data.top_products.slice(0, 6).map((p, idx) => <tr key={p.product_id}><td><span className="table-product-icon">{String(idx + 1).padStart(2, '0')}</span><span className="table-name">{p.product_name}<small>{p.category}</small></span></td><td>{smallMoney(p.revenue)}</td><td className={p.profit != null && p.profit < 0 ? 'negative' : ''}>{smallMoney(p.profit)}</td><td>{p.margin_pct === null ? <span className="muted">—</span> : <span className={`margin-badge ${p.margin_pct < 0 ? 'loss' : ''}`}>{p.margin_pct.toFixed(1)}%</span>}</td></tr>)}
              </tbody></table></div>
            </Panel>
            <Panel title="Customer intelligence" subtitle="Heuristic RFM customer segments" accessory={<span className="subtle-pill"><Users size={13}/> {numeric(data.kpis.customers)} customers</span>}>
              <div id="customers" className="rfm-stack">{data.rfm_segments.length ? data.rfm_segments.map((item, i) => <div className="rfm-row" key={item.segment}><div className="rfm-title"><span className="rfm-bullet" style={{ background: PALETTE[i % PALETTE.length] }}/><b>{item.segment}</b><span>{numeric(item.customers)} customers</span></div><div className="track"><div className="track-fill" style={{ width: `${Math.max(2, item.customers / data.kpis.customers * 100)}%`, background: PALETTE[i % PALETTE.length] }}/></div></div>) : <p className="muted">Customer identifiers are unavailable in this dataset.</p>}</div>
              <div className="rfm-foot"><CircleHelp size={15}/> RFM uses recency, distinct order frequency, and spending within this dataset.</div>
            </Panel>
          </div>
          <footer className="footer"><span>© RetailIQ — sample data and educational analytics</span><span>Built with React + FastAPI <ArrowRight size={13}/></span></footer>
        </>}
      </div>
    </main>
  </div>;
}
export default App;
