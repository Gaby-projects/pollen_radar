-- One row per city and ISO week (Monday–Sunday), built from daily.
-- avg = typical day in the week, max = worst day/hour in the week.

select
    city,
    isoyear(date_local)            as iso_year,
    week(date_local)               as iso_week,
    min(date_local)                as week_start,

    -- pollen (grains/m³)
    avg(alder_pollen_avg)   as alder_pollen_avg,
    max(alder_pollen_max)   as alder_pollen_max,
    avg(birch_pollen_avg)   as birch_pollen_avg,
    max(birch_pollen_max)   as birch_pollen_max,
    avg(grass_pollen_avg)   as grass_pollen_avg,
    max(grass_pollen_max)   as grass_pollen_max,
    avg(mugwort_pollen_avg) as mugwort_pollen_avg,
    max(mugwort_pollen_max) as mugwort_pollen_max,

    -- pollution (µg/m³)
    avg(pm2_5_avg) as pm2_5_avg,
    avg(ozone_avg) as ozone_avg,

    -- weather
    avg(temperature_avg_c)  as temperature_avg_c,
    sum(precipitation_mm)   as precipitation_mm,
    avg(wind_speed_avg_kmh) as wind_speed_avg_kmh,

    count(*) as n_days  -- 7 = complete week

from {{ ref('daily') }}
group by city, iso_year, iso_week
