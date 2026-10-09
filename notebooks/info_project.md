USAR CONTROL SHIP V PARA FORMAT EN VISUAL Y ES p PARA MAC
short command to format markdown in vscode

# Proyecto: Polen, calidad del aire y alergias en Suecia

## Cómo trabajar conmigo
Proyecto de portafolio para un perfil de **Data Analyst / Data Engineer**.
Quiero entender cada paso: explica el código y las decisiones, avanza por fases y confirma conmigo antes de cambios grandes. Se conciso y directo. Responde en ingles includo los codigos que se ponen en el notebook o dasboard a menos que te diga lo contrario.

## Resumen y business case
Pipeline automático de datos de polen, contaminación y clima en ciudades suecas, más un dashboard que responde cuándo y dónde el polen es más alto, y por qué.

- **Contexto:** alrededor de un tercio de la población sueca declara tener alergia al polen (encuestas de Astma- och Allergiförbundet/Sifo; informe CAMM, Región Estocolmo).
- **Cliente consumidor:** personas con alergia (y asma) que quieren planificar actividades al aire libre.
- **Clientes de negocio:**
  - **Farmacias:** reforzar el stock de antihistamínicos en el momento y la región correctos.
  - **Turismo:** recomendar destinos de primavera para personas con alergia.
  - **Eventos al aire libre:** elegir fechas con menos riesgo (polen, lluvia, mala calidad del aire).
  - **Hogar y retail:** cuándo y dónde vender purificadores de aire y filtros, y otros productos ligados al polen (ver *Retail y A/B tests*).
- **Tipo de análisis:** descriptivo y diagnóstico (explicar el pasado) + recomendaciones. Sin predicción en esta versión.

## Alcance del análisis
- **Todos los tipos de polen:** cada pregunta se responde para los **4 tipos** — aliso (alder), abedul (birch), gramíneas (grass) y artemisa (mugwort) — no solo para el abedul.
- **Granularidad: ciudad.** Cada resultado se da **por ciudad** (6 ciudades, un punto lat/lon por ciudad, celda del modelo CAMS de ~11 km). **No** a nivel de kommun ni distrito.
- **Regiones** (solo como agrupación de ciudades para resúmenes): **Sur** = Malmö + Göteborg · **Centro** = Estocolmo + Uppsala · **Norte** = Umeå + Luleå.
- **Periodo:** 2021-01-01 → ayer (~6 temporadas). Valores "típicos" = mediana 2021–2026.

## Preguntas a responder
Notebook: `notebooks/analysis.ipynb`. Columna "Estado": qué cubre ya el notebook con el alcance nuevo (4 tipos × ciudad).

**Personas con alergia**

| # | Pregunta | Estado en el notebook |
|---|---|---|
| 1 | ¿Cuándo empieza, alcanza su máximo y termina la temporada de **cada tipo de polen**, por ciudad? | ✅ 4 tipos × ciudad |
| 2 | ¿Cuántas semanas antes empieza la temporada de **cada tipo de polen** en el sur que en el norte, por ciudad? | ✅ 4 tipos × ciudad (semanas después de Malmö) + detalle del abedul por año y región |
| 3 | ¿A qué horas del día hay menos polen, **por tipo de polen y ciudad**? | ✅ 4 tipos × ciudad (más el promedio de las 6 ciudades) |
| 4 | ¿Cómo influyen la temperatura, la lluvia y el viento en **cada tipo de polen**, por ciudad? | ✅ Abedul, gramíneas y artemisa × ciudad (aliso excluido: datos débiles, casi cero fuera de Göteborg) |
| 5 | ¿Cuántos días tarda **cada tipo de polen** en volver a subir después de llover, por ciudad? | ✅ Abedul, gramíneas y artemisa × ciudad (aliso excluido: datos débiles; celdas con < 8 eventos marcadas como débiles) |
| 6 | ¿Qué días coinciden polen alto (**cualquier tipo**) y mala calidad del aire (PM2.5 = partículas finas < 2,5 µm, ozono), por ciudad? | ✅ 4 tipos × ciudad × año |
| 7 | ¿Qué año tuvo la temporada más intensa para **cada tipo de polen** y ciudad, y por qué? | ✅ 4 tipos × ciudad × año; "por qué" por tipo (verano anterior, primavera, tiempo durante la temporada) |
| – | **Calendario de riesgo para alérgicos:** ¿qué semanas son más seguras para actividades al aire libre, por ciudad? | ✅ 4 tipos juntos × ciudad × semana |

**Negocio**

| # | Pregunta | Estado en el notebook |
|---|---|---|
| 8 | Farmacias: ¿en qué semanas conviene reforzar el stock de antihistamínicos, por **tipo de polen** y ciudad/región? | ✅ 4 tipos × ciudad (aliso y artemisa con aviso de datos débiles) |
| 9 | Turismo: ¿qué destinos (ciudades) son mejores en primavera para personas con alergia? | ✅ 4 tipos juntos × ciudad × quincena |
| 10 | Eventos al aire libre (festivales, carreras): ¿qué fechas tienen menos riesgo, por ciudad? | ✅ 4 tipos por separado + lluvia + mala calidad del aire × ciudad × semana |
| 11 | Hogar y retail: ¿cuándo vender purificadores de aire o filtros, por ciudad? | ✅ Polen (4 tipos) y PM2.5 × ciudad × mes |
| 12 | Retail: ¿vende más una campaña de alergia que sigue al polen que una que sigue al calendario? (diseño de A/B test) | ✅ Diseño de geo-experiment + validación del disparador con datos de polen (sin datos de ventas) |

