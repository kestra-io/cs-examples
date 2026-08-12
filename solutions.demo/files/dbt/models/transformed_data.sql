select
  id,
  cast(created_at AS TIMESTAMP) as timestamp,
  upper(val),
  qty
from {{ ref('raw_data') }}