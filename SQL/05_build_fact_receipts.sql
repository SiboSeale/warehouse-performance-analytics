USE WMSDB;
GO

DROP TABLE IF EXISTS dw.fact_receipts;
CREATE TABLE dw.fact_receipts (
    po_number               VARCHAR(20) NOT NULL,
    po_line                 INT         NOT NULL,
    supplier_key            INT         NOT NULL,
    product_key             INT         NOT NULL,
    created_date_key        INT         NOT NULL,
    expected_date_key       INT         NOT NULL,
    first_received_date_key INT         NOT NULL,   -- 19000101 = nothing received yet
    po_status               VARCHAR(20),
    expected_qty            INT,
    received_qty            INT,
    rejected_qty            INT,                    -- received but Quarantine or Damaged
    PRIMARY KEY (po_number, po_line)
);
GO

WITH r AS (
    SELECT
        po_number,
        po_line,
        CAST(qty_received AS INT) AS qty,
        -- fix 1: tidy the messy quality labels into the standard ones
        CASE
            WHEN LTRIM(RTRIM(quality_status)) IN ('Available', 'In Stock', 'INSTOCK') THEN 'Available'
            WHEN LTRIM(RTRIM(quality_status)) IN ('Quarantine', 'Quarantined')        THEN 'Quarantine'
            WHEN LTRIM(RTRIM(quality_status)) IN ('Damaged', 'Damage')                THEN 'Damaged'
            WHEN LTRIM(RTRIM(quality_status)) = 'Returns'                             THEN 'Returns'
            WHEN LTRIM(RTRIM(quality_status)) = 'Expired'                             THEN 'Expired'
            ELSE 'Unknown'
        END AS quality_status,
        -- fix 2: two date formats -> one real datetime
        CASE
            WHEN received_datetime LIKE '[0-3][0-9]/[0-1][0-9]/%'
                THEN TRY_CONVERT(DATETIME2, received_datetime, 103)   -- DD/MM/YYYY HH:MM
            ELSE TRY_CONVERT(DATETIME2, received_datetime, 120)       -- YYYY-MM-DD HH:MM:SS
        END AS received_dt,
        -- fix 3: duplicates -> number the copies of each GRN line, keep copy 1 only
        ROW_NUMBER() OVER (PARTITION BY grn_number, grn_line ORDER BY (SELECT NULL)) AS rn
    FROM stg.receipts
),
r_po AS (
    SELECT
        po_number,
        po_line,
        SUM(qty) AS received_qty,
        SUM(CASE WHEN quality_status IN ('Quarantine', 'Damaged') THEN qty ELSE 0 END) AS rejected_qty,
        MIN(received_dt) AS first_received_dt
    FROM r
    WHERE rn = 1
    GROUP BY po_number, po_line
)
INSERT INTO dw.fact_receipts
SELECT
    p.po_number,
    CAST(p.po_line AS INT),
    ISNULL(s.supplier_key, 0),
    ISNULL(pr.product_key, 0),
    ISNULL(dc.date_key, 19000101),
    ISNULL(de.date_key, 19000101),
    ISNULL(dr.date_key, 19000101),
    p.po_status,
    CAST(p.expected_qty AS INT),
    ISNULL(x.received_qty, 0),
    ISNULL(x.rejected_qty, 0)
FROM stg.purchase_orders AS p
LEFT JOIN r_po AS x            ON x.po_number = p.po_number AND x.po_line = p.po_line
LEFT JOIN dw.dim_supplier AS s ON s.supplier_id = p.supplier_id
LEFT JOIN dw.dim_product AS pr ON pr.sku = p.sku
LEFT JOIN dw.dim_date AS dc    ON dc.full_date = CAST(p.created_date AS DATE)
LEFT JOIN dw.dim_date AS de    ON de.full_date = CAST(p.expected_date AS DATE)
LEFT JOIN dw.dim_date AS dr    ON dr.full_date = CAST(x.first_received_dt AS DATE);
GO

--Checking 
SELECT COUNT(*) AS total_rows,
       CAST(100.0 * SUM(CASE WHEN po_status <> 'Cancelled' THEN received_qty END)
                  / SUM(CASE WHEN po_status <> 'Cancelled' THEN expected_qty END) AS DECIMAL(5,2)) AS receiving_completion_pct,
       SUM(CASE WHEN received_qty > 0 AND first_received_date_key = 19000101 THEN 1 ELSE 0 END) AS bad_dates
FROM dw.fact_receipts;