## Retail y A/B tests
El retail es donde más se hacen A/B tests en la vida real, y el polen afecta a muchas ventas más allá de las farmacias.

**Retailers que podrían usar los datos**
- **Supermercados y droguerías:** pañuelos, colirios, antihistamínicos sin receta, sprays nasales.
- **Electrónica y hogar** (tipo Elgiganten o Clas Ohlson): purificadores de aire y filtros.
- **E-commerce de salud y belleza:** productos para la alergia y cuidado de la piel.
- **Tiendas de deporte y ropa outdoor:** gafas de sol, mascarillas, ropa técnica. En semanas de mucho polen, la gente alérgica entrena más en interiores.

**Ideas de A/B test para retail**

| Test | Grupo A | Grupo B | Métrica principal |
|---|---|---|---|
| Email de alerta de polen | Newsletter normal | Email "llega la temporada de abedul" con productos para la alergia | Ventas de productos para la alergia por cliente |
| Banner en la web según el polen | Banner normal | Banner de alergia en días de polen alto en la ciudad del cliente | Tasa de conversión |
| **Momento de la campaña** | Campaña en la fecha fija de cada año | Campaña que empieza cuando el análisis detecta el inicio de temporada en la región | Ventas totales de la temporada |
| Ubicación en tienda | Productos en su pasillo habitual | Productos junto a la caja en semanas de polen alto | Ventas por tienda |

- **El test más interesante para el proyecto es "Momento de la campaña"**: conecta directamente el análisis (cuándo empieza la temporada en cada región, `marts.seasons`, Q2 y Q8) con una decisión de negocio: ¿vende más una campaña que sigue al polen que una que sigue al calendario?
- **Detalle de diseño:** en este test no se pueden asignar clientes al azar fácilmente, porque la temporada llega a toda una región a la vez. Lo habitual es repartir **regiones o tiendas** entre los dos grupos (**geo-experiment**). Mencionarlo en el diseño demuestra que se entienden los límites de los A/B tests.
- **Limitación:** el proyecto no tiene datos de ventas → se entrega el **diseño** del test (hipótesis, grupos, métrica, unidad de asignación, duración), no el resultado.

## Definiciones usadas en el análisis
| Concepto | Definición |
|---|---|
| **Temporada** (inicio / fin) | Método de suma acumulada: inicio = día en que se alcanza el **5 %** del polen del año, fin = **95 %**; pico = día con el promedio diario más alto (`marts.seasons`) |
| **Día de polen alto** | Promedio diario: abedul o aliso > 100, gramíneas o artemisa > 30 granos/m³ (escalas nórdicas habituales; supuesto a validar) |
| **Día de polen moderado o alto** | Cualquier tipo de polen > 10 granos/m³ (personas sensibles) |
| **Día de mala calidad del aire** | Guías OMS 2021: PM2.5 (partículas finas < 2,5 µm) promedio diario > 15 µg/m³ **o** ozono media 8 h > 100 µg/m³ |
| **Día de lluvia** | ≥ 1 mm en el día (Q10); ≥ 2 mm para eventos de lluvia en Q5 |
| **Comparación con tiempo** | Ratio = polen del día / **promedio** de la temporada de esa ciudad y año (1 = día promedio; se usa el promedio y no la mediana porque la mediana del aliso es ~0), para quitar el efecto "momento de la temporada" |

## Fuentes de datos
| Fuente | Datos | Frecuencia | Histórico | Acceso |
|---|---|---|---|---|
| Open-Meteo Air Quality API | Polen (alder, birch, grass, mugwort), PM2.5, PM10, ozono, NO2 | Por hora | **Polen confirmado:** abedul y gramíneas desde oct. 2020, aliso desde nov. 2020, artemisa desde jun. 2021. Hasta 2023 solo dentro de cada temporada (vacío fuera); desde 2024 todo el año. Contaminación: desde 2013 | Sin clave, uso no comercial, citar CAMS y Open-Meteo |
| Open-Meteo Historical Weather | Temperatura, humedad, lluvia, viento (velocidad y dirección) | Por hora | Desde 1940 (usado desde 2021) | Sin clave |
| SMHI Open Data | Observaciones oficiales de clima | Por hora | Largo | Sin clave (alternativa o validación; no usado aún) |
| Librería `holidays` | Festivos suecos | Diaria | Completo | Python (no usado aún) |
| Pollenrapporten (Naturhistoriska riksmuseet) | Mediciones reales y pronósticos locales | — | — | **NO hacer scraping** (robots.txt lo bloquea). Solo validación manual o datos pedidos al laboratorio |
| Astma- och Allergiförbundet/Sifo, CAMM | Prevalencia; temporadas de Estocolmo 1973–2024 | Informes | — | Solo contexto y validación. Usado: informe CAMM 2026 *Förändringar i pollensäsonger, klimat och folkhälsa* (Tabla B1, p. 30) |

