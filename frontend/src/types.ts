export type DatasetResponse = {
  metadata: {
    source: string; currency: string; profit_available: boolean;
    input_rows: number; valid_rows: number; excluded_rows: number;
    warning: string | null; first_date: string; last_date: string;
  };
  kpis: {
    total_revenue: number; total_profit: number | null;
    profit_margin_pct: number | null; orders: number; customers: number;
    avg_order_value: number | null; latest_month_growth_pct: number | null;
  };
  monthly_sales: { month: string; revenue: number }[];
  top_products: {
    product_id: string; product_name: string; category: string; revenue: number;
    quantity: number; profit: number | null; margin_pct: number | null;
  }[];
  product_ranked_by: string;
  segments: {
    segment: string; revenue: number; orders: number; profit: number | null;
    margin_pct: number | null; share_pct: number | null;
  }[];
  rfm_segments: { segment: string; customers: number }[];
  forecast: {
    method: string; months: { month: string; prediction: number }[];
    backtest_mae: number | null; backtest_smape_pct: number | null; note: string;
  };
};
