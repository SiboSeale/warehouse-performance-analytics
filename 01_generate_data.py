"""
01_generate_data.py
===================
Builds a SYNTHETIC dataset for a fictional 3PL beauty / FMCG warehouse.
Nothing here comes from a real client or a real company.

What it does
------------
1. Creates master data (products, suppliers, customers, locations).
2. Creates transactions (purchase orders, receipts, stock, orders,
   order lines, shipments, cycle counts) covering 1 Jul - 30 Sep 2026.
3. Plants a small "story" in the data (so the dashboard has something to find).
4. Plants deliberate "mess" (so the SQL cleaning step has real work to do).
5. Writes everything as CSV files into a folder called  data/
   plus two helper files:
      mess_log.csv        - what mess was planted, and how it should be handled
      control_totals.csv  - the KPI values your SQL / Power BI should reproduce
                            AFTER cleaning (use it to reconcile your numbers)

How to run
----------
    python 01_generate_data.py

Requires: pandas, numpy   (pip install pandas numpy)
Note: running it again overwrites the files in data/.
"""

from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 0. SETTINGS
# ---------------------------------------------------------------------------
SEED = 42                                   # same seed -> same data
rng = np.random.default_rng(SEED)

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)

START = pd.Timestamp("2026-07-01")
AS_OF = pd.Timestamp("2026-09-30 23:59:59")  # "today" inside the dataset
AS_OF_DATE = AS_OF.normalize()

N_PRODUCTS = 300
N_ORDERS = 5000
N_PO = 420
N_CYCLE_COUNTS = 800
SHORT_SUPPLIER = "SUP-03"                    # planted story 1: chronically short


def fmt_dt(s):
    """Datetime column -> 'YYYY-MM-DD HH:MM:SS' text (blank if missing)."""
    return pd.to_datetime(s).dt.strftime("%Y-%m-%d %H:%M:%S")


def fmt_d(s):
    """Date column -> 'YYYY-MM-DD' text (blank if missing)."""
    return pd.to_datetime(s).dt.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# 1. MASTER DATA
# ---------------------------------------------------------------------------
# --- suppliers -------------------------------------------------------------
supplier_names = [
    "Northgate Cosmetics", "Lumiere Labs", "Cape Botanicals",
    "Harbour Fragrance House", "Savanna Skincare Co", "Orchid Beauty Supply",
    "Pinnacle Beauty Group", "Evergreen Naturals", "Coastline Cosmetics",
    "Meridian Personal Care", "Atlas Fragrance Works", "Kestrel Beauty Brands",
]
supplier_countries = [
    "South Africa", "France", "South Africa", "France", "South Africa",
    "Germany", "United Kingdom", "South Africa", "Italy", "South Africa",
    "France", "Germany",
]
suppliers = pd.DataFrame({
    "supplier_id": [f"SUP-{i:02d}" for i in range(1, 13)],
    "supplier_name": supplier_names,
    "country": supplier_countries,
})
sup_ids = suppliers["supplier_id"].to_numpy()
sup_w = np.full(12, 0.08)
sup_w[2] = 0.15                              # SUP-03 supplies more SKUs / POs
sup_w = sup_w / sup_w.sum()

# --- products --------------------------------------------------------------
TYPES = ["Skincare", "Fragrance", "Makeup", "Body Care", "Hair Care", "Sample/Tester"]
TYPE_P = [0.30, 0.15, 0.20, 0.15, 0.10, 0.10]
LINES = ["Radiant", "Velvet", "Pure", "Bloom", "Silk", "Glow", "Calm", "Dew", "Lumen", "Aura"]
ITEMS = {
    "Skincare": ["Serum", "Moisturiser", "Eye Cream", "Cleanser", "Toner"],
    "Fragrance": ["Eau de Parfum", "Eau de Toilette", "Body Mist"],
    "Makeup": ["Lipstick", "Mascara", "Foundation", "Lip Gloss", "Eyeliner"],
    "Body Care": ["Body Lotion", "Body Scrub", "Shower Gel", "Hand Cream"],
    "Hair Care": ["Shampoo", "Conditioner", "Hair Mask"],
    "Sample/Tester": ["Serum Sample", "Fragrance Tester", "Cream Trial"],
}
SIZES = {
    "Skincare": ["30ML", "50ML", "100ML"],
    "Fragrance": ["30ML", "50ML", "100ML"],
    "Makeup": ["3G", "5ML", "8ML"],
    "Body Care": ["100ML", "200ML", "250ML"],
    "Hair Care": ["200ML", "250ML", "400ML"],
    "Sample/Tester": ["3ML", "5ML", "10ML"],
}