- API calidad del aire: `https://air-quality-api.open-meteo.com/v1/air-quality` · API clima: `https://archive-api.open-meteo.com/v1/archive`
- Parámetros: `latitude`, `longitude`, `hourly`, `start_date`, `end_date`, `timezone=GMT` (la capa `raw` guarda **UTC**; `staging` convierte a Europe/Stockholm para evitar horas duplicadas en el cambio de hora)
- Resolución del modelo CAMS: ~11 km → trabajar a **nivel de ciudad**, no de distrito ni kommun.
- **Ciudades:** Malmö, Göteborg, Estocolmo, Uppsala, Umeå, Luleå (sur a norte).

## Arquitectura y stack (todo gratuito)
Fuentes → Ingesta Python (carga incremental, reintentos, log) → DuckDB `raw` → dbt (`staging`, `marts`, tests) → Notebooks de análisis + Dashboard **Dash (Plotly)**. GitHub Actions diario (pendiente).

| Capa (schema en `data/polen.duckdb`) | Tablas | Qué contiene |
|---|---|---|
| `raw` | `air_quality`, `weather`, `ingestion_log` | Datos tal como llegan (UTC) + log de cada ejecución |
| `staging` (vistas) | `stg_air_quality`, `stg_weather` | Hora sueca, polen vacío → 0, nombres con unidades |
| `marts` (tablas) | `hourly`, `daily`, `weekly`, `seasons`, `missing_values` | Ciudad × hora/día/semana con polen + contaminación + clima; temporadas; informe de faltantes |

Stack: Python (`requests`, `pandas`, `truststore`), DuckDB, dbt Core con `dbt-duckdb`, Altair (gráficos del notebook), **Dash + Plotly** (dashboard), GitHub Actions, GitHub. Entorno con **uv** (`pyproject.toml` + `uv.lock`).

## Plan por fases
Orden acordado: Fases 0–3 → **5 (análisis)** → **6a (dashboard)** → **4 (automatización) + 6b (publicar)** al final, porque requieren GitHub.

**Fase 0 – Validar los datos (hacer primero)**
- [x] Llamada de prueba: `birch_pollen` para mayo 2019 y mayo 2024 → polen desde oct. 2020 (artemisa desde jun. 2021); mayo 2019 sin polen
- [x] Comprobar que las 6 ciudades devuelven polen y contaminación
- [x] Definir el periodo del proyecto → 2021-01-01 hasta ayer (~6 temporadas)

**Fase 1 – Ingesta**
- [x] Script que descarga polen, contaminación y clima por ciudad y hora (`ingestion/ingest.py`, configuración en `ingestion/config.py`)
- [x] Guardar datos crudos tal como llegan (capa `raw`) en DuckDB (`data/polen.duckdb`, hora en UTC)
- [x] Carga incremental (solo días nuevos)
- [x] Reintentos si la API falla o limita peticiones
- [x] Log de cada ejecución (fecha, filas, errores) → `raw.ingestion_log` + `logs/ingest.log`
- [x] Empezar con UNA ciudad (Estocolmo) y luego ampliar a las 6
- Nota: hasta 2023 CAMS solo publica cada polen durante su temporada (nulos fuera de temporada); desde 2024, todo el año

**Fase 2 – Transformación y modelo (dbt)**
- [x] `staging`: tipos, zona horaria Europe/Stockholm, nombres de columnas (polen vacío → 0)
- [x] `marts`: tabla horaria unificada (ciudad × hora: polen, contaminación, clima) + tablas diarias y semanales
- [x] Tabla de temporadas: inicio, pico y fin por ciudad, año y tipo de polen (`marts.seasons`)
- [x] Documentar el umbral de "inicio de temporada" → método suma acumulada: inicio = 5 %, fin = 95 % del polen del año (`dbt/models/marts/_marts.yml`)

**Fase 3 – Calidad de datos**
- [x] Tests dbt: sin duplicados ciudad+hora, sin negativos, fechas completas (58 tests + freshness de `raw`)
- [x] Informe de valores faltantes por ciudad y variable (`marts.missing_values`)

**Fase 4 – Automatización** *(al final, junto con la publicación)*
- [ ] Decidir dónde vive la base de datos entre ejecuciones (GitHub Release, reconstruir cada día o MotherDuck)
- [ ] GitHub Actions que ejecuta el pipeline cada día (`ingest.py` → `dbt build` → `dbt source freshness`)
- [ ] Cualquier configuración sensible en secretos de GitHub, nunca en el código

