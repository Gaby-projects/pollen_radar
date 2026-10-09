-- Fails if a city is missing a day between its first and last day in marts.daily.
-- Returns the missing city + date combinations.

with bounds as (

    select city, min(date_local) as first_day, max(date_local) as last_day
    from {{ ref('daily') }}
    group by city

),

expected as (

    select
        city,
        cast(unnest(generate_series(first_day, last_day, interval 1 day)) as date) as date_local
    from bounds

)

select expected.city, expected.date_local
from expected
left join {{ ref('daily') }} as daily
    on  expected.city       = daily.city
    and expected.date_local = daily.date_local
where daily.city is null
