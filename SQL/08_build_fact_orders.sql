USE WMSDB;
GO

DROP TABLE IF EXISTS dw.fact_orders;
CREATE TABLE dw.fact_orders (
    order_id          VARCHAR(20)  NOT NULL PRIMARY KEY,
    customer_key      INT          NOT NULL,
    order_date_key    INT          NOT NULL,
    promised_date_key INT          NOT NULL,
    shipped_date_key  INT          NOT NULL,   -- 19000101 = not shipped
    order_type        VARCHAR(20),
    priority          VARCHAR(10),
    status            VARCHAR(20),
    created_datetime  DATETIME2,
    promised_date     DATE,
    shipped_datetime  DATETIME2,
    line_count        INT,
    ordered_units     INT,
    is_valid_for_kpi  BIT          NOT NULL,   -- 0 = bad timestamp or shipped with no shipment record
    is_otif_eligible  BIT          NOT NULL,   -- due by 30 Sep, not cancelled, data is valid
    is_on_time        BIT          NOT NULL,
    is_in_full        BIT          NOT NULL,
    is_otif           BIT          NOT NULL,
    cycle_time_hrs    DECIMAL(10,2)            -- created -> shipped, valid shipped orders only
);
GO

DECLARE @as_of DATE = '2026-09-30';

WITH lines AS (
    SELECT order_id,
           COUNT(*)         AS line_count,
           SUM(ordered_qty) AS ordered_units,
           MIN(CASE WHEN shipped_qty = ordered_qty THEN 1 ELSE 0 END) AS all_in_full
    FROM dw.fact_order_lines
    GROUP BY order_id
),
ord AS (
    SELECT
        o.order_id, o.customer_id, o.order_type, o.priority, o.status,
        TRY_CAST(o.created_datetime AS DATETIME2) AS created_dt,
        TRY_CAST(o.promised_date AS DATE)         AS promised_dt,
        TRY_CAST(NULLIF(s.shipped_datetime, '') AS DATETIME2) AS shipped_dt,
        CASE WHEN o.status = 'Shipped' AND s.order_id IS NULL THEN 1 ELSE 0 END AS no_ship_record
    FROM stg.orders AS o
    LEFT JOIN stg.shipments AS s ON s.order_id = o.order_id
),
chk AS (
    SELECT ord.*,
           CASE WHEN no_ship_record = 1 OR shipped_dt < created_dt THEN 0 ELSE 1 END AS is_valid_for_kpi
    FROM ord
),
calc AS (
    SELECT c.*,
           ISNULL(l.line_count, 0)    AS line_count,
           ISNULL(l.ordered_units, 0) AS ordered_units,
           CASE WHEN c.status <> 'Cancelled' AND c.promised_dt <= @as_of AND c.is_valid_for_kpi = 1
                THEN 1 ELSE 0 END AS is_otif_eligible,
           CASE WHEN c.shipped_dt IS NOT NULL AND CAST(c.shipped_dt AS DATE) <= c.promised_dt
                THEN 1 ELSE 0 END AS is_on_time,
           ISNULL(l.all_in_full, 0)   AS is_in_full
    FROM chk AS c
    LEFT JOIN lines AS l ON l.order_id = c.order_id
)
INSERT INTO dw.fact_orders
SELECT
    k.order_id,
    ISNULL(cu.customer_key, 0),
    ISNULL(dc.date_key, 19000101),
    ISNULL(dp.date_key, 19000101),
    ISNULL(ds.date_key, 19000101),
    k.order_type,
    k.priority,
    k.status,
    k.created_dt,
    k.promised_dt,
    k.shipped_dt,
    k.line_count,
    k.ordered_units,
    k.is_valid_for_kpi,
    k.is_otif_eligible,
    k.is_on_time,
    k.is_in_full,
    CASE WHEN k.is_otif_eligible = 1 AND k.is_on_time = 1 AND k.is_in_full = 1 THEN 1 ELSE 0 END,
    CASE WHEN k.shipped_dt IS NOT NULL AND k.is_valid_for_kpi = 1
         THEN CAST(DATEDIFF(SECOND, k.created_dt, k.shipped_dt) / 3600.0 AS DECIMAL(10,2)) END
FROM calc AS k
LEFT JOIN dw.dim_customer AS cu ON cu.customer_id = k.customer_id
LEFT JOIN dw.dim_date AS dc     ON dc.full_date = CAST(k.created_dt AS DATE)
LEFT JOIN dw.dim_date AS dp     ON dp.full_date = k.promised_dt
LEFT JOIN dw.dim_date AS ds     ON ds.full_date = CAST(k.shipped_dt AS DATE);
GO

--Checking
SELECT COUNT(*) AS total_rows,
       SUM(CAST(is_otif_eligible AS INT)) AS orders_due,
       CAST(100.0 * SUM(CAST(is_otif AS INT)) / SUM(CAST(is_otif_eligible AS INT)) AS DECIMAL(5,2)) AS otif_pct,
       CAST(AVG(cycle_time_hrs) AS DECIMAL(5,2)) AS avg_cycle_hrs
FROM dw.fact_orders;
