-- One row per city and day (Swedish date).
-- avg = typical level, max = worst hour, sum = daily total (rain).

select
    city,
    date_local,

    -- pollen (grains/m³)
    avg(alder_pollen)   as alder_pollen_avg,
    max(alder_pollen)   as alder_pollen_max,
    avg(birch_pollen)   as birch_pollen_avg,
    max(birch_pollen)   as birch_pollen_max,
    avg(grass_pollen)   as grass_pollen_avg,
    max(grass_pollen)   as grass_pollen_max,
    avg(mugwort_pollen) as mugwort_pollen_avg,
    max(mugwort_pollen) as mugwort_pollen_max,

    -- pollution (µg/m³)
    avg(pm2_5) as pm2_5_avg,
    max(pm2_5) as pm2_5_max,
    avg(pm10)  as pm10_avg,
    avg(ozone) as ozone_avg,
    max(ozone) as ozone_max,
    avg(no2)   as no2_avg,

    -- weather
    avg(temperature_c)    as temperature_avg_c,
    min(temperature_c)    as temperature_min_c,
    max(temperature_c)    as temperature_max_c,
    avg(humidity_pct)     as humidity_avg_pct,
    sum(precipitation_mm) as precipitation_mm,
    avg(wind_speed_kmh)   as wind_speed_avg_kmh,

    count(*) as n_hours

from {{ ref('hourly') }}
group by city, date_local
-- Only complete days: 24 hours, or 23/25 on the days clocks change.
-- Drops the partial first and last day of the period.
having count(*) >= 23