**Fase 5 – Análisis** (`notebooks/analysis.ipynb`)
- [x] EDA: calendario de polen, distribución, correlaciones, clima por ciudad
- [x] Notebook con una sección por pregunta (1–11), separado en **Personas con alergia** y **Negocio**
- [x] Comparaciones: lluvia vs seco, viento alto vs bajo, temperatura
- [x] Calendario de riesgo para alérgicos por ciudad y semana
- [x] Ampliar Q2 y Q3 a **los 4 tipos de polen y a nivel de ciudad**
- [x] Ampliar Q4, Q5, Q7 y Q8 a **los 4 tipos de polen y a nivel de ciudad**
- [x] Contrastar fechas de Estocolmo con el informe CAMM (2026, Tabla B1: media 1973–2024 + tendencia, ajustada a 2023; misma definición 3 % / 97 %) → sección *Validation* en `analysis.ipynb`
- [ ] (Opcional) Contrastar manualmente con Pollenrapporten algún año concreto
- [x] 3–5 recomendaciones para consumidor y negocios (sección *Recommendations* al final de `analysis.ipynb`)
- [x] Diseño de A/B test para retail (Q12): "Momento de la campaña" como geo-experiment (regiones o tiendas como unidad), usando el inicio de temporada por región

**Fase 6 – Dashboard y presentación**
- [x] 6a. Dashboard **Dash (Plotly)** con las vistas de abajo, en local (`uv run python dashboard/app.py`): 8 pestañas, con etiquetas de grupo encima: **Customers** (solo Weather & air; Why this matters, Pollen calendar y Pollen now sin etiqueta) y **Business** (Pharmacies, Tourism, Events, Retail); ocultas en el móvil – Why this matters · Pollen calendar · Weather & air · Pharmacies · Tourism · Events · Retail (con el diseño del A/B test como última sección) · Pollen now (fotos, semáforo de alertas, gráficos según la fecha; última pestaña)
- [x] 6b. README: business case, arquitectura, resultados, limitaciones (escrito en local, en inglés; falta añadir capturas y subirlo)
- [ ] 6b. Publicar el dashboard Dash en un hosting gratuito (p. ej. Render). **Preparado en local:** foto de los marts en Parquet (`data_snapshot/`, ~5 MB, se sube a git; `dashboard/export_snapshot.py` la regenera); `data.py` lee el Parquet si no existe `polen.duckdb`; `server = app.server` + `gunicorn`; `requirements.txt` (exportado de `uv.lock`); `render.yaml` (Blueprint, plan gratis, Frankfurt). Probado sin DuckDB: mismos datos, todas las pestañas OK, ~186 MB de memoria. **Falta:** subir a GitHub (puede ser privado) y crear el servicio en Render


## Notebooks
| Notebook | Contenido |
|---|---|
| `notebooks/Polen_data_analysis.ipynb` | Construcción del pipeline (pasos 1–5): pruebas de la API, exploración de `raw`, perfil de datos, decisiones de limpieza, resultados de dbt y tests. Encuentra la base de datos desde cualquier carpeta (`DB_PATH` en la celda de setup) |
| `notebooks/analysis.ipynb` | Análisis (paso 7): EDA + preguntas 1–11 con gráficos y conclusiones. Se ejecuta completo con "Run All" (solo lee `marts`, abre y cierra la conexión en cada consulta) |
| `notebooks/steps.md` | Estado de cada paso (1–9) |

## Dashboard (Dash + Plotly)
Filtros comunes: **ciudad** y **tipo de polen** (los 4 tipos).

### Principio de diseño: máximo de gráficos, mínimo de texto
- **Cada mensaje se cuenta con un gráfico o un KPI**, no con párrafos. El texto largo se queda en los notebooks.
- **Texto permitido:** título de la página, título del gráfico (en negrita, que ya diga la conclusión, p. ej. *"Pollen is lowest in the early morning"*), un subtítulo de una línea, etiquetas de ejes/leyendas y tooltips.
- **Sin bloques de texto:** como mucho **una frase** por gráfico si hace falta explicar algo (p. ej. el aviso de datos débiles).
- **Números importantes como KPI grandes** (tarjetas) en vez de frases.
- **Detalles en el tooltip** (al pasar el ratón) en vez de en el texto.
- Fuentes y avisos (*"Pattern information, not medical advice"*) en una línea pequeña al pie.

### Título y frases (pitch) – candidatos
**Título sugerido del dashboard:** **Pollen Radar Sweden** (alternativas: *Swedish Pollen Calendar*, *PollenPulse Sweden*).

Frases candidatas (el texto va en inglés, como el dashboard). Decidir dónde encaja mejor cada una:

| # | Frase principal | Subtítulo | Dónde podría ir |
|---|---|---|---|
| 1 | **Know before you sneeze.** | 1 in 4 Swedes suffer from pollen every spring. See when and where it hits – city by city, hour by hour. | ✅ **Decidido:** titular de la pestaña **"Weather & air"** (no en la cabecera) |
| 2 | **Pollen doesn't follow the calendar. Now you can follow the pollen.** | Birch season starts ~3 weeks later in the north than in the south – and 16 days earlier than 50 years ago. | ✅ **Decidido:** titular de la pestaña **"Pollen calendar"** |
| 3 | **The right stock, in the right city, in the right week.** | Pollen seasons move every year. Plan with data, not with a fixed date. | ✅ **Decidido:** titular de la pestaña **"Pharmacies"** (8c) |
| 4 | **Breathe smarter.** | When, where and why pollen is high in Sweden. | ✅ **Decidido:** titular de la pestaña **"Tourism"** (también vale para README / post de LinkedIn) |

