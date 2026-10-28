select
    try_cast(LocationID as int) as location_id,
    Borough as borough,
    Zone    as zone
from {{ source('raw', 'taxi_zones_raw') }}