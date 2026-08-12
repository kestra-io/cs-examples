{{ config(materialized='table') }}
select
  model_name,
  count(*)                              as inspections,
  sum(case when result = 'pass' then 1 else 0 end) as passed,
  sum(case when result = 'fail' then 1 else 0 end) as failed,
  sum(case when result = 'rework' then 1 else 0 end) as reworked,
  avg(labor_hours)                      as avg_labor_hours
from {{ source('raw', 'aircraft_production_data') }}
group by model_name