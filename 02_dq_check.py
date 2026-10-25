"""
02_dq_check.py
==============
Data-quality health check on the raw CSV files in data/ BEFORE they go into SQL.
It does not change any data. It reads, checks, and prints a report.
The report is also saved to  reports/dq_report.txt  (paste it into your README).

What it checks
--------------
1. Row counts and empty (NULL) cells per column
2. Exact duplicate rows
3. Duplicate primary keys
4. Orphan foreign keys (e.g. an order line pointing at an order that doesn't exist)
5. Status labels - are they consistent?
6. Date formats - is every date written the same way?
7. Business-logic checks (shipped before created, negative quantities, ...)

How to run (after 01_generate_data.py):
    python 02_dq_check.py

Requires: pandas   (pip install pandas)
"""

from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
REPORT_DIR = BASE / "reports"
REPORT_DIR.mkdir(exist_ok=True)

report = []


def out(text=""):
    print(text)
    report.append(text)


issues = 0


def check(label, count, note=""):
    """Print one check line. count == 0 means OK."""
    global issues
    if count == 0:
        out(f"  [ OK ]    {label}")
    else:
        issues += 1
        out(f"  [ISSUE]   {label}: {count:,}" + (f"  ({note})" if note else ""))


TABLES = ["products", "suppliers", "customers", "locations", "purchase_orders",
          "receipts", "stock_snapshot", "orders", "order_lines", "shipments", "cycle_counts"]

missing = [t for t in TABLES if not (DATA / f"{t}.csv").exists()]
if missing:
    raise SystemExit(f"Missing files in {DATA}: {missing}\nRun 01_generate_data.py first.")

# read everything as text so nothing is silently changed (e.g. leading zeros)
df = {t: pd.read_csv(DATA / f"{t}.csv", dtype=str) for t in TABLES}

out("=" * 70)
out("WMS DATA QUALITY REPORT")
out("=" * 70)

# ---------------------------------------------------------------- 1. size + nulls
out("\n1. ROW COUNTS AND EMPTY CELLS")
for t in TABLES:
    d = df[t]
    out(f"\n  {t}: {len(d):,} rows, {d.shape[1]} columns")
    nulls = d.isna().sum()
    nulls = nulls[nulls > 0]
    if nulls.empty:
        out("    no empty cells")
    for col, n in nulls.items():
        out(f"    {col}: {n:,} empty ({n / len(d):.1%})")

# ---------------------------------------------------------------- 2. exact duplicates
out("\n2. EXACT DUPLICATE ROWS")
for t in TABLES:
    check(t, int(df[t].duplicated().sum()))

# ---------------------------------------------------------------- 3. primary keys
out("\n3. DUPLICATE PRIMARY KEYS (extra rows beyond the first)")
KEYS = {
    "products": ["sku"], "suppliers": ["supplier_id"], "customers": ["customer_id"],
    "locations": ["location_id"], "purchase_orders": ["po_number", "po_line"],
    "receipts": ["grn_number", "grn_line"], "stock_snapshot": ["stock_id"],
    "orders": ["order_id"], "order_lines": ["order_id", "line_no"],
    "shipments": ["shipment_id"], "cycle_counts": ["count_id"],
}
for t, k in KEYS.items():
    check(f"{t} ({' + '.join(k)})", int(df[t].duplicated(subset=k).sum()))

# ---------------------------------------------------------------- 4. orphan foreign keys
out("\n4. ORPHAN FOREIGN KEYS (child value not found in parent table)")
FKS = [
    ("purchase_orders", ["supplier_id"], "suppliers", ["supplier_id"]),
    ("purchase_orders", ["sku"], "products", ["sku"]),
    ("receipts", ["po_number", "po_line"], "purchase_orders", ["po_number", "po_line"]),
    ("receipts", ["sku"], "products", ["sku"]),
    ("stock_snapshot", ["sku"], "products", ["sku"]),
    ("stock_snapshot", ["location_id"], "locations", ["location_id"]),
    ("orders", ["customer_id"], "customers", ["customer_id"]),
    ("order_lines", ["order_id"], "orders", ["order_id"]),
    ("order_lines", ["sku"], "products", ["sku"]),
    ("order_lines", ["pick_location_id"], "locations", ["location_id"]),
    ("shipments", ["order_id"], "orders", ["order_id"]),
    ("cycle_counts", ["location_id"], "locations", ["location_id"]),
    ("cycle_counts", ["sku"], "products", ["sku"]),
]
for child, ccols, parent, pcols in FKS:
    c = df[child].dropna(subset=ccols)                      # blanks are reported in section 1
    p = df[parent][pcols].drop_duplicates()
    merged = c.merge(p, left_on=ccols, right_on=pcols, how="left", indicator=True)
    check(f"{child}.{'+'.join(ccols)} -> {parent}", int((merged["_merge"] == "left_only").sum()))

