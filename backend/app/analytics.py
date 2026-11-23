"""Transparent retail analytics: revenue, available profit, RFM, and baseline forecast."""
from __future__ import annotations

from io import BytesIO
import re
from typing import Any

import numpy as np
import pandas as pd


class DataError(ValueError):
    """Raised for unusable CSV data or unsupported schemas."""


def _key(column: str) -> str:
    return re.sub(r"[^a-z0-9]", "", column.lower())


def _take(df: pd.DataFrame, name: str, default: Any = None) -> pd.Series:
    match = {_key(c): c for c in df.columns}
    col = match.get(_key(name))
    return df[col] if col is not None else pd.Series(default, index=df.index)


def _require(df: pd.DataFrame, names: list[str]) -> None:
    present = {_key(c) for c in df.columns}
    missing = [name for name in names if _key(name) not in present]
    if missing:
        raise DataError("Missing required CSV column(s): " + ", ".join(missing))


def _str(series: pd.Series, fallback: str = "Unknown") -> pd.Series:
    result = series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    return result.mask(result.isna() | result.eq(""), fallback).astype(str)


def _num(series: pd.Series, default: Any = None) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values if default is None else values.fillna(default)


def parse_sales_csv(content: bytes) -> tuple[pd.DataFrame, dict[str, Any]]:
    try:
        raw = pd.read_csv(BytesIO(content), low_memory=False)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise DataError("The upload must be a valid UTF-8 CSV file") from exc
    if raw.empty:
        raise DataError("This CSV contains no transaction rows")
    if len(raw) > 300_000:
        raise DataError("Starter upload limit: 300,000 CSV rows")
    normalized = {_key(c) for c in raw.columns}
    out = pd.DataFrame(index=raw.index)
    if {"orderdate", "sales", "profit", "orderid"}.issubset(normalized):
        source, currency = "Sample Superstore", "USD"
        out["order_id"] = _str(_take(raw, "Order ID"))
        out["order_date"] = pd.to_datetime(_take(raw, "Order Date"), errors="coerce", dayfirst=False)
        out["customer_id"] = _str(_take(raw, "Customer ID"))
        out["product_id"] = _str(_take(raw, "Product ID"))
        out["product_name"] = _str(_take(raw, "Product Name"), "Unnamed product")
        out["category"] = _str(_take(raw, "Category"), "Other")
        out["segment"] = _str(_take(raw, "Segment"), "Unknown")
        out["region"] = _str(_take(raw, "Region"), "Unknown")
        out["quantity"] = _num(_take(raw, "Quantity"))
        out["revenue"] = _num(_take(raw, "Sales"))
        out["profit"] = _num(_take(raw, "Profit"))
    elif {"invoiceno", "invoicedate", "stockcode", "quantity", "unitprice"}.issubset(normalized):
        source, currency = "UCI Online Retail", "GBP"
        out["order_id"] = _str(_take(raw, "InvoiceNo"))
        out["order_date"] = pd.to_datetime(_take(raw, "InvoiceDate"), errors="coerce", dayfirst=False)
        out["customer_id"] = _str(_take(raw, "CustomerID"))
        out["product_id"] = _str(_take(raw, "StockCode"))
        out["product_name"] = _str(_take(raw, "Description"), "Unnamed product")
        out["category"] = "Other"
        out["segment"] = "Unspecified"
        out["region"] = _str(_take(raw, "Country"))
        out["quantity"] = _num(_take(raw, "Quantity"))
        out["revenue"] = out["quantity"] * _num(_take(raw, "UnitPrice"))
        out["profit"] = np.nan
        out = out.loc[~out["order_id"].str.upper().str.startswith("C")].copy()
    else:
        _require(raw, ["order_id", "order_date", "customer_id", "product_id", "product_name", "category", "segment", "region", "quantity", "unit_price", "unit_cost"])
        source, currency = "RetailIQ transaction CSV", "USD"
        for key in ["order_id", "customer_id", "product_id", "product_name", "category", "segment", "region"]:
            out[key] = _str(_take(raw, key))
        out["order_date"] = pd.to_datetime(_take(raw, "order_date"), errors="coerce")
        out["quantity"] = _num(_take(raw, "quantity"))
        unit_price = _num(_take(raw, "unit_price"))
        unit_cost = _num(_take(raw, "unit_cost"))
        discount = _num(_take(raw, "discount_pct"), default=0)
        out["revenue"] = out["quantity"] * unit_price * (1 - discount)
        out["profit"] = out["revenue"] - out["quantity"] * unit_cost
        out["valid_discount"] = discount.between(0, 1, inclusive="both")

    original_rows = len(raw)
    valid = out["order_date"].notna() & out["quantity"].gt(0) & out["revenue"].gt(0)
    valid &= out["order_id"].ne("Unknown")
    if "valid_discount" in out:
        valid &= out["valid_discount"]
    cleaned = out.loc[valid].drop(columns=["valid_discount"], errors="ignore").copy()
    if cleaned.empty:
        raise DataError("No valid positive-sale transaction rows remain after cleaning")
    cleaned["order_date"] = cleaned["order_date"].dt.tz_localize(None) if cleaned["order_date"].dt.tz is not None else cleaned["order_date"]
    cleaned["revenue"] = cleaned["revenue"].astype(float)
    cleaned["profit"] = cleaned["profit"].astype(float)
    profit_available = bool(cleaned["profit"].notna().all())
    # Never present partial profit coverage as total profit.
    if not profit_available:
        cleaned["profit"] = np.nan
    return cleaned, {
        "source": source,
        "currency": currency,
        "profit_available": profit_available,
        "input_rows": original_rows,
        "valid_rows": len(cleaned),
        "excluded_rows": original_rows - len(cleaned),
        "warning": None if profit_available else "Profit unavailable: the source lacks complete unit costs or profit values.",
    }


