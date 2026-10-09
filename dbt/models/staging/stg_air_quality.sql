-- Pollen and pollution per city and hour, cleaned.
-- 1. Adds Swedish local time next to UTC
-- 2. Empty pollen values (off-season 2021–2023) -> 0 (Decision 1)

with source as (

    select * from {{ source('raw', 'air_quality') }}

)

select
    city,
    time                                                  as time_utc,
    timezone('Europe/Stockholm', time at time zone 'UTC') as time_local,

    -- pollen (grains/m³)
    coalesce(alder_pollen, 0)   as alder_pollen,
    coalesce(birch_pollen, 0)   as birch_pollen,
    coalesce(grass_pollen, 0)   as grass_pollen,
    coalesce(mugwort_pollen, 0) as mugwort_pollen,

    -- pollution (µg/m³)
    pm2_5,
    pm10,
    ozone,
    nitrogen_dioxide            as no2

from source
