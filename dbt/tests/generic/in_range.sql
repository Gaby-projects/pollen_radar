{#
    Fails if the column has values outside [min_value, max_value].
    Example: humidity must be between 0 and 100 %.
#}
{% test in_range(model, column_name, min_value, max_value) %}

select {{ column_name }}
from {{ model }}
where {{ column_name }} < {{ min_value }}
   or {{ column_name }} > {{ max_value }}

{% endtest %}