def _money(value: float | None) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), 2)


def _percent(part: float, whole: float) -> float | None:
    return round(float(part) * 100 / float(whole), 2) if whole else None


def _sales_months(df: pd.DataFrame) -> pd.Series:
    monthly = df.groupby(df["order_date"].dt.to_period("M"))["revenue"].sum().sort_index()
    periods = pd.period_range(monthly.index.min(), monthly.index.max(), freq="M")
    return monthly.reindex(periods, fill_value=0).astype(float)


def forecast_revenue(monthly: pd.Series, horizon: int = 3) -> dict[str, Any]:
    # Do not forecast a still-in-progress calendar month as though it were complete.
    today = pd.Timestamp.now().to_period("M")
    complete = monthly.loc[monthly.index < today]
    if len(complete) < 3:
        return {"method": "Not enough history", "months": [], "backtest_mae": None,
                "backtest_smape_pct": None, "note": "At least 3 completed months are required."}
    observations = complete.to_numpy(dtype=float)
    seasonal = len(observations) >= 15
    method = "Seasonal naive (same month previous year)" if seasonal else "3-month moving average"

    def prediction(history: list[float], target_idx: int) -> float:
        if seasonal and target_idx >= 12:
            return max(0.0, history[target_idx - 12])
        return max(0.0, float(np.mean(history[-3:])))

    # Sequential holdout: predict each of final 3 completed months using only earlier data.
    errors, smape = [], []
    if len(observations) >= 9:
        for idx in range(len(observations) - 3, len(observations)):
            history = list(observations[:idx])
            p = prediction(history, idx)
            actual = float(observations[idx])
            errors.append(abs(actual - p))
            if abs(actual) + abs(p) > 0:
                smape.append(200 * abs(actual - p) / (abs(actual) + abs(p)))
    history = list(observations)
    predictions = []
    for step in range(horizon):
        idx = len(history)
        value = prediction(history, idx)
        history.append(value)
        month = complete.index[-1] + step + 1
        predictions.append({"month": str(month), "prediction": _money(value)})
    return {
        "method": method,
        "months": predictions,
        "backtest_mae": _money(np.mean(errors)) if errors else None,
        "backtest_smape_pct": round(float(np.mean(smape)), 2) if smape else None,
        "note": "Baseline forecast only. The 3-month holdout backtest uses no future observations; forecasts are estimates, not guarantees.",
    }


