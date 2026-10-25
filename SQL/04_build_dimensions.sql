USE WMSDB;
GO

-- ===== dim_supplier =====
DROP TABLE IF EXISTS dw.dim_supplier;
CREATE TABLE dw.dim_supplier (
    supplier_key  INT NOT NULL PRIMARY KEY,
    supplier_id   VARCHAR(20) NOT NULL,
    supplier_name VARCHAR(100),
    country       VARCHAR(50)
);
INSERT INTO dw.dim_supplier VALUES (0, 'UNKNOWN', 'Unknown', 'Unknown');
INSERT INTO dw.dim_supplier
SELECT ROW_NUMBER() OVER (ORDER BY supplier_id), supplier_id, supplier_name, country
FROM stg.suppliers;
GO

-- ===== dim_customer =====
DROP TABLE IF EXISTS dw.dim_customer;
CREATE TABLE dw.dim_customer (
    customer_key  INT NOT NULL PRIMARY KEY,
    customer_id   VARCHAR(20) NOT NULL,
    customer_name VARCHAR(100),
    city          VARCHAR(50),
    customer_type VARCHAR(30)
);
INSERT INTO dw.dim_customer VALUES (0, 'UNKNOWN', 'Unknown', 'Unknown', 'Unknown');
INSERT INTO dw.dim_customer
SELECT ROW_NUMBER() OVER (ORDER BY customer_id), customer_id, customer_name, city, customer_type
FROM stg.customers;
GO

-- ===== dim_location =====
DROP TABLE IF EXISTS dw.dim_location;
CREATE TABLE dw.dim_location (
    location_key  INT NOT NULL PRIMARY KEY,
    location_id   VARCHAR(20) NOT NULL,
    zone          VARCHAR(10),
    aisle         INT,
    location_type VARCHAR(30)
);
INSERT INTO dw.dim_location VALUES (0, 'UNKNOWN', 'Unknown', NULL, 'Unknown');
INSERT INTO dw.dim_location
SELECT ROW_NUMBER() OVER (ORDER BY location_id), location_id, zone,
       CAST(aisle AS INT), location_type
FROM stg.locations;
GO

-- ===== dim_product =====
DROP TABLE IF EXISTS dw.dim_product;
CREATE TABLE dw.dim_product (
    product_key     INT NOT NULL PRIMARY KEY,
    sku             VARCHAR(20) NOT NULL,
    description     VARCHAR(100),
    barcode         VARCHAR(20),
    product_type    VARCHAR(30),
    batch_managed   BIT,
    unit_weight_g   DECIMAL(10,1),
    unit_volume_cm3 DECIMAL(12,1),
    supplier_id     VARCHAR(20)
);
INSERT INTO dw.dim_product VALUES (0, 'UNKNOWN', 'Unknown', NULL, 'Unknown', 0, NULL, NULL, 'UNKNOWN');
INSERT INTO dw.dim_product
SELECT ROW_NUMBER() OVER (ORDER BY sku), sku, description, barcode, product_type,
       CAST(batch_managed AS BIT),
       CAST(unit_weight_g AS DECIMAL(10,1)),
       CAST(unit_volume_cm3 AS DECIMAL(12,1)),
       supplier_id
FROM stg.products;
GO

-- ===== dim_quality_status (the 5 standard labels) =====
DROP TABLE IF EXISTS dw.dim_quality_status;
CREATE TABLE dw.dim_quality_status (
    quality_key    INT NOT NULL PRIMARY KEY,
    quality_status VARCHAR(20) NOT NULL,
    is_available   BIT NOT NULL
);
INSERT INTO dw.dim_quality_status VALUES
    (0, 'Unknown', 0),
    (1, 'Available', 1),
    (2, 'Quarantine', 0),
    (3, 'Damaged', 0),
    (4, 'Returns', 0),
    (5, 'Expired', 0);
GO

-- Checking dimension tables
SELECT 'dim_supplier' AS tbl, COUNT(*) AS n FROM dw.dim_supplier
UNION ALL SELECT 'dim_customer', COUNT(*) FROM dw.dim_customer
UNION ALL SELECT 'dim_location', COUNT(*) FROM dw.dim_location
UNION ALL SELECT 'dim_product', COUNT(*) FROM dw.dim_product
UNION ALL SELECT 'dim_quality_status', COUNT(*) FROM dw.dim_quality_status;