prod_rows = []
for i in range(N_PRODUCTS):
    ptype = str(rng.choice(TYPES, p=TYPE_P))
    item = str(rng.choice(ITEMS[ptype]))
    line = str(rng.choice(LINES))
    size = str(rng.choice(SIZES[ptype]))
    weight = float(np.clip(rng.lognormal(5.0, 0.6), 10, 1500))
    prod_rows.append({
        "sku": str(80000001 + i),
        "description": f"{line} {item} {size}".upper(),
        "barcode": "6001" + f"{int(rng.integers(0, 10**9)):09d}",
        "product_type": ptype,
        "batch_managed": int(rng.random() < 0.75),
        "unit_weight_g": round(weight, 1),
        "unit_volume_cm3": round(weight * float(rng.uniform(1.5, 4.0)), 1),
        "supplier_id": str(rng.choice(sup_ids, p=sup_w)),
    })
products = pd.DataFrame(prod_rows)
sku_arr = products["sku"].to_numpy()
sku_supplier = dict(zip(products["sku"], products["supplier_id"]))
sku_batch_managed = dict(zip(products["sku"], products["batch_managed"]))
# each SKU lives in one pick zone (internal detail, not written to a file)
sku_zone = {s: str(rng.choice(["A", "B", "C"], p=[0.40, 0.35, 0.25])) for s in sku_arr}

# --- customers -------------------------------------------------------------
CITIES = ["Johannesburg", "Sandton", "Pretoria", "Cape Town", "Durban",
          "Port Elizabeth", "Midrand", "Bloemfontein", "East London", "Pietermaritzburg"]
cust = []
for n in ["GlowBox Online", "BeautyNest Online", "Petal Co Online", "Skinly Online",
          "The Vanity Shop Online", "Dewdrop Direct", "Mirror Mirror Online", "Luxe Lane Online"]:
    cust.append((n, "Online", "E-Com"))
for brand in ["Greenleaf", "Sunrise", "Wellcare"]:
    for city in CITIES[:4]:
        cust.append((f"{brand} Pharmacy - {city}", city, "Pharmacy"))
for city in CITIES[:8]:
    cust.append((f"Harrington Stores - {city}", city, "Department Store"))
for n, city in [("Studio Aura", "Sandton"), ("Silk and Co", "Cape Town"), ("The Style Lab", "Durban"),
                ("Bloom Hair", "Pretoria"), ("Velvet Room", "Johannesburg"), ("Glow Bar", "Midrand")]:
    cust.append((f"{n} Salon", city, "Salon"))
for n, city in [("Cape Beauty Distribution", "Cape Town"), ("Highveld Wholesale Beauty", "Johannesburg"),
                ("Natal Cosmetics Distributors", "Durban"), ("Export Partners Windhoek", "Windhoek")]:
    cust.append((n, city, "Distributor"))
for n in ["Internal Orders - Marketing", "Internal Orders - Samples"]:
    cust.append((n, "Johannesburg", "Internal"))
customers = pd.DataFrame(cust, columns=["customer_name", "city", "customer_type"])
customers.insert(0, "customer_id", [f"CUST-{i:03d}" for i in range(1, len(customers) + 1)])

# --- locations -------------------------------------------------------------
loc_rows = []
for zone in ["A", "B", "C"]:
    for aisle in range(1, 6):
        for bay in range(1, 11):
            for level in range(1, 4):
                loc_rows.append({
                    "location_id": f"{zone}{aisle:02d}-{bay:02d}-{level}",
                    "zone": zone, "aisle": aisle,
                    "location_type": "Pick" if level == 1 else "Bulk",
                })
d_types = {1: "Quarantine", 2: "Damage", 3: "Returns", 4: "Expired", 5: "Special"}
for aisle in range(1, 6):
    for bay in range(1, 11):
        for level in range(1, 4):
            loc_rows.append({
                "location_id": f"D{aisle:02d}-{bay:02d}-{level}",
                "zone": "D", "aisle": aisle, "location_type": d_types[aisle],
            })
locations = pd.DataFrame(loc_rows)
zone_locs = {z: locations.loc[locations["zone"] == z, "location_id"].to_numpy() for z in "ABC"}
d_locs = {
    "Quarantine": locations.loc[locations["location_type"] == "Quarantine", "location_id"].to_numpy(),
    "Damaged": locations.loc[locations["location_type"] == "Damage", "location_id"].to_numpy(),
    "Returns": locations.loc[locations["location_type"] == "Returns", "location_id"].to_numpy(),
    "Expired": locations.loc[locations["location_type"] == "Expired", "location_id"].to_numpy(),
}

# ---------------------------------------------------------------------------
# 2. STOCK SNAPSHOT  (stock on hand at the end of 30 Sep 2026)
# ---------------------------------------------------------------------------
stock_rows = []
used = set()


def add_stock(sku, batch, expiry, loc, status):
    key = (sku, batch, loc)
    if key in used:
        return
    used.add(key)
    qty = int(np.clip(rng.lognormal(4.0, 0.8), 1, 2000))
    stock_rows.append({"sku": sku, "batch": batch, "expiry_date": expiry,
                       "location_id": loc, "quality_status": status, "qty_on_hand": qty})


