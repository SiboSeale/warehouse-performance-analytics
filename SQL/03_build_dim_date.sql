USE WMSDB;
GO
DROP TABLE IF EXISTS dw.dim_date;
GO
CREATE TABLE dw.dim_date (
    date_key          INT         NOT NULL PRIMARY KEY,
    full_date         DATE        NOT NULL,
    year_num          INT,
    quarter_num       INT,
    month_num         INT,
    month_name        VARCHAR(10),
    year_month        VARCHAR(10),
    day_of_month      INT,
    day_name          VARCHAR(10),
    day_of_week       INT,          -- 1 = Monday ... 7 = Sunday
    is_weekend        BIT,
    is_month_end_peak BIT           -- last 3 days of the month
);
GO
DECLARE @start DATE = '2026-05-01', @end DATE = '2026-12-31';

WITH d AS (
    SELECT @start AS dt
    UNION ALL
    SELECT DATEADD(DAY, 1, dt) FROM d WHERE dt < @end
)
INSERT INTO dw.dim_date
SELECT
    CONVERT(INT, CONVERT(CHAR(8), dt, 112)),
    dt,
    YEAR(dt),
    DATEPART(QUARTER, dt),
    MONTH(dt),
    DATENAME(MONTH, dt),
    LEFT(CONVERT(CHAR(10), dt, 120), 7),
    DAY(dt),
    DATENAME(WEEKDAY, dt),
    (DATEDIFF(DAY, '1900-01-01', dt) % 7) + 1,
    CASE WHEN (DATEDIFF(DAY, '1900-01-01', dt) % 7) + 1 IN (6, 7) THEN 1 ELSE 0 END,
    CASE WHEN DATEDIFF(DAY, dt, EOMONTH(dt)) <= 2 THEN 1 ELSE 0 END
FROM d
OPTION (MAXRECURSION 1000);

-- "Unknown" row for facts with a missing date
INSERT INTO dw.dim_date
VALUES (19000101, '1900-01-01', 1900, 1, 1, 'Unknown', 'Unknown', 1, 'Unknown', 1, 0, 0);

-- Checking
SELECT COUNT(*) AS total_rows,
       SUM(CAST(is_month_end_peak AS INT)) AS peak_days
FROM dw.dim_date;