KPIs para acompañar la frase principal (datos oficiales):
- **1 in 4** – Swedes with pollen symptoms in spring and summer (1177)
- **~16 days** – earlier birch season than in the 1970s in Stockholm (CAMM 2026)
- **6 cities × 4 pollen types** – hourly, 2021 → today

- **Por qué Dash:** app web en Python con más control del diseño que Streamlit (layout, callbacks), muestra habilidades de Data Engineer / Analytics Engineer.
- **Alertas al móvil con ntfy** (`notify.py --channel ntfy` o `both`): app gratuita ntfy (o ntfy.sh/app en el navegador); **un solo canal para todas las ciudades**, `pollen-project-gab` (cada alerta dice su ciudad en el título; nombre cambiable con la variable NTFY_TOPIC); el proyecto solo hace un POST al canal y ntfy lo reparte a quien esté suscrito; sin cuentas ni datos personales; el canal es público (quien sepa el nombre puede leer/escribir), por eso un nombre poco obvio. Una alerta llega a todos los móviles suscritos al canal. Previsión = prioridad alta. "Ya enviado" se recuerda por canal en logs/alerts_sent.json. En Pollen now, bajo la barra de alertas, recuadro con una línea "📲 Alerts on your phone: ntfy app → subscribe to pollen-project-gab · web" y un **código QR** (librería qrcode, imagen SVG) del enlace https://ntfy.sh/pollen-project-gab, con el texto "Web version only": abre la versión web (los enlaces https no abren la app; el enlace ntfy:// que sí la abre solo funciona en Android, por eso se dejó la web). Debajo, botón **"📤 Send this alert to phones"** (solo en local, oculto en Render): envía a ntfy las alertas de la ciudad y fecha elegidas (temporada en ≤ 14 días o previsión; mismo mensaje que notify.py, siempre, como prueba/demo); gris si ese día no hay alerta. Una temporada ya en curso (barra roja sin alerta, p. ej. 13 may 2021) no se envía: se decidió avisar solo cuando la temporada está por venir. Para la presentación: elegir Stockholm + 2 abr 2026 → pulsar → suenan los móviles suscritos al canal pollen-project-gab. Pendiente: enlace en la notificación que abra el dashboard filtrado (necesita Render).
- **Botón "🔄 Update data"** (cabecera, solo en local): muestra en una línea "Latest data: {último día} · ✅ Dashboard up to date · Next update: {último día + 2} (new pollen data daily ~13:30)" – hora leída de los metadatos de Open-Meteo: CAMS Europe (polen) corre 1 vez al día a las 00 UTC y se publica ~11:30 UTC ≈ 13:30 en verano / 12:30 en invierno; el tiempo (ECMWF IFS) cada 6 h, ~6,5 h después (datos hasta ayer: botón "🔄 Update data" gris/desactivado) o "Latest data: … · ⚠️ Update needed (N days missing)" (botón activo); la hora de la última descarga va en el tooltip; al pulsarlo ejecuta ingest.py → dbt build → export_snapshot.py (`dashboard/update.py`, ~10 s), borra la caché y recarga la página (el layout es una función, así todas las pestañas leen los datos nuevos). Si un paso falla, dice cuál y deja los datos como estaban. En Render está oculto (no hay base de datos).
- **Diseño visual** (`dashboard/assets/style.css`): fondo gris cálido suave, tarjetas blancas con esquinas redondeadas y sombra ligera, cabecera como tarjeta (🌼 + título + estado de los datos + botón azul), pestañas con subrayado azul en vez de las cajas grises de Dash (todas del mismo ancho), KPIs con línea azul arriba, títulos de sección con barra azul, etiquetas de filtros en mayúsculas pequeñas. Los colores de los datos NO cambian: siguen la paleta validada (apta para daltonismo) de los notebooks.
- **Gráficos:** se rehacen en **Plotly** (Dash no usa Altair), con el mismo estilo (títulos en negrita, K/M, colores fijos).
- **Datos:** lee las tablas `marts` de DuckDB en modo solo lectura (o exportadas a Parquet para el despliegue).
- **Publicación:** Dash no tiene un hosting gratuito propio como Streamlit Cloud → se despliega en un servicio como Render (plan gratuito: la primera visita tarda unos segundos en arrancar). Requiere decidir dónde viven los datos (ver Fase 4).