for p in products.itertuples():
    zone = sku_zone[p.sku]
    n_batches = int(rng.integers(2, 7)) if p.batch_managed == 1 else 1
    for _ in range(n_batches):
        if p.batch_managed == 1:
            batch = f"0{int(rng.integers(400000, 560000))}"
            r = rng.random()
            if r < 0.02:
                days = -int(rng.integers(1, 200))          # already expired
            elif r < 0.05:
                days = int(rng.integers(1, 31))            # <= 30 days
            elif r < 0.075:
                days = int(rng.integers(31, 61))           # 31-60 days
            elif r < 0.10:
                days = int(rng.integers(61, 91))           # 61-90 days
            else:
                days = int(rng.integers(91, 1100))         # > 90 days
            expiry = (AS_OF_DATE + pd.Timedelta(days=days)).strftime("%Y-%m-%d")
            expired = days < 0
        else:
            batch, expiry, expired = None, None, False
        for _ in range(int(rng.integers(1, 5))):
            if expired:
                add_stock(p.sku, batch, expiry, str(rng.choice(d_locs["Expired"])), "Expired")
                continue
            r = rng.random()
            if r < 0.94:
                add_stock(p.sku, batch, expiry, str(rng.choice(zone_locs[zone])), "Available")
            elif r < 0.97:
                add_stock(p.sku, batch, expiry, str(rng.choice(d_locs["Quarantine"])), "Quarantine")
            elif r < 0.99:
                add_stock(p.sku, batch, expiry, str(rng.choice(d_locs["Damaged"])), "Damaged")
            else:
                add_stock(p.sku, batch, expiry, str(rng.choice(d_locs["Returns"])), "Returns")

stock = pd.DataFrame(stock_rows)
# every SKU must have at least one Available row (so it can be picked)
have_avail = set(stock.loc[stock["quality_status"] == "Available", "sku"])
extra = []
for p in products.itertuples():
    if p.sku not in have_avail:
        batch = f"0{int(rng.integers(400000, 560000))}" if p.batch_managed == 1 else None
        expiry = (AS_OF_DATE + pd.Timedelta(days=int(rng.integers(120, 900)))).strftime("%Y-%m-%d") if batch else None
        extra.append({"sku": p.sku, "batch": batch, "expiry_date": expiry,
                      "location_id": str(rng.choice(zone_locs[sku_zone[p.sku]])),
                      "quality_status": "Available", "qty_on_hand": int(rng.integers(20, 300))})
if extra:
    stock = pd.concat([stock, pd.DataFrame(extra)], ignore_index=True)
stock.insert(0, "stock_id", np.arange(1, len(stock) + 1))
stock.insert(1, "snapshot_date", "2026-09-30")
avail_locs = (stock[stock["quality_status"] == "Available"]
              .groupby("sku")["location_id"].apply(list).to_dict())

# ---------------------------------------------------------------------------
# 3. PURCHASE ORDERS + RECEIPTS  (inbound)
# ---------------------------------------------------------------------------
sku_by_supplier = products.groupby("supplier_id")["sku"].apply(list).to_dict()
po_days = pd.date_range("2026-06-15", AS_OF_DATE, freq="B")

headers = []
for _ in range(N_PO):
    sup = str(rng.choice(sup_ids, p=sup_w))
    exp = pd.Timestamp(rng.choice(po_days))
    headers.append({"supplier_id": sup,
                    "expected_date": exp,
                    "created_date": exp - pd.Timedelta(days=int(rng.integers(5, 21))),
                    "n_lines": int(rng.integers(1, 7))})
headers.sort(key=lambda h: h["created_date"])

QTY_CHOICES = [48, 96, 120, 240, 360, 480, 600, 1200]
QTY_P = [0.15, 0.20, 0.20, 0.20, 0.10, 0.08, 0.05, 0.02]

