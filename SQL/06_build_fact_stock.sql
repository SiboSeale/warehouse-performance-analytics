USE WMSDB;
GO

DROP TABLE IF EXISTS dw.fact_stock;
CREATE TABLE dw.fact_stock (
    stock_id          INT         NOT NULL PRIMARY KEY,
    snapshot_date_key INT         NOT NULL,
    product_key       INT         NOT NULL,
    location_key      INT         NOT NULL,   -- 0 = unknown location
    quality_key       INT         NOT NULL,
    batch             VARCHAR(20),
    expiry_date       DATE,
    expiry_bucket     VARCHAR(20) NOT NULL,
    qty_on_hand       INT,
    is_valid          BIT         NOT NULL    -- 0 = negative quantity (bad data)
);
GO

WITH s AS (
    SELECT
        stock_id,
        snapshot_date,
        sku,
        batch,
        location_id,
        qty_on_hand,
        TRY_CAST(expiry_date AS DATE) AS expiry_dt,
        -- tidy the messy quality labels into the 5 standard ones
        CASE
            WHEN LTRIM(RTRIM(quality_status)) IN ('Available', 'In Stock', 'INSTOCK') THEN 'Available'
            WHEN LTRIM(RTRIM(quality_status)) IN ('Quarantine', 'Quarantined')        THEN 'Quarantine'
            WHEN LTRIM(RTRIM(quality_status)) IN ('Damaged', 'Damage')                THEN 'Damaged'
            WHEN LTRIM(RTRIM(quality_status)) = 'Returns'                             THEN 'Returns'
            WHEN LTRIM(RTRIM(quality_status)) = 'Expired'                             THEN 'Expired'
            ELSE 'Unknown'
        END AS quality_status
    FROM stg.stock_snapshot
)
INSERT INTO dw.fact_stock
SELECT
    CAST(s.stock_id AS INT),
    ISNULL(d.date_key, 19000101),
    ISNULL(p.product_key, 0),
    ISNULL(l.location_key, 0),            -- missing location -> Unknown (0), quantity is kept
    ISNULL(q.quality_key, 0),
    s.batch,
    s.expiry_dt,
    CASE
        WHEN s.expiry_dt IS NULL THEN 'Unknown'
        WHEN DATEDIFF(DAY, CAST(s.snapshot_date AS DATE), s.expiry_dt) < 0   THEN 'Expired'
        WHEN DATEDIFF(DAY, CAST(s.snapshot_date AS DATE), s.expiry_dt) <= 30 THEN '0-30 days'
        WHEN DATEDIFF(DAY, CAST(s.snapshot_date AS DATE), s.expiry_dt) <= 60 THEN '31-60 days'
        WHEN DATEDIFF(DAY, CAST(s.snapshot_date AS DATE), s.expiry_dt) <= 90 THEN '61-90 days'
        ELSE '90+ days'
    END,
    CAST(s.qty_on_hand AS INT),
    CASE WHEN CAST(s.qty_on_hand AS INT) < 0 THEN 0 ELSE 1 END
FROM s
LEFT JOIN dw.dim_date AS d           ON d.full_date = CAST(s.snapshot_date AS DATE)
LEFT JOIN dw.dim_product AS p        ON p.sku = s.sku
LEFT JOIN dw.dim_location AS l       ON l.location_id = s.location_id
LEFT JOIN dw.dim_quality_status AS q ON q.quality_status = s.quality_status;
GO

--Checking
SELECT COUNT(*) AS total_rows,
       CAST(100.0 * SUM(CASE WHEN f.is_valid = 1 AND q.is_available = 1 THEN f.qty_on_hand END)
                  / SUM(CASE WHEN f.is_valid = 1 THEN f.qty_on_hand END) AS DECIMAL(5,2)) AS available_stock_pct,
       SUM(CASE WHEN f.location_key = 0 THEN 1 ELSE 0 END) AS unknown_location_rows,
       SUM(CASE WHEN f.is_valid = 0 THEN 1 ELSE 0 END) AS invalid_rows
FROM dw.fact_stock AS f
JOIN dw.dim_quality_status AS q ON q.quality_key = f.quality_key;

-- Extra check to see if blank cells return NULLS
SELECT expiry_bucket, COUNT(*) AS n
FROM dw.fact_stock
GROUP BY expiry_bucket
ORDER BY expiry_bucket;