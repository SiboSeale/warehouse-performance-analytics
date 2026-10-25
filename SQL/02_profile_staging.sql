-- 1. Duplicate GRN rows
SELECT SUM(c - 1) AS dup_grn_rows FROM (
    SELECT COUNT(*) AS c FROM stg.receipts
    GROUP BY grn_number, grn_line HAVING COUNT(*) > 1) d;

-- 2. Receipts with DD/MM/YYYY dates
SELECT COUNT(*) AS odd_date_rows FROM stg.receipts
WHERE received_datetime LIKE '[0-3][0-9]/[0-1][0-9]/%';

-- 3. Stock rows with no location
SELECT COUNT(*) AS no_location FROM stg.stock_snapshot
WHERE location_id IS NULL OR LTRIM(RTRIM(location_id)) = '';

-- 4. Negative stock quantities
SELECT COUNT(*) AS negative_qty FROM stg.stock_snapshot
WHERE TRY_CAST(qty_on_hand AS INT) < 0;

-- 5. Shipped before created
SELECT COUNT(*) AS shipped_before_created
FROM stg.shipments s JOIN stg.orders o ON o.order_id = s.order_id
WHERE TRY_CAST(s.shipped_datetime AS DATETIME2) < TRY_CAST(o.created_datetime AS DATETIME2);

-- 6. Shipped orders with no shipment record
SELECT COUNT(*) AS shipped_no_record FROM stg.orders o
WHERE o.status = 'Shipped'
  AND NOT EXISTS (SELECT 1 FROM stg.shipments s WHERE s.order_id = o.order_id);