po_rows, rec_rows = [], []
for idx, h in enumerate(headers):
    po_number = f"PO{4500000 + idx}"
    pool = sku_by_supplier[h["supplier_id"]]
    skus = rng.choice(pool, size=min(h["n_lines"], len(pool)), replace=False)
    delay = int(rng.choice([0, 1, 2, 3, 4], p=[0.45, 0.25, 0.15, 0.10, 0.05]))
    if h["supplier_id"] == SHORT_SUPPLIER:
        delay += int(rng.integers(1, 4))                   # also late
    recv_date = h["expected_date"] + pd.Timedelta(days=delay)
    for ln, sku in enumerate(skus, start=1):
        exp_qty = int(rng.choice(QTY_CHOICES, p=QTY_P))
        status = "Open"
        parts = []
        if rng.random() < 0.03:
            status = "Cancelled"
        elif recv_date <= AS_OF_DATE:
            # fill factor: planted story 1 -> SUP-03 delivers short
            if h["supplier_id"] == SHORT_SUPPLIER:
                fill = 1.0 if rng.random() < 0.35 else float(rng.uniform(0.60, 0.92))
            else:
                fill = 1.0 if rng.random() < 0.90 else float(rng.uniform(0.80, 0.98))
            qty = max(1, int(round(exp_qty * fill)))
            second = recv_date + pd.Timedelta(days=int(rng.integers(1, 4)))
            if qty >= 10 and rng.random() < 0.08 and second <= AS_OF_DATE:
                first = int(qty * 0.6)
                parts = [(recv_date, first), (second, qty - first)]    # split delivery
            else:
                parts = [(recv_date, qty)]
            if fill == 1.0 or (AS_OF_DATE - h["expected_date"]).days > 14:
                status = "Closed"
        for d, q in parts:
            r = rng.random()
            qstat = "Available" if r < 0.93 else ("Quarantine" if r < 0.97 else "Damaged")
            if sku_batch_managed[sku] == 1:
                batch = f"0{int(rng.integers(400000, 560000))}"
                expiry = (d + pd.Timedelta(days=int(rng.integers(365, 1200)))).strftime("%Y-%m-%d")
            else:
                batch, expiry = None, None
            rec_rows.append({"po_number": po_number, "po_line": ln,
                             "supplier_id": h["supplier_id"], "sku": sku,
                             "batch": batch, "expiry_date": expiry,
                             "qty_received": int(q), "quality_status": qstat,
                             "recv_date": d})
        po_rows.append({"po_number": po_number, "po_line": ln, "supplier_id": h["supplier_id"],
                        "sku": sku, "expected_qty": exp_qty, "po_status": status,
                        "created_date": h["created_date"], "expected_date": h["expected_date"]})

purchase_orders = pd.DataFrame(po_rows)
receipts = pd.DataFrame(rec_rows)
receipts = receipts.sort_values(["recv_date", "po_number", "po_line"]).reset_index(drop=True)
grp = receipts.groupby(["recv_date", "po_number"], sort=True).ngroup()
receipts["grn_number"] = ["GRN" + f"{g + 1:06d}" for g in grp]
receipts["grn_line"] = receipts.groupby("grn_number").cumcount() + 1
n_grn = int(grp.max()) + 1
grn_time = (rng.integers(6, 17, n_grn) * 3600 + rng.integers(0, 3600, n_grn))
receipts["received_datetime"] = receipts["recv_date"] + pd.to_timedelta(grn_time[grp.to_numpy()], unit="s")
receipts["dock"] = [f"DOCK-{d}" for d in rng.integers(1, 5, n_grn)[grp.to_numpy()]]
receipts["received_by"] = [f"USER{u:02d}" for u in rng.integers(1, 9, n_grn)[grp.to_numpy()]]
receipts = receipts[["grn_number", "grn_line", "po_number", "po_line", "supplier_id", "sku",
                     "batch", "expiry_date", "qty_received", "quality_status",
                     "received_datetime", "dock", "received_by"]]

# ---------------------------------------------------------------------------
# 4. ORDERS, ORDER LINES, SHIPMENTS  (outbound)
# ---------------------------------------------------------------------------
days = pd.date_range(START, AS_OF_DATE, freq="D")
dow_w = {0: 1.35, 1: 1.10, 2: 1.00, 3: 1.00, 4: 1.05, 5: 0.45, 6: 0.15}
w = np.array([dow_w[d.dayofweek] for d in days])
is_month_end = np.array([(d + pd.offsets.MonthEnd(0) - d).days <= 2 for d in days])
w[is_month_end] *= 1.6
promo_day = pd.Timestamp("2026-09-11")
w[days == promo_day] *= 3.0
month_end_days = set(days[is_month_end])
counts = rng.multinomial(N_ORDERS, w / w.sum())

hours = np.arange(6, 18)
hour_p = np.array([3, 5, 8, 9, 9, 8, 8, 8, 7, 6, 4, 2], dtype=float)
hour_p /= hour_p.sum()
created_list = []
for d, c in zip(days, counts):
    hh = rng.choice(hours, size=c, p=hour_p)
    mm = rng.integers(0, 60, size=c)
    ss = rng.integers(0, 60, size=c)
    for a, b, s in zip(hh, mm, ss):
        created_list.append(d + pd.Timedelta(hours=int(a), minutes=int(b), seconds=int(s)))
created_list.sort()

# customer pools (zipf-ish: a few big customers, many small)
def zipf(n, a=0.8):
    x = 1.0 / np.arange(1, n + 1) ** a
    return x / x.sum()


by_type = {t: customers.loc[customers["customer_type"] == t, "customer_id"].tolist()
           for t in customers["customer_type"].unique()}
