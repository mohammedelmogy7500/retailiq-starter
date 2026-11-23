"""Generate reproducible fictional transactions for the demo. No real customers."""
from pathlib import Path
import calendar
import csv
import numpy as np
import pandas as pd

OUTPUT = Path(__file__).with_name("sample_sales.csv")
SEED = 42
PRODUCTS = [
    ("P001", "Wireless Mouse", "Accessories", 24, 9),
    ("P002", "Mechanical Keyboard", "Accessories", 85, 48),
    ("P003", "USB-C Hub", "Accessories", 55, 27),
    ("P004", "Office Chair", "Furniture", 240, 169),
    ("P005", "Standing Desk", "Furniture", 410, 288),
    ("P006", "Monitor 27 inch", "Electronics", 315, 210),
    ("P007", "Webcam HD", "Electronics", 75, 31),
    ("P008", "Portable SSD", "Electronics", 139, 82),
    ("P009", "Notebook Pack", "Office Supplies", 19, 5),
    ("P010", "Desk Lamp", "Office Supplies", 48, 21),
]
CUSTOMERS = [(f"C{i:04}", ["Consumer", "Corporate", "Home Office"][i % 3],
              ["East", "West", "Central", "South"][i % 4]) for i in range(1, 240)]


def generate():
    rng = np.random.default_rng(SEED)
    rows = []
    order_no = 0
    for mi, month in enumerate(pd.period_range("2023-01", "2026-10", freq="M")):
        q4_boost = 1.4 if month.month in (10, 11, 12) else 1.0
        base_orders = int((48 + mi * 0.5) * q4_boost)
        num_orders = max(10, int(rng.normal(base_orders, 7)))
        for _ in range(num_orders):
            order_no += 1
            customer_idx = int(rng.integers(0, len(CUSTOMERS)))
            cid, segment, region = CUSTOMERS[customer_idx]
            max_day = calendar.monthrange(month.year, month.month)[1]
            day = int(rng.integers(1, max_day + 1))
            date = f"{month.year:04d}-{month.month:02d}-{day:02d}"
            unique_product_indices = rng.choice(len(PRODUCTS), size=int(rng.integers(1, 4)), replace=False)
            for idx in unique_product_indices:
                pid, name, category, price, cost = PRODUCTS[int(idx)]
                qty = int(rng.integers(1, 5))
                discount = float(rng.choice([0, .05, .10, .15, .20], p=[.65,.15,.10,.06,.04]))
                rows.append({"order_id": f"O{order_no:06}", "order_date": date,
                             "customer_id": cid, "product_id": pid, "product_name": name,
                             "category": category, "segment": segment, "region": region,
                             "quantity": qty, "unit_price": price, "unit_cost": cost,
                             "discount_pct": discount})
    # Mark the last complete demo month as complete, without inserting revenue.
    # The forecast operates on completed months using the current calendar month.
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    print(f"Wrote {len(rows)} synthetic sales lines to {OUTPUT}")


if __name__ == "__main__":
    generate()
