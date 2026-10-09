-- Fails if a city has fewer hours than expected between its first and last hour.
-- In UTC every hour exists exactly once, so: hours = (last - first) + 1.

select
    city,
    count(*)                                                as n_hours,
    date_diff('hour', min(time_utc), max(time_utc)) + 1      as expected_hours
from {{ ref('hourly') }}
group by city
having count(*) <> date_diff('hour', min(time_utc), max(time_utc)) + 1
