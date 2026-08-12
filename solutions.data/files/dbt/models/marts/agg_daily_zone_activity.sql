select
    date_trunc('day', pickup_datetime) as trip_date,
    pickup_borough,
    pickup_zone,
    count(*) as total_trips,
    sum(total_amount) as total_revenue,
    avg(trip_distance) as avg_trip_distance_miles,
    avg(trip_duration_minutes) as avg_trip_duration_minutes,
    avg(tip_amount) as avg_tip_amount
from {{ ref('fct_taxi_trips') }}
group by 1, 2, 3
order by 1, total_trips desc
