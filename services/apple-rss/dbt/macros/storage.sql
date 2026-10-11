{# Storage location of a dataset, e.g. uri('bronze') -> $APPLE_RSS_BRONZE_URI #}
{% macro uri(name) -%}
    {{ return(env_var('APPLE_RSS_' ~ name | upper ~ '_URI').rstrip('/')) }}
{%- endmacro %}

{# on-run-start hook: DuckDB credentials for GCS. Local paths need nothing. #}
{% macro storage_setup() -%}
    {% if uri('bronze').startswith('gs://') %}
        INSTALL httpfs; LOAD httpfs;
        CREATE OR REPLACE SECRET gcs (
            TYPE GCS,
            KEY_ID '{{ env_var("APPLE_RSS_GCS_HMAC_KEY_ID") }}',
            SECRET '{{ env_var("APPLE_RSS_GCS_HMAC_SECRET") }}'
        );
    {% else %}
        SELECT 1;
    {% endif %}
{%- endmacro %}