std_pool = by_type["Pharmacy"] + by_type["Department Store"] + by_type["Salon"] + by_type["Distributor"]
rng.shuffle(std_pool)
pools = {"E-Com": by_type["E-Com"], "Standard": std_pool, "Promo": std_pool,
         "Internal": by_type["Internal"], "Export": by_type["Distributor"]}
pool_w = {k: zipf(len(v)) for k, v in pools.items()}

ORDER_TYPES = ["E-Com", "Standard", "Promo", "Internal", "Export"]
ORDER_P = [0.52, 0.26, 0.16, 0.04, 0.02]
PRIORITIES = ["High", "Medium", "Low"]
PRIO_P = [0.10, 0.30, 0.60]
LEAD_DAYS = {"High": 1, "Medium": 2, "Low": 3}
PICK_MED = {"High": 2.0, "Medium": 5.0, "Low": 12.0}      # median hours to pick
SHIP_MED = {"High": 2.0, "Medium": 4.0, "Low": 8.0}       # median hours to ship after picking
CARRIERS = ["Swift Freight", "RoadLink", "BlueLine Express", "Atlas Couriers", "Metro Parcels"]

pop_w = zipf(N_PRODUCTS, 0.6)
pop_w = pop_w[rng.permutation(N_PRODUCTS)]               # popularity not tied to SKU order


def next_working(ts):
    """Warehouse works Mon-Sat 06:00-18:00. Push a timestamp into that window."""
    if ts.hour >= 18:
        ts = ts.normalize() + pd.Timedelta(days=1, hours=6, minutes=int(ts.minute))
    elif ts.hour < 6:
        ts = ts.normalize() + pd.Timedelta(hours=6, minutes=int(ts.minute))
    if ts.dayofweek == 6:
        ts = ts.normalize() + pd.Timedelta(days=1, hours=6, minutes=int(ts.minute))
    return ts


order_rows, line_rows, ship_rows = [], [], []
for i, created in enumerate(created_list):
    order_id = f"SO{1000000 + i}"
    otype = str(rng.choice(ORDER_TYPES, p=ORDER_P))
    prio = str(rng.choice(PRIORITIES, p=PRIO_P))
    cust_id = str(rng.choice(pools[otype], p=pool_w[otype]))
    lead = LEAD_DAYS[prio] + (3 if otype == "Export" else 0)
    promised = created.normalize() + pd.Timedelta(days=lead)
    cancelled = rng.random() < 0.015
    stuck = (not cancelled) and created < pd.Timestamp("2026-09-26") and rng.random() < 0.008

    if otype == "E-Com":
        n_lines = int(np.clip(1 + rng.poisson(0.8), 1, 4))
    elif otype == "Internal":
        n_lines = int(np.clip(2 + rng.poisson(3), 2, 12))
    else:
        n_lines = int(np.clip(2 + rng.poisson(7), 2, 20))
    skus = rng.choice(sku_arr, size=n_lines, replace=False, p=pop_w)

    # planted story 3: month-end peaks (and Mondays / promo day) slow everything down
    mult = 1.0
    if created.normalize() in month_end_days:
        mult *= 2.0
    if created.dayofweek == 0:
        mult *= 1.3
    if created.normalize() == promo_day:
        mult *= 1.5
    pick_h = float(rng.lognormal(np.log(PICK_MED[prio]), 0.6)) * mult
    ship_h = float(rng.lognormal(np.log(SHIP_MED[prio]), 0.6)) * mult

    lines = []
    for ln, sku in enumerate(skus, start=1):
        if otype == "E-Com":
            ordered = int(rng.choice([1, 2, 3], p=[0.7, 0.2, 0.1]))
        elif otype == "Internal":
            ordered = int(rng.integers(1, 25))
        elif otype == "Export":
            ordered = int(rng.choice([48, 96, 240, 480]))
        else:
            ordered = int(rng.choice([6, 12, 24, 48, 96, 120], p=[0.15, 0.25, 0.25, 0.20, 0.10, 0.05]))
        rec = {"order_id": order_id, "line_no": ln, "sku": sku, "ordered_qty": ordered,
               "allocated_qty": None, "pick_location_id": None, "picked_sku": None,
               "picked_qty": None, "picked_datetime": pd.NaT, "shipped_qty": None}
        if not cancelled:
            # planted story 1 (again): SUP-03 SKUs hit stock-outs far more often
            p_out = 0.03 if sku_supplier[sku] == SHORT_SUPPLIER else 0.004
            if rng.random() < p_out:
                alloc = int(ordered * float(rng.uniform(0.2, 0.9)))
                alloc = alloc if ordered > 1 else 0
            else:
                alloc = ordered
            loc = str(rng.choice(avail_locs[sku]))
            # planted story 2: Zone C has a much higher pick-error rate
            p_err = 0.025 if loc[0] == "C" else 0.0025
            p_sku, p_qty = sku, alloc
            if rng.random() < p_err:
                kind = rng.choice(["wrong_sku", "short", "over"], p=[0.5, 0.3, 0.2])
                if kind == "short" and alloc > 0:
                    p_qty = max(0, alloc - max(1, int(alloc * float(rng.uniform(0.05, 0.3)))))
                elif kind == "over":
                    p_qty = alloc + max(1, int(alloc * float(rng.uniform(0.05, 0.3))))
                else:
                    same_zone = [s for s in sku_arr if sku_zone[s] == loc[0] and s != sku]
                    p_sku = str(rng.choice(same_zone))
            rec.update({"allocated_qty": alloc, "pick_location_id": loc,
                        "picked_sku": p_sku, "picked_qty": p_qty,
                        "picked_datetime": next_working(
                            created + pd.Timedelta(hours=pick_h)
                            + pd.Timedelta(minutes=int(rng.integers(0, 61))))})
        lines.append(rec)

    status, shipped_dt = "Cancelled", pd.NaT
    if not cancelled:
        done = max(r["picked_datetime"] for r in lines)
        packed = next_working(done + pd.Timedelta(hours=0.5 * ship_h))
        shipped = next_working(done + pd.Timedelta(hours=ship_h))
        if stuck:
            status = str(rng.choice(["Picking", "Picked", "Packed"], p=[0.2, 0.5, 0.3]))
            if status == "Picking":
                lines[-1].update({"picked_sku": None, "picked_qty": None, "picked_datetime": pd.NaT})
        elif shipped <= AS_OF:
            status, shipped_dt = "Shipped", shipped
        elif packed <= AS_OF:
            status = "Packed"
        elif done <= AS_OF:
            status = "Picked"
        else:
            n_done = sum(1 for r in lines if r["picked_datetime"] <= AS_OF)
            status = "Picking" if n_done > 0 else "Created"
        # nothing can be recorded as picked in the future
        for r in lines:
            if pd.notna(r["picked_datetime"]) and r["picked_datetime"] > AS_OF:
                r.update({"picked_sku": None, "picked_qty": None, "picked_datetime": pd.NaT})
        if status == "Created":
            for r in lines:
                r.update({"picked_sku": None, "picked_qty": None, "picked_datetime": pd.NaT})
        if status == "Shipped":
            for r in lines:
                r["shipped_qty"] = r["picked_qty"] if r["picked_sku"] == r["sku"] else 0
            ship_rows.append({"order_id": order_id, "shipped_datetime": shipped_dt,
                              "carrier": str(rng.choice(CARRIERS))})

    order_rows.append({"order_id": order_id, "customer_id": cust_id, "order_type": otype,
                       "priority": prio, "created_datetime": created, "promised_date": promised,
                       "status": status})
    line_rows.extend(lines)

