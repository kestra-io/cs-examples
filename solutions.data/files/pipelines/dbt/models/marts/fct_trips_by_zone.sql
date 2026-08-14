select
    z.borough,
    z.zone,
    count(*)              as trip_count,
    avg(t.trip_distance)  as avg_distance_miles,
    avg(t.total_amount)   as avg_fare
from {{ ref('stg_trips') }} t
join {{ ref('stg_zones') }} z
  on t.pickup_location_id = z.location_id
group by 1, 2
order by trip_count desc