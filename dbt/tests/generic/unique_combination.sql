{#
    Fails if any combination of the given columns appears more than once.
    Example: columns [city, time_utc] -> one row per city and hour.
#}
{% test unique_combination(model, columns) %}

select
    {{ columns | join(', ') }},
    count(*) as n_rows
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1

{% endtest %}