orders = pd.DataFrame(order_rows)
order_lines = pd.DataFrame(line_rows)
for c in ["allocated_qty", "picked_qty", "shipped_qty"]:
    order_lines[c] = order_lines[c].astype("Int64")
shipments = pd.DataFrame(ship_rows)
shipments.insert(0, "shipment_id", [f"SH{2000000 + i}" for i in range(len(shipments))])

# ---------------------------------------------------------------------------
# 5. CYCLE COUNTS
# ---------------------------------------------------------------------------
pick = rng.choice(len(stock), size=N_CYCLE_COUNTS, replace=False)
cc = stock.iloc[pick][["location_id", "sku", "batch", "qty_on_hand"]].reset_index(drop=True)
cc = cc.rename(columns={"qty_on_hand": "system_qty"})
counted = []
for q in cc["system_qty"]:
    if rng.random() < 0.955:
        counted.append(int(q))
    else:
        d = int(rng.integers(1, max(2, int(round(q * 0.1)) + 1)))
        counted.append(max(0, int(q) + (d if rng.random() < 0.5 else -d)))
cc["counted_qty"] = counted
cc["count_status"] = np.where(rng.random(len(cc)) < 0.95, "Count complete", "Booked")
cc.loc[cc["count_status"] == "Booked", "counted_qty"] = np.nan
cc["counted_qty"] = cc["counted_qty"].astype("Int64")
cc["count_date"] = pd.Timestamp("2026-07-15") + pd.to_timedelta(rng.integers(0, 78, len(cc)), unit="D")
cc.insert(0, "count_id", [f"CC{i:05d}" for i in range(1, len(cc) + 1)])
cycle_counts = cc[["count_id", "location_id", "sku", "batch", "system_qty",
                   "counted_qty", "count_date", "count_status"]]

# ---------------------------------------------------------------------------
# 6. DECIDE WHICH ROWS GET "MESS" (needed first, so control totals can exclude them)
# ---------------------------------------------------------------------------
# bad timestamps on shipments + shipped orders with no shipment record
n_bad_ts = int(round(0.003 * len(shipments)))
n_missing = int(round(0.005 * len(shipments)))
pick_idx = rng.choice(len(shipments), size=n_bad_ts + n_missing, replace=False)
bad_ts_idx, missing_idx = pick_idx[:n_bad_ts], pick_idx[n_bad_ts:]
bad_ts_orders = set(shipments.iloc[bad_ts_idx]["order_id"])
missing_orders = set(shipments.iloc[missing_idx]["order_id"])
exclude_orders = bad_ts_orders | missing_orders

