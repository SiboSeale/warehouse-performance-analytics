USE WMSDB;
GO

DROP TABLE IF EXISTS dw.fact_cycle_counts;
CREATE TABLE dw.fact_cycle_counts (
    count_id          VARCHAR(20) NOT NULL PRIMARY KEY,
    count_date_key    INT         NOT NULL,
    location_key      INT         NOT NULL,
    product_key       INT         NOT NULL,
    batch             VARCHAR(20),
    count_status      VARCHAR(20),
    system_qty        INT,
    counted_qty       INT,
    variance_qty      INT,                     -- counted minus system (completed counts only)
    is_count_complete BIT         NOT NULL,
    is_accurate       BIT                      -- NULL = count not completed yet
);
GO

INSERT INTO dw.fact_cycle_counts
SELECT
    c.count_id,
    ISNULL(d.date_key, 19000101),
    ISNULL(l.location_key, 0),
    ISNULL(p.product_key, 0),
    NULLIF(c.batch, ''),
    c.count_status,
    CAST(c.system_qty AS INT),
    TRY_CAST(NULLIF(c.counted_qty, '') AS INT),
    CASE WHEN c.count_status = 'Count complete'
         THEN TRY_CAST(NULLIF(c.counted_qty, '') AS INT) - CAST(c.system_qty AS INT) END,
    CASE WHEN c.count_status = 'Count complete' THEN 1 ELSE 0 END,
    CASE
        WHEN c.count_status <> 'Count complete' THEN NULL
        WHEN TRY_CAST(NULLIF(c.counted_qty, '') AS INT) = CAST(c.system_qty AS INT) THEN 1
        ELSE 0
    END
FROM stg.cycle_counts AS c
LEFT JOIN dw.dim_date AS d     ON d.full_date = CAST(c.count_date AS DATE)
LEFT JOIN dw.dim_location AS l ON l.location_id = c.location_id
LEFT JOIN dw.dim_product AS p  ON p.sku = c.sku;
GO

--Checking
SELECT COUNT(*) AS total_rows,
       CAST(100.0 * SUM(CAST(is_accurate AS INT)) / COUNT(is_accurate) AS DECIMAL(5,2)) AS inventory_accuracy_pct,
       SUM(CASE WHEN is_count_complete = 0 THEN 1 ELSE 0 END) AS booked_not_counted
FROM dw.fact_cycle_counts;

SELECT @@SERVERNAME;