| Vista | Filtros | Elementos | KPIs |
|---|---|---|---|
| **0. Portada: "Why this matters"** (primera pestaña) | Sin filtros | Título + frase principal (pitch); hechos oficiales como **gráficos** (barras 2007 vs 2023, temporadas más tempranas y largas); qué aporta el proyecto; fuentes en una línea | 1 in 4 Swedes with symptoms · 43 % of adults in Stockholm · ~16 days earlier birch season · ~13 billion SEK/year |
| *(Pestaña "Pollen now": fila de 4 tarjetas – aliso, abedul, gramíneas, artemisa – cada una con **planta entera + flores**, nombre en inglés y sueco (abajo) y **tipo** solo en inglés (arriba: Tree / Herb (grass) / Herb (weed)); todas siempre en sus colores originales; los tipos en temporada o con alerta para la ciudad y fecha elegidas llevan borde azul. Fotos de Wikimedia Commons en `dashboard/assets/img/` (`*_plant.jpg`, `*_flower.jpg`): todas CC0 (AnRo0002) salvo las flores del abedul, CC BY-SA 3.0 (DimiTalen); créditos en el pie)* | | | |
| Consumidor: **"Pollen now"** (última pestaña) | Ciudad, **Date** (vacío = hoy) | De arriba abajo: fotos · filtros · título **"🔔 Pollen alert per date – {ciudad}, {fecha} (today / past date / future date)"** · **barra de alertas** · título de los gráficos según la fuente · gráfico de la **semana** alrededor de la fecha (2 días antes → 4 después, día elegido marcado) y gráfico del **día** hora a hora.<br>**Barra de alertas** (`alerts.py`, misma lógica que la notificación de Windows `notify.py`), como **semáforo**: 🟢 sin temporada ahora ni en 14 días (dice la próxima) · 🟡 una temporada empieza en ≤ 14 días (inicio típico; 1177: empezar el tratamiento 1–2 semanas antes) · 🔴 dentro de una temporada típica (inicio–fin mediano) o previsión ≥ 10 granos/m³ durante 3 horas seguidas (persistencia, como `alert_logic.py` del caso pádel); gana el más grave. Barra compacta (la ciudad y la fecha ya están en el título de encima; la frescura de los datos, en la cabecera): una línea de estado + una línea corta por alerta (p. ej. "🌳 Birch in about 2 weeks · usually 16 Apr (between 3 and 27 Apr in 2021–2026)" – "usually" = mediana de los inicios reales, "between" = el más temprano y el más tardío de los años con datos; las notificaciones del móvil/Windows mantienen la frase completa). Fechas pasadas: sin línea extra (se quitó "📊 Real data…" para que la barra sea más simple). Fechas futuras: "📅 Typical season dates 2021–2026, not a forecast".<br>**Gráficos según la fecha** (`data.pollen_for_date`): **hoy** = en directo de la API (únicos títulos con "Live": "📡 Live pollen information for today", "Live this week", "Live today"; previsión en gris y línea "now") · **fecha pasada en la base de datos** = `marts.hourly` ("📊 … – historical data") · **pasado reciente aún no ingerido** = API ("📊 … – recent data") · **próximos días** = previsión de la API ("🔮 Pollen forecast for …") · **más adelante** = valores típicos, media de las mismas fechas en los años con datos ("📅 Typical pollen for … – average of the same dates 2021–2026, not a forecast"). Eje Y de al menos 0–15 con línea punteada en **10 = "symptoms start"**. Se actualiza solo cada hora (`dcc.Interval`) | Semáforo; hora de la última actualización |
| Consumidor: **"Pollen calendar"** (2.ª pestaña) | Ciudad (**All cities** por defecto, o una ciudad), tipo de polen. Con una ciudad, todo muestra **solo esa ciudad**; con All cities, las 6 (KPIs = mediana/promedio de las 6) | Frase "Pollen doesn't follow the calendar. Now you can follow the pollen."; filtros arriba; **línea temporal del polen** (todas las ciudades: rango sur→norte; una ciudad: su temporada típica); calendario semanal, temporada y calendario de riesgo con una fila por ciudad (All cities) o **una fila por año 2021–2026** (una ciudad: así las celdas no quedan largas y finas y se comparan los años) (feb–ago, los 4 tipos, claro = temporada en alguna ciudad, oscuro = pico); KPIs; calendario semanal por nivel; temporada por ciudad; gráfico por hora del día; calendario de riesgo | Inicio y pico típicos; mejor hora; nº días de polen alto por año |
| Negocio: farmacias | Ciudad (incluye **All cities**, por defecto), tipo de polen. Con una ciudad elegida, las demás filas/barras se ven en color claro; con All cities todas en color completo | Inicio de temporada por ciudad; comparación entre años; semana para tener stock listo | Semana de inicio por ciudad; diferencia sur–norte en semanas; intensidad vs año anterior |
| Negocio: A/B test retail (Q12) – sección final de la pestaña "Retail" (ya no es pestaña propia) | Sin filtros | Título "Next step – A/B tests retailers can run with pollen data" + tabla de 4 ideas de test (test · grupo A · grupo B · métrica principal · unidad · análisis): email de alerta de polen, banner web según el polen, momento de la campaña, ubicación en tienda (misma tabla que *Ideas de A/B test para retail*) | Sin KPIs ni gráficos (se quitaron: error del disparador vs fecha fija y tiendas por grupo; el cálculo sigue en `analysis.ipynb`) |
| Negocio: turismo (Q9) – pestaña "Tourism" | Ciudad (resaltar) | Heatmap ciudad × quincena con % de días de polen alto (4 tipos juntos); barras de primavera por ciudad | Mejor destino en Apr 1–15, May 16–end y Jun 1–15 |
| Negocio: eventos al aire libre (Q10) – pestaña "Events" | Ciudad (resaltar) | Heatmap ciudad × semana con % de días problemáticos (polen > 10 granos/m³, lluvia ≥ 1 mm o mala calidad del aire); líneas por factor (polen, lluvia, aire) | Mejor semana (mayo–agosto); % de días problemáticos esa semana; peor semana |
| Negocio: retail (Q11) – pestaña "Retail" | Ciudad (resaltar) | Heatmap ciudad × mes de días de polen alto (productos de alergia); heatmap ciudad × mes de días con PM2.5 alto (filtros/purificadores) | Mes pico para productos de polen; mes pico para filtros de partículas; ciudad con más días de PM2.5 alto |

