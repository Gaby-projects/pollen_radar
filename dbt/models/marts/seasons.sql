-- One row per city, pollen type and year: when the season starts, peaks and ends.
-- Method (Decision 2): cumulative sum of daily pollen over the year.
--   start = first day the running total reaches 5% of the year's total
--   end   = first day the running total reaches 95%
--   peak  = day with the highest daily average

with daily_long as (

    -- one row per city, day and pollen type (columns -> rows)
    unpivot (
        select
            city,
            date_local,
            alder_pollen_avg   as alder,
            birch_pollen_avg   as birch,
            grass_pollen_avg   as grass,
            mugwort_pollen_avg as mugwort
        from {{ ref('daily') }}
    )
    on alder, birch, grass, mugwort
    into name pollen_type value pollen

),

cumulative as (

    select
        *,
        year(date_local) as year,
        sum(pollen) over (
            partition by city, pollen_type, year(date_local)
            order by date_local
        ) as running_total,
        sum(pollen) over (
            partition by city, pollen_type, year(date_local)
        ) as year_total
    from daily_long

),

seasons as (

    select
        city,
        pollen_type,
        year,
        min(date_local) filter (where running_total >= 0.05 * year_total) as season_start,
        arg_max(date_local, pollen)                                       as peak_date,
        max(pollen)                                                       as peak_pollen,
        min(date_local) filter (where running_total >= 0.95 * year_total) as season_end,
        any_value(year_total)                                             as year_total
    from cumulative
    where year_total > 0
    group by city, pollen_type, year

)

select
    city,
    pollen_type,
    year,
    season_start,
    peak_date,
    season_end,
    week(season_start)                   as start_week,
    week(peak_date)                      as peak_week,
    week(season_end)                     as end_week,
    date_diff('day', season_start, season_end) + 1 as season_days,
    peak_pollen,
    year_total
from seasons
