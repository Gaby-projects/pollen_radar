-- One row per city and hour: pollen + pollution + weather together.
-- Base table for all other marts.

with air as (

    select * from {{ ref('stg_air_quality') }}

),

weather as (

    select * from {{ ref('stg_weather') }}

)

select
    air.city,
    air.time_utc,
    air.time_local,
    cast(air.time_local as date) as date_local,
    hour(air.time_local)         as hour_local,

    -- pollen (grains/m³)
    air.alder_pollen,
    air.birch_pollen,
    air.grass_pollen,
    air.mugwort_pollen,

    -- pollution (µg/m³)
    air.pm2_5,
    air.pm10,
    air.ozone,
    air.no2,

    -- weather
    weather.temperature_c,
    weather.humidity_pct,
    weather.precipitation_mm,
    weather.wind_speed_kmh,
    weather.wind_direction_deg

from air
left join weather
    on  air.city     = weather.city
    and air.time_utc = weather.time_utc
