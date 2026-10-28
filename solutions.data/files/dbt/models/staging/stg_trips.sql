select
    try_cast(tpep_pickup_datetime as timestamp_ntz)  as pickup_datetime,
    try_cast(tpep_dropoff_datetime as timestamp_ntz) as dropoff_datetime,
    datediff(
        'minute',
        try_cast(tpep_pickup_datetime as timestamp_ntz),
        try_cast(tpep_dropoff_datetime as timestamp_ntz)
    )                                                as trip_duration_minutes,
    try_cast(PULocationID as int)                    as pickup_location_id,
    try_cast(trip_distance as float)                 as trip_distance,
    try_cast(total_amount as float)                  as total_amount,
    try_cast(tip_amount as float)                    as tip_amount
from {{ source('raw', 'yellow_tripdata_raw') }}