# negative stock quantities
neg_ids = set(int(x) for x in rng.choice(stock["stock_id"], size=5, replace=False))

# ---------------------------------------------------------------------------
# 7. CONTROL TOTALS  (KPIs on the clean data, after removing flagged rows)
# ---------------------------------------------------------------------------
def build_control_totals():
    out = []
    # OTIF
    o = orders[(orders["status"] != "Cancelled") & (orders["promised_date"] <= AS_OF_DATE)]
    o = o[~o["order_id"].isin(exclude_orders)].merge(shipments[["order_id", "shipped_datetime"]],
                                                       on="order_id", how="left")
    ol = order_lines.copy()
    ol["in_full"] = (ol["shipped_qty"] == ol["ordered_qty"]).fillna(False).astype(bool)
    full = ol.groupby("order_id")["in_full"].all()
    o["in_full"] = o["order_id"].map(full).fillna(False).astype(bool)
    o["on_time"] = o["shipped_datetime"].notna() & (o["shipped_datetime"].dt.normalize() <= o["promised_date"])
    otif = (o["in_full"] & o["on_time"]).mean() * 100
    out.append(("OTIF %", round(otif, 2), "Non-cancelled orders due by 30 Sep, flagged rows excluded"))
    out.append(("Orders due (OTIF denominator)", len(o), ""))
    out.append(("On-time % (ignoring in-full)", round(o["on_time"].mean() * 100, 2), "Helper"))
    out.append(("In-full % (ignoring on-time)", round(o["in_full"].mean() * 100, 2), "Helper"))
    # Receiving completion
    po_ok = purchase_orders[purchase_orders["po_status"] != "Cancelled"]
    out.append(("Receiving Completion %",
                round(receipts["qty_received"].sum() / po_ok["expected_qty"].sum() * 100, 2),
                "Units received / units expected, cancelled PO lines excluded"))
    # Available stock
    st = stock[~stock["stock_id"].isin(neg_ids)]
    out.append(("Available Stock %",
                round(st.loc[st["quality_status"] == "Available", "qty_on_hand"].sum()
                      / st["qty_on_hand"].sum() * 100, 2),
                "Negative-quantity rows excluded"))
    # Pick accuracy
    pl = order_lines[order_lines["picked_datetime"].notna()]
    ok = (pl["picked_sku"] == pl["sku"]) & (pl["picked_qty"] == pl["allocated_qty"])
    out.append(("Pick Accuracy %", round(ok.mean() * 100, 2),
                "Right SKU and picked qty = allocated qty"))
    # Cycle time
    s = shipments[~shipments["order_id"].isin(exclude_orders)].merge(
        orders[["order_id", "created_datetime"]], on="order_id")
    hrs = (s["shipped_datetime"] - s["created_datetime"]).dt.total_seconds() / 3600
    out.append(("Order Cycle Time (hrs)", round(hrs.mean(), 2), "Shipped orders, flagged rows excluded"))
    # Inventory accuracy
    done = cycle_counts[cycle_counts["count_status"] == "Count complete"]
    out.append(("Inventory Accuracy %",
                round((done["counted_qty"] == done["system_qty"]).mean() * 100, 2),
                "Completed count lines only"))
    return pd.DataFrame(out, columns=["kpi", "expected_value", "note"])


control = build_control_totals()

# ---------------------------------------------------------------------------
# 8. INJECT THE MESS
# ---------------------------------------------------------------------------
STATUS_VARIANTS = {
    "Available": ["AVAILABLE", "available ", " Available", "In Stock", "INSTOCK"],
    "Quarantine": ["QUARANTINE", "Quarantined", "quarantine "],
    "Damaged": ["DAMAGED", "damaged", "Damage"],
    "Returns": ["RETURNS", "returns"],
    "Expired": ["EXPIRED", "expired "],
}


def dirty_status(series, share=0.08):
    s = series.copy()
    hit = rng.random(len(s)) < share
    s[hit] = [str(rng.choice(STATUS_VARIANTS[v])) for v in s[hit]]
    return s, int(hit.sum())


mess = []

# --- receipts ---------------------------------------------------------------
rc = receipts.copy()
rc["quality_status"], n = dirty_status(rc["quality_status"])
mess.append(("receipts", "quality_status", "Inconsistent labels (case, spaces, synonyms)", n,
             "Trim, upper/lower-case and map to 5 standard statuses"))
