{#
    Fails if the column has values below 0 (pollen, pollution, rain, wind).
#}
{% test not_negative(model, column_name) %}

select {{ column_name }}
from {{ model }}
where {{ column_name }} < 0

{% endtest %}
