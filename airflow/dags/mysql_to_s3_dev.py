from datetime import timedelta

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

# table_config has no imports, so it is safe to load at DAG-parse time.
# (incremental_ingest is not: it reads env vars and imports pandas on import.)
from src.ingestion.table_config import TABLE_CONFIG

ENVIRONMENT = "dev"
S3_BUCKET = "cwo-dev-lake"

with DAG(
    dag_id="mysql_to_s3_dev",
    description="Ingest every table in TABLE_CONFIG from MySQL into the DEV S3 lake.",
    doc_md="""
    Daily extract of every table in `src/ingestion/table_config.py` to the
    DEV S3 bucket (`raw/mysql/<table>/ingestion_date=YYYY-MM-DD/`).

    - `incremental` tables load rows newer than their watermark; `full_snapshot`
      tables reload everything.
    - Each table is an independent task; one failure does not block the others.
    - Watermarks advance only after the S3 upload is validated, so retrying or
      clearing a failed task is safe. A retry after a failed validation can
      leave an extra Parquet file in the raw partition.
    - Adding a table to `TABLE_CONFIG` adds a task here automatically.
    """,
    start_date=pendulum.datetime(2026, 10, 1, tz="America/Chicago"),
    schedule="None",
    catchup=False,
    # Watermarks are per table; two runs at once could load the same rows twice.
    max_active_runs=1,
    # Cap concurrent MySQL connections from this DAG.
    max_active_tasks=3,
    dagrun_timeout=timedelta(hours=2),
    default_args={
        "owner": "data-engineering",
        "retries": 3,
        "retry_delay": timedelta(minutes=2),
        "retry_exponential_backoff": True,
        "max_retry_delay": timedelta(minutes=20),
        "execution_timeout": timedelta(minutes=30),
    },
    tags=["mysql", "s3", "ingestion", ENVIRONMENT],
) as dag:

    for table in TABLE_CONFIG:
        BashOperator(
            task_id=f"ingest_{table}",
            bash_command=f"python -m src.ingestion.incremental_ingest --table {table}",
            # Pin the target here so the DAG never depends on whatever
            # ENVIRONMENT/S3_BUCKET the container happens to have.
            env={
                "ENVIRONMENT": ENVIRONMENT,
                "S3_BUCKET": S3_BUCKET,
            },
            append_env=True,
        )
