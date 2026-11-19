"""SparkSession that behaves the same locally and in Glue.

The Iceberg catalog is named ``glue_catalog`` everywhere (plan convention).
Locally it is a Hadoop catalog on a folder; in Glue it is the Glue Data
Catalog. So SQL like ``MERGE INTO glue_catalog.cwo_dev_silver.orders``
runs unchanged in tests, in the container, and in DEV/PROD.
"""
from __future__ import annotations

import os

from pyspark.sql import SparkSession

CATALOG = "glue_catalog"
ICEBERG_EXTENSIONS = (
    "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"
)


def iceberg_conf(runtime: str, warehouse: str) -> dict[str, str]:
    """Iceberg settings for the ``glue_catalog`` catalog."""
    conf = {
        "spark.sql.extensions": ICEBERG_EXTENSIONS,
        f"spark.sql.catalog.{CATALOG}": "org.apache.iceberg.spark.SparkCatalog",
        f"spark.sql.catalog.{CATALOG}.warehouse": warehouse,
        "spark.sql.session.timeZone": "UTC",
    }
    if runtime == "local":
        conf[f"spark.sql.catalog.{CATALOG}.type"] = "hadoop"
    elif runtime == "glue":
        conf[f"spark.sql.catalog.{CATALOG}.catalog-impl"] = (
            "org.apache.iceberg.aws.glue.GlueCatalog"
        )
        conf[f"spark.sql.catalog.{CATALOG}.io-impl"] = (
            "org.apache.iceberg.aws.s3.S3FileIO"
        )
    else:
        raise ValueError(f"Unknown runtime {runtime!r}; use 'local' or 'glue'")
    return conf

def build_spark(runtime: str | None = None, warehouse: str | None = None) -> SparkSession:
    """Return a SparkSession wired for Iceberg."""
    runtime = runtime or os.environ.get("SILVER_RUNTIME", "glue")

    if runtime == "glue":
        # In Glue, Iceberg settings come from the job's --conf (Terraform).
        spark = SparkSession.builder.getOrCreate()
        if spark.conf.get(f"spark.sql.catalog.{CATALOG}", None) is None:
            raise RuntimeError(
                "Glue job is missing the glue_catalog Iceberg settings; "
                "set them in the job's --conf default argument."
            )
        return spark
    
    warehouse = warehouse or "/tmp/cwo_iceberg_warehouse"
    builder = (
        SparkSession.builder.appName("cwo-silver-local")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.memory", "2g")
    )
    for key, value in iceberg_conf("local", warehouse).items():
        builder = builder.config(key, value)
    return builder.getOrCreate()