txt = fmt_dt(rc["received_datetime"])
alt = rng.random(len(rc)) < 0.15
txt[alt] = pd.to_datetime(rc.loc[alt, "received_datetime"]).dt.strftime("%d/%m/%Y %H:%M")
rc["received_datetime"] = txt
mess.append(("receipts", "received_datetime", "15% of rows use DD/MM/YYYY HH:MM instead of YYYY-MM-DD HH:MM:SS",
             int(alt.sum()), "Parse both formats into one DATETIME column"))
rc["expiry_date"] = rc["expiry_date"]
dups = rc.sample(n=int(round(0.01 * len(rc))), random_state=SEED)
rc = pd.concat([rc, dups], ignore_index=True).sort_values(["grn_number", "grn_line"], kind="stable")
mess.append(("receipts", "grn_number + grn_line", "Exact duplicate rows", len(dups),
             "Keep one row per (grn_number, grn_line)"))

# --- stock snapshot -----------------------------------------------------------
sk = stock.copy()
sk["quality_status"], n = dirty_status(sk["quality_status"])
mess.append(("stock_snapshot", "quality_status", "Inconsistent labels (case, spaces, synonyms)", n,
             "Trim, upper/lower-case and map to 5 standard statuses"))
cand = sk.index[~sk["stock_id"].isin(neg_ids)]
miss_loc = rng.choice(cand, size=int(round(0.005 * len(sk))), replace=False)
sk.loc[miss_loc, "location_id"] = np.nan
mess.append(("stock_snapshot", "location_id", "Missing location", len(miss_loc),
             "Keep the quantity, assign location 'UNKNOWN'"))
cand = sk.index[sk["expiry_date"].notna() & ~sk.index.isin(miss_loc)]
null_exp = rng.choice(cand, size=int(round(0.02 * len(sk))), replace=False)
sk.loc[null_exp, "expiry_date"] = np.nan
mess.append(("stock_snapshot", "expiry_date", "Missing expiry on batch-managed stock", len(null_exp),
             "Leave as NULL, report as 'Unknown' expiry bucket"))
sk.loc[sk["stock_id"].isin(neg_ids), "qty_on_hand"] *= -1
mess.append(("stock_snapshot", "qty_on_hand", "Negative quantity (sign error)", len(neg_ids),
             "Flag as invalid and exclude from stock totals"))

# --- shipments --------------------------------------------------------------------
sh = shipments.copy()
created_map = orders.set_index("order_id")["created_datetime"]
for idx in bad_ts_idx:
    oid = sh.iloc[idx]["order_id"]
    sh.iloc[idx, sh.columns.get_loc("shipped_datetime")] = (
        created_map[oid] - pd.Timedelta(hours=int(rng.integers(1, 49))))
sh = sh.drop(sh.index[missing_idx]).reset_index(drop=True)
mess.append(("shipments", "shipped_datetime", "Shipped BEFORE the order was created", n_bad_ts,
             "Flag as invalid; exclude from OTIF and Order Cycle Time"))
mess.append(("orders / shipments", "order_id", "Orders with status 'Shipped' but no shipment record", n_missing,
             "Flag; exclude from OTIF and Order Cycle Time"))

# --- write everything -----------------------------------------------------------------
orders_out = orders.copy()
orders_out["created_datetime"] = fmt_dt(orders_out["created_datetime"])
orders_out["promised_date"] = fmt_d(orders_out["promised_date"])
lines_out = order_lines.copy()
lines_out["picked_datetime"] = fmt_dt(lines_out["picked_datetime"])
sh["shipped_datetime"] = fmt_dt(sh["shipped_datetime"])
po_out = purchase_orders.copy()
po_out["created_date"] = fmt_d(po_out["created_date"])
po_out["expected_date"] = fmt_d(po_out["expected_date"])
cc_out = cycle_counts.copy()
cc_out["count_date"] = fmt_d(cc_out["count_date"])

files = {
    "products": products, "suppliers": suppliers, "customers": customers,
    "locations": locations, "purchase_orders": po_out, "receipts": rc,
    "stock_snapshot": sk, "orders": orders_out, "order_lines": lines_out,
    "shipments": sh, "cycle_counts": cc_out,
}
for name, df in files.items():
    df.to_csv(DATA / f"{name}.csv", index=False, encoding="utf-8")

pd.DataFrame(mess, columns=["table", "column", "issue", "rows_affected", "expected_handling"]) \
    .rename_axis("issue_id").reset_index().assign(issue_id=lambda d: d["issue_id"] + 1) \
    .to_csv(DATA / "mess_log.csv", index=False, encoding="utf-8")
control.to_csv(DATA / "control_totals.csv", index=False, encoding="utf-8")

print("Done. Files written to:", DATA)
for name, df in files.items():
    print(f"  {name:<16} {len(df):>7,} rows")
print("\nControl totals (what your SQL / Power BI should reproduce after cleaning):")
print(control[["kpi", "expected_value"]].to_string(index=False))
