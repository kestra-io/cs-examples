WITH buckets AS (
    SELECT
        symbol,
        DATEADD(
            minute,
            -MOD(DATE_PART(minute, time), 5),
            DATE_TRUNC('minute', time)
        ) AS bucket_start,
        price,
        quantity,
        time
    FROM demo.public.trades
),

agg AS (
    SELECT
        symbol,
        bucket_start,
        SUM(quantity) AS total_quantity,
        SUM(price * quantity) / NULLIF(SUM(quantity), 0) AS vwap,
        MAX(price) AS high,
        MIN(price) AS low
    FROM buckets
    GROUP BY symbol, bucket_start
),

open_close AS (
    SELECT
        symbol,
        bucket_start,
        FIRST_VALUE(price) OVER (PARTITION BY symbol, bucket_start ORDER BY time ASC) AS open,
        FIRST_VALUE(price) OVER (PARTITION BY symbol, bucket_start ORDER BY time DESC) AS close
    FROM buckets
)

SELECT
    a.symbol,
    a.bucket_start,
    a.total_quantity,
    a.vwap,
    a.high,
    a.low,
    o.open,
    o.close
FROM agg a
JOIN (
    SELECT DISTINCT symbol, bucket_start, open, close
    FROM open_close
) o
    ON a.symbol = o.symbol AND a.bucket_start = o.bucket_start
ORDER BY a.symbol, a.bucket_start
