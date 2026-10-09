-- Weather per city and hour, cleaned.
-- Adds Swedish local time and puts the unit in each column name.

with source as (

    select * from {{ source('raw', 'weather') }}

)

select
    city,
    time                                                  as time_utc,
    timezone('Europe/Stockholm', time at time zone 'UTC') as time_local,

    temperature_2m       as temperature_c,
    relative_humidity_2m as humidity_pct,
    precipitation        as precipitation_mm,
    wind_speed_10m       as wind_speed_kmh,
    wind_direction_10m   as wind_direction_deg

from source