### Pestaña 0 – "Why this matters" (contenido)
Primera pestaña del dashboard: explica **por qué** se hace este análisis antes de mostrar datos. Mismos hechos que la portada de `notebooks/Polen_data_analysis.ipynb` (todos de fuentes oficiales):

| Hecho | Número | Fuente oficial |
|---|---|---|
| Cuántos la tienen | ~**1 de cada 4** personas en Suecia tiene síntomas de polen en primavera/verano; hasta **30 %** es alérgico | 1177; CAMM 2026 p. 24 |
| Región de Estocolmo | **43 %** de los adultos (2023) vs **30 %** (2007); mujeres 45 %, hombres 41 % | Miljöhälsoenkäten 2023 (Folkhälsomyndigheten), en CAMM Miljöhälsorapport 2025, cap. 12 |
| La alergia más común | "La alergia al polen es la más común y la que más ha aumentado" | CAMM Miljöhälsorapport 2025, cap. 12 |
| Temporadas más tempranas y largas | Abedul **~16 días antes** que en los años 70; gramíneas +19 y artemisa +40 días más largas | CAMM 2026 p. 17 y Tabla B1 |
| Más días de riesgo | **~10 días más** por temporada con abedul alto (2019–2024 vs 1973–1977) | CAMM 2026 p. 18 |
| Carga sanitaria | Visitas ambulatorias por vías respiratorias: **~267/día** sin polen de abedul → **~390/día** con polen alto; **~530–540 visitas extra** por temporada | CAMM 2026 p. 18 |
| Coste para la sociedad | **~13.000 millones SEK/año** (estimación 2016), sobre todo indirecto (bajas, productividad) | CAMM 2026 p. 13 (Cardell et al. 2016) |
| Larga duración | **~75 %** de los niños con rinitis por polen siguen con síntomas de adultos; **~1 de cada 3** desarrolla asma | CAMM 2026 p. 26 (cohorte BAMSE) |
| El momento importa | El tratamiento funciona mejor si se empieza **1–2 semanas antes** de la temporada | 1177 |

Diseño sugerido de la pestaña (siguiendo el principio "máximo de gráficos, mínimo de texto"):
1. **Título** "Pollen Radar Sweden" en la cabecera (la frase "Know before you sneeze." va en la pestaña "Weather & air").
2. **Fila de 4 KPIs grandes:** 1 in 4 · 43 % · ~16 days · ~13 bn SEK.
3. **Hechos como gráficos** en lugar de tabla de texto (2 gráficos, lado a lado):
   - **Barras 2007 vs 2023:** % de adultos con alergia al polen en Estocolmo (30 % → 43 %).
   - **Barras horizontales:** inicio del abedul ~16 días antes que en los años 70; temporadas más largas (gramíneas +19, artemisa +40 días).
   - *(Descartados para no repetir ni recargar: mujeres vs hombres, visitas al médico por nivel de polen y el gráfico de cuadrados "1 in 4", que ya está en los KPI.)*
   - *(La línea temporal del polen se movió al principio de la pestaña "Pollen calendar".)* **Línea temporal del polen**: una barra por tipo de polen sobre el año entero (ene–dic); claro = temporada en alguna ciudad (inicio más temprano en el sur → fin más tardío en el norte), oscuro = semanas de pico. Aliso 20 feb – 21 may · abedul 14 abr – 7 jun · gramíneas 1 jun – 10 ago · artemisa 9 jul – 18 ago (fechas típicas 2021–2026 de `typical_seasons`)
4. **"What this dashboard adds"** como 3 iconos o mini-KPIs: 6 ciudades · cada hora · 4 tipos de polen + clima + aire.
5. **Fuentes** en una línea pequeña al pie (CAMM 2026, CAMM Miljöhälsorapport 2025 / Folkhälsomyndigheten, 1177) + *"Pattern information, not medical advice."*

## Estilo de gráficos
- Títulos en **negrita**
- Etiquetas de datos divididas entre 1000 con sufijo **K** o **M** (no separadores de miles)
- Siglas explicadas entre paréntesis la primera vez: p. ej. **PM2.5 (partículas finas < 2,5 µm)**, **NO2 (dióxido de nitrógeno)**
- Mismo color fijo por ciudad, región y tipo de polen en todos los gráficos; nunca dos ejes Y en un mismo gráfico

