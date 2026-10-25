USE WMSDB;
GO

DROP TABLE IF EXISTS dw.fact_order_lines;
CREATE TABLE dw.fact_order_lines (
    order_id          VARCHAR(20) NOT NULL,
    line_no           INT         NOT NULL,
    order_date_key    INT         NOT NULL,   -- date the order was created
    product_key       INT         NOT NULL,
    pick_location_key INT         NOT NULL,   -- 0 = nothing picked (e.g. cancelled)
    ordered_qty       INT,
    allocated_qty     INT,
    picked_qty        INT,
    shipped_qty       INT,
    picked_datetime   DATETIME2,
    is_pick_correct   BIT,                    -- NULL = line not picked
    PRIMARY KEY (order_id, line_no)
);
GO

INSERT INTO dw.fact_order_lines
SELECT
    l.order_id,
    CAST(l.line_no AS INT),
    ISNULL(d.date_key, 19000101),
    ISNULL(p.product_key, 0),
    ISNULL(loc.location_key, 0),
    CAST(l.ordered_qty AS INT),
    TRY_CAST(NULLIF(l.allocated_qty, '') AS INT),
    TRY_CAST(NULLIF(l.picked_qty, '') AS INT),
    TRY_CAST(NULLIF(l.shipped_qty, '') AS INT),
    TRY_CAST(NULLIF(l.picked_datetime, '') AS DATETIME2),
    CASE
        WHEN NULLIF(l.picked_datetime, '') IS NULL THEN NULL
        WHEN l.picked_sku = l.sku
         AND TRY_CAST(NULLIF(l.picked_qty, '') AS INT) = TRY_CAST(NULLIF(l.allocated_qty, '') AS INT) THEN 1
        ELSE 0
    END
FROM stg.order_lines AS l
LEFT JOIN stg.orders AS o        ON o.order_id = l.order_id
LEFT JOIN dw.dim_date AS d       ON d.full_date = CAST(o.created_datetime AS DATE)
LEFT JOIN dw.dim_product AS p    ON p.sku = l.sku
LEFT JOIN dw.dim_location AS loc ON loc.location_id = NULLIF(l.pick_location_id, '');
GO

--Checking
SELECT COUNT(*) AS total_rows,
       CAST(100.0 * SUM(CASE WHEN is_pick_correct = 1 THEN 1 ELSE 0 END)
                  / COUNT(is_pick_correct) AS DECIMAL(5,2)) AS pick_accuracy_pct,
       SUM(CASE WHEN is_pick_correct IS NULL THEN 1 ELSE 0 END) AS not_picked_lines
FROM dw.fact_order_lines;