# ---------------------------------------------------------------- 5. status labels
out("\n5. STATUS / CATEGORY LABELS (every distinct value and how often it appears)")
CANON = {
    ("receipts", "quality_status"): {"Available", "Quarantine", "Damaged", "Returns", "Expired"},
    ("stock_snapshot", "quality_status"): {"Available", "Quarantine", "Damaged", "Returns", "Expired"},
    ("orders", "status"): {"Created", "Picking", "Picked", "Packed", "Shipped", "Cancelled"},
    ("orders", "order_type"): {"E-Com", "Standard", "Promo", "Internal", "Export"},
    ("orders", "priority"): {"High", "Medium", "Low"},
    ("purchase_orders", "po_status"): {"Open", "Closed", "Cancelled"},
    ("cycle_counts", "count_status"): {"Count complete", "Booked"},
}
for (t, col), canon in CANON.items():
    vc = df[t][col].value_counts(dropna=False)
    odd = [v for v in vc.index if v not in canon]
    check(f"{t}.{col} has {len(vc)} distinct labels (expected {len(canon)})", len(odd),
          "non-standard: " + ", ".join(repr(v) for v in odd[:8]) if odd else "")

# ---------------------------------------------------------------- 6. date formats
out("\n6. DATE / DATETIME FORMATS")
DT_RE = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"
D_RE = r"^\d{4}-\d{2}-\d{2}$"
DATE_COLS = [
    ("receipts", "received_datetime", DT_RE), ("receipts", "expiry_date", D_RE),
    ("orders", "created_datetime", DT_RE), ("orders", "promised_date", D_RE),
    ("order_lines", "picked_datetime", DT_RE), ("shipments", "shipped_datetime", DT_RE),
    ("purchase_orders", "created_date", D_RE), ("purchase_orders", "expected_date", D_RE),
    ("stock_snapshot", "expiry_date", D_RE), ("cycle_counts", "count_date", D_RE),
]
for t, col, rx in DATE_COLS:
    s = df[t][col].dropna()
    check(f"{t}.{col} not in standard format", int((~s.str.match(rx)).sum()))

# ---------------------------------------------------------------- 7. business logic
out("\n7. BUSINESS-LOGIC CHECKS")
orders = df["orders"].copy()
ship = df["shipments"].copy()
lines = df["order_lines"].copy()
stock = df["stock_snapshot"].copy()
rec = df["receipts"].copy()

m = ship.merge(orders[["order_id", "created_datetime"]], on="order_id", how="left")
s_dt = pd.to_datetime(m["shipped_datetime"], errors="coerce")
c_dt = pd.to_datetime(m["created_datetime"], errors="coerce")
check("Shipped BEFORE the order was created", int((s_dt < c_dt).sum()))

shipped_orders = set(orders.loc[orders["status"] == "Shipped", "order_id"])
check("Orders marked Shipped with no shipment record", len(shipped_orders - set(ship["order_id"])))
check("Shipment records for orders NOT marked Shipped",
      len(set(ship["order_id"]) - shipped_orders))

check("Negative quantity on hand (stock_snapshot)",
      int((pd.to_numeric(stock["qty_on_hand"]) < 0).sum()))
check("Zero or negative qty_received (receipts)",
      int((pd.to_numeric(rec["qty_received"]) <= 0).sum()))
check("Order lines with ordered_qty <= 0",
      int((pd.to_numeric(lines["ordered_qty"]) <= 0).sum()))

batch_skus = set(df["products"].loc[df["products"]["batch_managed"] == "1", "sku"])
bm = stock[stock["sku"].isin(batch_skus)]
check("Batch-managed stock rows with no expiry date", int(bm["expiry_date"].isna().sum()))
check("Stock rows with no location", int(stock["location_id"].isna().sum()))

shipped_lines = lines[lines["order_id"].isin(shipped_orders)]
sq = pd.to_numeric(shipped_lines["shipped_qty"])
oq = pd.to_numeric(shipped_lines["ordered_qty"])
check("Shipped lines where shipped_qty <> ordered_qty (short or over-shipped)", int((sq != oq).sum()),
      "this one is a business finding, not a data error")

out("\n" + "=" * 70)
out(f"SUMMARY: {issues} check(s) flagged an issue.")
out("Next step: load the CSVs into SQL Server staging (stg) tables and clean there.")
out("=" * 70)

(REPORT_DIR / "dq_report.txt").write_text("\n".join(report), encoding="utf-8")
print(f"\nReport saved to: {REPORT_DIR / 'dq_report.txt'}")
