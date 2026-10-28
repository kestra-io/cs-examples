select
    t.pickup_datetime,
    z.borough as pickup_borough,
    z.zone    as pickup_zone,
    t.trip_distance,
    t.trip_duration_minutes,
    t.total_amount,
    t.tip_amount
from {{ ref('stg_trips') }} t
join {{ ref('stg_zones') }} z
  on t.pickup_location_id = z.location_id