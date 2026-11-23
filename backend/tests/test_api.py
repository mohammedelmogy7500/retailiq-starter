from fastapi.testclient import TestClient
from app.main import app
from app.analytics import analyze_csv, parse_sales_csv, DataError
import pytest

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_demo():
    r = client.get("/api/demo")
    assert r.status_code == 200
    obj = r.json()
    assert obj["kpis"]["total_revenue"] > 0
    assert obj["kpis"]["total_profit"] is not None
    assert len(obj["forecast"]["months"]) == 3
    assert obj["forecast"]["backtest_mae"] is not None


def test_canonical_revenue_profit():
    content = ("order_id,order_date,customer_id,product_id,product_name,category,segment,region,quantity,unit_price,unit_cost,discount_pct\n"
               "o1,2025-01-03,c1,p1,Product A,Office,Consumer,East,2,100,55,0.1\n").encode()
    obj = analyze_csv(content)
    assert obj["kpis"]["total_revenue"] == 180
    assert obj["kpis"]["total_profit"] == 70


def test_superstore_does_not_apply_discount_twice():
    content = ("Order ID,Order Date,Customer ID,Product ID,Product Name,Category,Segment,Region,Quantity,Sales,Profit,Discount\n"
               "o1,2025-01-03,c1,p1,Product A,Office,Consumer,East,2,100,-10,0.2\n").encode()
    obj = analyze_csv(content)
    assert obj["kpis"]["total_revenue"] == 100
    assert obj["kpis"]["total_profit"] == -10


def test_uci_cancellations_excluded_no_invented_profit():
    content = ("InvoiceNo,InvoiceDate,StockCode,Description,Quantity,UnitPrice,CustomerID,Country\n"
               "123,2011-08-10 11:00,p1,Product A,2,15,12,United Kingdom\n"
               "C124,2011-08-11 12:00,p1,Product A,-2,15,12,United Kingdom\n").encode()
    obj = analyze_csv(content)
    assert obj["kpis"]["total_revenue"] == 30
    assert obj["kpis"]["total_profit"] is None
    assert obj["metadata"]["excluded_rows"] == 1
    assert obj["metadata"]["currency"] == "GBP"


def test_reject_bad_schema():
    with pytest.raises(DataError):
        parse_sales_csv(b"foo,bar\na,b\n")


def test_upload_reject_extension():
    response = client.post("/api/analyze", files={"file": ("sales.txt", b"hello", "text/plain")})
    assert response.status_code == 400


def test_forecast_uses_only_past_values():
    import pandas as pd
    from app.analytics import forecast_revenue
    months = pd.period_range("2023-01", periods=24, freq="M")
    # Final future months are not included in the training series.
    history = pd.Series([float(i + 1) * 100 for i in range(24)], index=months)
    forecast = forecast_revenue(history, horizon=3)
    assert forecast["months"][0]["prediction"] == 1300.0
    assert forecast["months"][1]["prediction"] == 1400.0
    assert forecast["months"][2]["prediction"] == 1500.0


def test_missing_cost_never_reports_partial_profit():
    content = ("order_id,order_date,customer_id,product_id,product_name,category,segment,region,quantity,unit_price,unit_cost\n"
               "o1,2025-01-03,c1,p1,Product A,Office,Consumer,East,1,100,50\n"
               "o2,2025-01-04,c1,p2,Product B,Office,Consumer,East,1,100,\n").encode()
    response = analyze_csv(content)
    assert response["kpis"]["total_profit"] is None
    assert response["top_products"][0]["profit"] is None
