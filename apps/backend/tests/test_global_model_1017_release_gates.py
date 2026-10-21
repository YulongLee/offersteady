"""Synthetic release guards; no provider, network, production data or writes."""
import importlib.util
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[3]
NOW = 2_000_000
SETTINGS = SimpleNamespace(product_edition='global', environment='production', database_url='synthetic')


def load(name):
    path = ROOT/'scripts/global_model_1017_release'/f'{name}.py'
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


OPTIMIZER = load('resume_optimizer_idle_gate')
FINANCIAL = load('global_financial_idle_gate')


class Database:
    """Run production aggregate SQL against synthetic in-memory rows.

    SQLite supports the aggregate FILTER and IS DISTINCT FROM expressions used
    here. Only placeholder spelling and PostgreSQL btrim need adaptation.
    """
    def __init__(self):
        self.connection = sqlite3.connect(':memory:')
        self.connection.create_function('btrim', 1, lambda value: value.strip())
        self.connection.executescript('''
          CREATE TABLE global_resume_optimizer_jobs (
            job_id TEXT, owner_user_id TEXT, quota_day TEXT, status TEXT,
            created_at_ms INTEGER, updated_at_ms INTEGER, deleted_at_ms INTEGER,
            lease_until_ms INTEGER, claim_token TEXT);
          CREATE TABLE global_resume_optimizer_usage (
            job_id TEXT, owner_user_id TEXT, quota_day TEXT, status TEXT,
            created_at_ms INTEGER, finalized_at_ms INTEGER);
          CREATE TABLE global_commerce_orders (status TEXT, created_at_ms INTEGER, updated_at_ms INTEGER);
          CREATE TABLE global_commerce_provider_events (status TEXT, received_at_ms INTEGER);
          CREATE TABLE global_commerce_usage_reservations (
            status TEXT, usage_kind TEXT, amount INTEGER, created_at_ms INTEGER,
            settled_at_ms INTEGER, released_at_ms INTEGER);
        ''')
        self.queries = []

    def insert(self, table, **values):
        self.connection.execute(f"INSERT INTO {table} ({','.join(values)}) VALUES ({','.join('?' for _ in values)})", tuple(values.values()))

    def connect(self, url, *, connect_timeout, options):
        assert url == 'synthetic' and connect_timeout == 3
        assert options == '-c default_transaction_read_only=on -c statement_timeout=3000'
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, sql, params):
        assert sql.lstrip().startswith('SELECT')
        assert not any(word in sql.upper().split() for word in ('UPDATE', 'INSERT', 'DELETE', 'ALTER', 'DROP'))
        self.queries.append((sql, params))
        return self.connection.execute(sql.replace('%s', '?'), params)

    def optimizer(self):
        return OPTIMIZER.collect_counts(SETTINGS, now_ms=NOW, connect=self.connect)

    def financial(self):
        return FINANCIAL.collect_counts(SETTINGS, now_ms=NOW, connect=self.connect)

    def job(self, **changes):
        values = dict(job_id='synthetic-job', owner_user_id='synthetic-owner', quota_day='2026-10-22',
                      status='completed', created_at_ms=1_000, updated_at_ms=2_000,
                      deleted_at_ms=None, lease_until_ms=None, claim_token=None)
        values.update(changes)
        self.insert('global_resume_optimizer_jobs', **values)

    def optimizer_usage(self, **changes):
        values = dict(job_id='synthetic-job', owner_user_id='synthetic-owner', quota_day='2026-10-22',
                      status='settled', created_at_ms=1_000, finalized_at_ms=2_000)
        values.update(changes)
        self.insert('global_resume_optimizer_usage', **values)

    def commerce_usage(self, **changes):
        values = dict(status='settled', usage_kind='screen_assist', amount=1,
                      created_at_ms=1_000, settled_at_ms=2_000, released_at_ms=None)
        values.update(changes)
        self.insert('global_commerce_usage_reservations', **values)


@pytest.mark.parametrize('module', [OPTIMIZER, FINANCIAL])
def test_empty_schema_is_idle_fixed_shape(module):
    db = Database()
    result = module.collect_counts(SETTINGS, now_ms=NOW, connect=db.connect)
    assert result == dict.fromkeys(module.PROTECTED, 0)
    assert not module.blocked(result)


