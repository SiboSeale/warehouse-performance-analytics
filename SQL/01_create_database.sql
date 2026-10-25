CREATE DATABASE WMSDB;
GO
USE WMSDB;
GO
CREATE SCHEMA stg;
GO
CREATE SCHEMA dw;
GO

SELECT name FROM sys.schemas WHERE name IN ('stg','dw');

--Checking if the table loaded

SELECT COUNT(*) FROM stg.products;

-- One query check for all tables
SELECT 'products' AS tbl, COUNT(*) AS n FROM stg.products
UNION ALL SELECT 'suppliers', COUNT(*) FROM stg.suppliers
UNION ALL SELECT 'customers', COUNT(*) FROM stg.customers
UNION ALL SELECT 'locations', COUNT(*) FROM stg.locations
UNION ALL SELECT 'purchase_orders', COUNT(*) FROM stg.purchase_orders
UNION ALL SELECT 'receipts', COUNT(*) FROM stg.receipts
UNION ALL SELECT 'stock_snapshot', COUNT(*) FROM stg.stock_snapshot
UNION ALL SELECT 'orders', COUNT(*) FROM stg.orders
UNION ALL SELECT 'order_lines', COUNT(*) FROM stg.order_lines
UNION ALL SELECT 'shipments', COUNT(*) FROM stg.shipments
UNION ALL SELECT 'cycle_counts', COUNT(*) FROM stg.cycle_counts;