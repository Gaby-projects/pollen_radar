-- Data quality report: how many values are missing (NULL) in raw,
-- per source, city, year and variable. One row per combination.

{% set sources = ['air_quality', 'weather'] %}

with counts as (

    {% for src in sources %}
    -- count(column) only counts non-NULL values
    unpivot (
        select
            '{{ src }}'   as source,
            city,
            year(time)    as year,
            count(*)      as n_rows,
            count(columns(* exclude (city, time, loaded_at)))
        from {{ source('raw', src) }}
        group by all
    )
    on columns(* exclude (source, city, year, n_rows))
    into name variable value n_values
    {% if not loop.last %}union all{% endif %}
    {% endfor %}

)

select
    source,
    city,
    year,
    variable,
    n_rows,
    n_rows - n_values                                   as n_missing,
    round(100.0 * (n_rows - n_values) / n_rows, 1)      as pct_missing
from counts
order by source, city, year, variable