@pytest.mark.parametrize('status', ['queued', 'running'])
@pytest.mark.parametrize('deleted', [None, 1_500])
def test_optimizer_active_status_is_protected_even_deleted(status, deleted):
    db = Database(); db.job(status=status, deleted_at_ms=deleted)
    result = db.optimizer()
    assert result['resumeOptimizerQueuedOrRunning'] == 1
    assert OPTIMIZER.blocked(result)


@pytest.mark.parametrize('status', ['completed', 'failed', 'cancelled'])
@pytest.mark.parametrize('lease', [NOW, NOW+1])
def test_optimizer_claim_is_independent_of_status_and_deletion(status, lease):
    db = Database(); db.job(status=status, deleted_at_ms=1_500, claim_token='synthetic-claim', lease_until_ms=lease)
    result = db.optimizer()
    assert result['resumeOptimizerEffectiveClaims'] == result['resumeOptimizerEffectiveLeases'] == 1
    assert OPTIMIZER.blocked(result)


def test_optimizer_lease_without_token_still_blocks_and_is_invalid():
    db = Database(); db.job(lease_until_ms=NOW+1)
    result = db.optimizer()
    assert result['resumeOptimizerEffectiveLeases'] == result['invalidResumeOptimizerMetadata'] == 1


@pytest.mark.parametrize('changes', [
    {'claim_token':'orphan'}, {'claim_token':'', 'lease_until_ms':NOW+1},
    {'claim_token':'  ', 'lease_until_ms':NOW+1},
    {'claim_token':'orphan', 'lease_until_ms':0},
    {'created_at_ms':0}, {'created_at_ms':None}, {'updated_at_ms':999},
    {'updated_at_ms':NOW+5_001}, {'status':'unknown'}, {'status':None},
])
def test_optimizer_malformed_metadata_and_unknown_state_fail_closed(changes):
    db = Database(); db.job(**changes)
    result = db.optimizer()
    assert OPTIMIZER.blocked(result)
    assert result['invalidResumeOptimizerMetadata'] + result['unknownResumeOptimizerStates'] > 0


def test_optimizer_old_reserved_quota_is_protected_with_terminal_deleted_job():
    db = Database(); db.job(deleted_at_ms=1_500); db.optimizer_usage(status='reserved', finalized_at_ms=None)
    result = db.optimizer()
    assert result['reservedResumeOptimizerUsage'] == 1
    assert OPTIMIZER.blocked(result)


@pytest.mark.parametrize('changes', [
    {'job_id':'absent'}, {'owner_user_id':'different'}, {'quota_day':'2026-10-21'},
    {'created_at_ms':0}, {'created_at_ms':NOW+5_001}, {'finalized_at_ms':None},
    {'finalized_at_ms':999}, {'finalized_at_ms':NOW+5_001},
    {'status':'reserved'}, {'status':'unknown'}, {'status':None},
])
def test_optimizer_quota_unknown_or_inconsistent_is_protected(changes):
    db = Database(); db.job(); db.optimizer_usage(**changes)
    result = db.optimizer()
    assert OPTIMIZER.blocked(result)


def test_optimizer_valid_terminal_history_is_idle():
    db = Database(); db.job(); db.optimizer_usage()
    assert not OPTIMIZER.blocked(db.optimizer())


@pytest.mark.parametrize('status', ['pending', 'checkout_created', 'confirming'])
@pytest.mark.parametrize('updated', [NOW-120_000, NOW])
def test_recent_checkout_is_protected(status, updated):
    db = Database(); db.insert('global_commerce_orders', status=status, created_at_ms=1_000, updated_at_ms=updated)
    assert db.financial()['recentCommerceCheckouts'] == 1


def test_old_pending_checkout_is_not_alone_execution_but_processing_event_is():
    db = Database(); db.insert('global_commerce_orders', status='pending', created_at_ms=1_000, updated_at_ms=2_000)
    assert not FINANCIAL.blocked(db.financial())
    db.insert('global_commerce_provider_events', status='processing', received_at_ms=1_000)
    assert db.financial()['processingProviderEvents'] == 1


