"""Destination and reporting safety checks; no database or optional pool required."""
import importlib.util
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location("connection_pool_eval", Path(__file__).with_name("connection_pool_eval.py"))
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

VALID = "postgresql://synthetic_state:synthetic-test-only@127.0.0.1:58642/synthetic_state"


@pytest.fixture(autouse=True)
def explicit_database_environment(monkeypatch):
    for key in MODULE.FORBIDDEN_DATABASE_ENVIRONMENT:
        monkeypatch.delenv(key, raising=False)


def test_explicit_dedicated_loopback_target_is_allowed():
    assert MODULE.validate_local_dsn(VALID) == VALID


@pytest.mark.parametrize("dsn", [
    "",
    VALID.replace("127.0.0.1", "example.com"),
    VALID.replace("127.0.0.1", "localhost.example.com"),
    VALID.replace("127.0.0.1", "127.0.0.1,example.com"),
    VALID.replace("58642", "5432"),
    VALID.replace("/synthetic_state", "/postgres"),
    VALID.replace("synthetic_state:", "postgres:"),
    VALID + "?hostaddr=127.0.0.1",
    VALID + "?hostaddr=203.0.113.9",
    VALID + "?service=external-service",
    VALID + "?passfile=/tmp/test-password-file",
    "dbname=synthetic_state user=synthetic_state port=58642",
])
def test_non_dedicated_or_indirect_targets_are_rejected_without_echoing_dsn(dsn):
    with pytest.raises(ValueError) as error:
        MODULE.validate_local_dsn(dsn)
    assert "synthetic-test-only" not in str(error.value)
    assert "postgresql://" not in str(error.value)


def test_nearest_rank_percentile_matches_metric_definition():
    assert MODULE.percentile(list(range(1, 101)), .95) == 95
    assert MODULE.percentile([2], .95) == 2


@pytest.mark.parametrize("key", [
    "PGHOST", "PGHOSTADDR", "PGPORT", "PGDATABASE", "PGUSER",
    "PGSERVICE", "PGSERVICEFILE", "PGSYSCONFDIR", "PGPASSFILE",
    "PGTARGETSESSIONATTRS", "PGLOADBALANCEHOSTS",
])
@pytest.mark.parametrize("value", ["synthetic-indirect-value", ""])
def test_indirect_database_environment_is_rejected_without_echoing_value(monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError, match="indirect_database_environment_forbidden") as error:
        MODULE.validate_local_dsn(VALID)
    assert "synthetic-indirect-value" not in str(error.value)


def test_counter_is_returned_when_borrower_raises():
    counter = MODULE.WorkCounter()
    with pytest.raises(RuntimeError):
        with counter.borrowing():
            raise RuntimeError("synthetic")
    assert counter.borrowed == 0
    assert counter.peak_borrowed == 1
