-- Fails if a season ends before it starts.

select *
from {{ ref('seasons') }}
where season_start > season_end