@pytest.mark.parametrize('kind', ['copilot_minute', 'screen_assist', 'knowledge_token'])
def test_every_global_reserved_entitlement_protected_without_age_exemption(kind):
    db = Database(); db.commerce_usage(status='reserved', usage_kind=kind, settled_at_ms=None)
    result = db.financial()
    assert result['unfinishedCommerceUsageReservations'] == 1
    assert FINANCIAL.blocked(result)
    assert 'billing_usage_reservations' not in FINANCIAL.USAGE_SQL
    assert 'startedAt' not in FINANCIAL.USAGE_SQL


@pytest.mark.parametrize('changes', [
    {'status':'unknown'}, {'status':None}, {'usage_kind':'answer'}, {'usage_kind':None},
    {'created_at_ms':0}, {'created_at_ms':NOW+5_001}, {'amount':0}, {'amount':None},
    {'settled_at_ms':None}, {'settled_at_ms':999}, {'settled_at_ms':NOW+5_001},
    {'released_at_ms':2_000}, {'status':'reserved'}, {'status':'released'},
])
def test_global_usage_unknown_or_invalid_metadata_fails_closed(changes):
    db = Database(); db.commerce_usage(**changes)
    assert FINANCIAL.blocked(db.financial())


def test_valid_settled_and_released_global_history_is_idle():
    db = Database(); db.commerce_usage(); db.commerce_usage(status='released', settled_at_ms=None, released_at_ms=2_000)
    assert not FINANCIAL.blocked(db.financial())


@pytest.mark.parametrize('module,missing_table,field', [
    (OPTIMIZER,'global_resume_optimizer_jobs','resumeOptimizerReadFailures'),
    (OPTIMIZER,'global_resume_optimizer_usage','resumeOptimizerReadFailures'),
    (FINANCIAL,'global_commerce_orders','financialReadFailures'),
    (FINANCIAL,'global_commerce_provider_events','financialReadFailures'),
    (FINANCIAL,'global_commerce_usage_reservations','financialReadFailures'),
])
def test_required_schema_missing_is_unknown_not_idle(module, missing_table, field):
    db = Database(); db.connection.execute('DROP TABLE '+missing_table)
    result = module.collect_counts(SETTINGS, now_ms=NOW, connect=db.connect)
    assert result[field] == 1 and module.blocked(result)


@pytest.mark.parametrize('module,field', [(OPTIMIZER,'resumeOptimizerReadFailures'),(FINANCIAL,'financialReadFailures')])
@pytest.mark.parametrize('row', [None, (), (0,), (True,0,0), (-1,0,0), ('0',0,0)])
def test_aggregate_shape_fail_closed(module, field, row):
    class Bad(Database):
        def execute(self, *args):
            return SimpleNamespace(fetchone=lambda:row)
    result = module.collect_counts(SETTINGS, now_ms=NOW, connect=Bad().connect)
    assert result[field] == 1 and module.blocked(result)


@pytest.mark.parametrize('module,field', [(OPTIMIZER,'resumeOptimizerReadFailures'),(FINANCIAL,'financialReadFailures')])
@pytest.mark.parametrize('edition,environment,now', [('cn','production',NOW),('global','development',NOW),('global','production',0),('global','production',True)])
def test_wrong_context_or_time_never_queries(module, field, edition, environment, now):
    def forbidden(*args, **kwargs):
        raise AssertionError('query must not be reached')
    result = module.collect_counts(SimpleNamespace(product_edition=edition, environment=environment), now_ms=now, connect=forbidden)
    assert result[field] == 1 and module.blocked(result)


@pytest.mark.parametrize('module', [OPTIMIZER, FINANCIAL])
def test_blocked_contract_rejects_missing_extra_and_boolean_counts(module):
    assert module.blocked({})
    counts = dict.fromkeys(module.PROTECTED, 0); counts['extra']=0
    assert module.blocked(counts)
    counts = dict.fromkeys(module.PROTECTED, 0); counts[module.PROTECTED[0]]=False
    assert module.blocked(counts)
