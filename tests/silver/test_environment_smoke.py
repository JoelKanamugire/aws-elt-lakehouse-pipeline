"""Prove the local Glue container can do what Silver needs."""

from datetime import datetime

TABLE = "glue_catalog.cwo_local_silver.orders_smoke"

def test_spark_matches_glue_and_runs_in_utc(spark):
    assert spark.version.startswith("3.5")
    assert spark.conf.get("spark.sql.session.timeZone") == "UTC"

def test_iceberg_create_and_read_back(spark):
    spark.sql("CREATE NAMESPACE IF NOT EXISTS glue_catalog.cwo_local_silver")
    spark.sql(f"DROP TABLE IF EXISTS {TABLE}")
    spark.sql(f"""
              CREATE TABLE {TABLE} (
                  order_id BIGINT, status STRING,
                  order_date TIMESTAMP, updated_at TIMESTAMP
              )  USING iceberg
              PARTITIONED BY (months(order_date))
              TBLPROPERTIES ('format-version'='2', 'write.merge.mode'='copy-on-write')           
    """)
    ts = datetime(2026, 10, 1, 10, 0, 0)
    spark.createDataFrame(
        [(1, "pending", ts, ts)],
        "order_id BIGINT, status STRING, order_date TIMESTAMP, updated_at TIMESTAMP",
    ).writeTo(TABLE).append()

    rows = spark.table(TABLE).collect()
    assert len(rows) == 1 and rows[0].status == "pending"