## Estructura del repositorio
```
Polen_history/
├── ingestion/          # config.py (ciudades, variables, fechas) + ingest.py (descarga → DuckDB)
├── dbt/                # models/staging, models/marts, tests, macros, profiles.yml
├── data/               # DuckDB local: polen.duckdb (en .gitignore)
├── logs/               # log de la ingesta (en .gitignore)
├── notebooks/          # Polen_data_analysis.ipynb, analysis.ipynb, steps.md, info_project.md
├── dashboard/          # app.py (layout, pestañas, callbacks), charts.py (gráficos), data.py (consultas + API en directo),
│                       # alerts.py (reglas de alerta), notify.py (notificación de Windows + push al móvil con ntfy), update.py (botón Update data),
│                       # export_snapshot.py (marts → Parquet), assets/ (CSS, fotos)
├── tests/              # pytest: test_live_api.py (API simulada), test_alerts.py (alertas y Pollen now), test_calendar.py (filtro de ciudad), test_update.py (botón), test_notify.py (ntfy) – 36 tests
├── data_snapshot/      # copia Parquet de los marts (~5 MB, sí va a git) para el dashboard publicado
├── pics/               # capturas del dashboard para el README
├── .github/workflows/  # ejecución diaria (pendiente)
├── README.md
├── render.yaml         # despliegue en Render (plan gratis, gunicorn)
├── requirements.txt    # exportado de uv.lock para Render (`uv export`)
├── pyproject.toml      # dependencias (uv)
└── uv.lock
```

## Notas y conclusiones

### Validación con CAMM (explicado simple)
- **CAMS (nuestros datos)** es como un **pronóstico del tiempo**: un modelo que *estima* cuánto polen debería haber, para todo el país.
- **CAMM** es como un **termómetro en la pared**: en el Museo de Historia Natural de Estocolmo se atrapa y cuenta polen con microscopio **cada día desde 1973**. Es la **medición real**.
- La validación pregunta: **¿coincide nuestro pronóstico con la medición real?**
- **¿Por qué no año por año?** El informe CAMM **no publica las fechas de cada año**, solo el **promedio de 50 años** y la **tendencia por año** (p. ej. el abedul empieza ~0,31 días antes cada año). El valor de 2023 es una **estimación**: promedio + tendencia × años. Para comparar año por año harían falta los datos diarios de Pollenrapporten (solo gráficos, sin scraping) o pedirlos al laboratorio.
- **No se reemplazó nada.** El 3 % / 97 % se usa **solo en la comparación** (para medir igual que CAMM); Q1–Q12 siguen con 5 % / 95 %. CAMM no sustituye nuestros datos: es el **árbitro** que dice cuánto confiar en cada parte:
  - ✅ **Fechas** de abedul y gramíneas → fiables (±1 semana), las conclusiones se mantienen.
  - ⚠️ **Cantidades** → el modelo tiene menos polen que la realidad (abedul ~0,5×, gramíneas ~0,4×) → el riesgo real probablemente es **mayor**; gramíneas y artemisa terminan 2–4 semanas antes en el modelo.
  - ❌ **Aliso** → no fiable (~3 % de la cantidad medida).

### Conclusiones principales del análisis
- **Temporadas:** aliso (feb–abr) → abedul (mediados abr–may) → gramíneas (jun–ago) → artemisa (mediados jul–ago).
- **Sur vs norte:** el abedul empieza ~3–3,5 semanas más tarde en el norte (Umeå, Luleå); gramíneas ~2–2,5 semanas; artemisa igual en todas partes.
- **Hora del día:** el polen es mínimo entre las **05:00 y 08:00** en todas las ciudades y tipos.
- **Tiempo:** la lluvia reduce el polen ~a la mitad; los días cálidos lo aumentan (efecto más fuerte); el viento tiene un efecto menor y mixto. Tras un día de lluvia, el polen vuelve en ~1,5–2 días.
- **Polen + mala calidad del aire:** 62 días en 6 años, casi siempre por **ozono**, sobre todo en **mayo**.
- **Negocio:** stock de antihistamínicos listo en semana 13–14 (sur/centro) y 16 (norte) para el abedul; campañas de retail que siguen al polen en vez del calendario (A/B test como geo-experiment); turismo "primavera sin polen" por dirección; eventos mejor a finales de agosto.

## Limitaciones a explicar
- Histórico de polen corto: **~6 temporadas (2021–2026)** → suficiente para patrones por hora, clima y ciudad; poco para explicar diferencias entre años (Q7). Usar CAMM como referencia histórica
- El polen de CAMS es **estimación de modelo, no medición**: el aliso se concentra en Göteborg y la artemisa tiene las mismas fechas en todas las ciudades (probables simplificaciones del modelo)
- **Validación con CAMM (Estocolmo):** las fechas de abedul y gramíneas coinciden en ~1 semana (fiables); las cantidades del modelo son menores (abedul ~0,5×, gramíneas ~0,4×) → los días de "polen alto" están **subestimados**; gramíneas y artemisa terminan 2–4 semanas antes en el modelo; el aliso tiene solo ~3 % de la cantidad medida (no fiable)
- Hasta 2023 el polen fuera de temporada viene vacío → se rellena con 0 en `staging`
- Granularidad de **ciudad** (celda de ~11 km): no representa barrios ni kommuner
- Umbrales de "polen alto" = supuesto basado en escalas nórdicas habituales; validar con Pollenrapporten
- Prevalencia de alergia = encuestas autodeclaradas
- Open-Meteo: gratis solo para uso no comercial; citar CAMS y Open-Meteo
- Información sobre patrones, no consejo médico ("para tratamientos, consulta a tu médico")