def rfm_segments(df: pd.DataFrame) -> list[dict[str, Any]]:
    customers = df.loc[df["customer_id"] != "Unknown"]
    if customers.empty:
        return []
    as_of = df["order_date"].max().normalize() + pd.Timedelta(days=1)
    group = customers.groupby("customer_id").agg(
        last_order=("order_date", "max"),
        frequency=("order_id", "nunique"),
        monetary=("revenue", "sum"),
    )
    group["recency"] = (as_of - group["last_order"].dt.normalize()).dt.days
    # Percentile ranking avoids qcut failures on heavily tied frequencies.
    group["r"] = (6 - np.ceil(group["recency"].rank(pct=True, method="average") * 5)).clip(1, 5)
    group["f"] = np.ceil(group["frequency"].rank(pct=True, method="average") * 5).clip(1, 5)
    group["m"] = np.ceil(group["monetary"].rank(pct=True, method="average") * 5).clip(1, 5)
    conditions = [
        (group["r"] >= 4) & (group["f"] >= 4) & (group["m"] >= 4),
        (group["r"] <= 2) & (group["f"] >= 3),
        group["f"] >= 4,
        group["r"] >= 4,
    ]
    labels = ["Champions", "At Risk", "Loyal", "Potential"]
    group["rfm_segment"] = np.select(conditions, labels, default="Regular")
    counts = group["rfm_segment"].value_counts()
    return [{"segment": str(name), "customers": int(count)} for name, count in counts.items()]


def analyze(df: pd.DataFrame, meta: dict[str, Any]) -> dict[str, Any]:
    profit_known = bool(meta["profit_available"])
    revenue = float(df["revenue"].sum())
    profit = float(df["profit"].sum()) if profit_known else None
    orders = int(df["order_id"].nunique())
    customers = int(df.loc[df["customer_id"] != "Unknown", "customer_id"].nunique())
    monthly = _sales_months(df)

    group_cols = ["product_id", "product_name", "category"]
    product_agg = {"revenue": ("revenue", "sum"), "quantity": ("quantity", "sum")}
    if profit_known:
        product_agg["profit"] = ("profit", "sum")
    products = df.groupby(group_cols, dropna=False).agg(**product_agg).reset_index()
    rank_by = "profit" if profit_known else "revenue"
    products = products.sort_values(rank_by, ascending=False).head(10)
    top_products = []
    for record in products.to_dict("records"):
        item = {"product_id": record["product_id"], "product_name": record["product_name"],
                "category": record["category"], "revenue": _money(record["revenue"]),
                "quantity": int(record["quantity"]),
                "profit": _money(record["profit"]) if profit_known else None,
                "margin_pct": _percent(record["profit"], record["revenue"]) if profit_known else None}
        top_products.append(item)

    segment_agg = {"revenue": ("revenue", "sum"), "orders": ("order_id", "nunique")}
    if profit_known:
        segment_agg["profit"] = ("profit", "sum")
    segments = df.groupby("segment").agg(**segment_agg).reset_index().sort_values("revenue", ascending=False)
    segment_list = []
    for record in segments.to_dict("records"):
        segment_list.append({"segment": record["segment"], "revenue": _money(record["revenue"]),
                             "orders": int(record["orders"]),
                             "profit": _money(record["profit"]) if profit_known else None,
                             "margin_pct": _percent(record["profit"], record["revenue"]) if profit_known else None,
                             "share_pct": _percent(record["revenue"], revenue)})

    last = float(monthly.iloc[-1]); previous = float(monthly.iloc[-2]) if len(monthly) > 1 else None
    growth = _percent(last - previous, previous) if previous is not None else None
    return {
        "metadata": {**meta, "first_date": df["order_date"].min().strftime("%Y-%m-%d"),
                     "last_date": df["order_date"].max().strftime("%Y-%m-%d")},
        "kpis": {"total_revenue": _money(revenue), "total_profit": _money(profit),
                 "profit_margin_pct": _percent(profit, revenue) if profit_known else None,
                 "orders": orders, "customers": customers, "avg_order_value": _money(revenue / orders) if orders else None,
                 "latest_month_growth_pct": growth},
        "monthly_sales": [{"month": str(index), "revenue": _money(val)} for index, val in monthly.items()],
        "top_products": top_products, "product_ranked_by": rank_by,
        "segments": segment_list, "rfm_segments": rfm_segments(df),
        "forecast": forecast_revenue(monthly),
    }


def analyze_csv(content: bytes) -> dict[str, Any]:
    frame, meta = parse_sales_csv(content)
    return analyze(frame, meta)
