"""Fixtures for Silver tests. Skipped when PySpark isn't installed,
so ci.yml (plain Python, no Spark) keeps passing."""

import pytest

pytest.importorskip("pyspark")

from silver.spark_session import build_spark  # noqa: E402


@pytest.fixture(scope="session")
def spark(tmp_path_factory):
    warehouse = tmp_path_factory.mktemp("iceberg_warehouse")
    session = build_spark(runtime="local", warehouse=f"file://{warehouse}")
    yield session
    session.stop()