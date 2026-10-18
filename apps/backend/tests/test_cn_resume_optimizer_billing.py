"""Actual CN wallet, PostgreSQL concurrency, and terminal accounting regressions."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
import pytest
import psycopg

from app.core.config import REPO_ROOT
from app.core.errors import DomainRequestError
from app.services.cn_resume_optimizer_repository import CNResumeOptimizerRepository,quota_day,reset_at
from app.services.cn_resume_optimizer_diagnostics import failure_diagnostic
from app.services.postgres_migrations import apply_sql_migrations
from cn_resume_optimizer_test_support import harness,ensure_synthetic_database,member,creation,complete,seed_document,NOW


def assert_error(code,call):
    with pytest.raises(DomainRequestError) as exc:call()
    assert exc.value.error_code=='resume_optimizer_'+code


def ledger(h):
    return [r for r in h.billing.state_for_user(user_id='owner').ledger if r.kind.startswith('resume_optimizer_')]


@pytest.mark.parametrize('days',[1,7,30])
def test_all_time_members_first_three_free_fourth_100_and_other_daily_quota_independent(harness,days):
    h=harness;member(h,days=days)
    before=h.mock.quote('owner',NOW)
    assert before['dailyFreeRemaining']==1
    cap=h.service.capabilities('owner')
    assert cap['activeTimeMember'] and cap['entryPoints']==0 and cap['dailyRemaining']==3
    assert cap['dailyLimit']==3
    assert cap['timezone']=='Asia/Shanghai' and cap['memberRequired'] is False and cap['canStart']
    for index in range(3):
        job=complete(h,h.service.create('owner',creation(h,key=f'free-{index}')))
        assert job['billingClass']=='daily_pass_free' and job['pointsCharged']==0 and job['billingStatus']=='settled'
        assert h.service.capabilities('owner')['dailyRemaining']==2-index
        assert h.billing.state_for_user(user_id='owner').balance==200 and not ledger(h)
    cap=h.service.capabilities('owner')
    assert cap['exhausted'] and cap['entryPoints']==100 and cap['dailyRemaining']==0
    paid=complete(h,h.service.create('owner',creation(h,key='paid')))
    assert paid['pointsCharged']==100 and h.billing.state_for_user(user_id='owner').balance==100
    assert h.mock.quote('owner',NOW)['dailyFreeRemaining']==1
    assert len(ledger(h))==1


def test_concurrent_last_free_slot_single_admission_and_exactly_once_release(harness):
    h=harness;member(h)
    for index in range(2):
        complete(h,h.service.create('owner',creation(h,key=f'completed-free-{index}')))
    assert h.service.capabilities('owner')['dailyRemaining']==1
    requests=[creation(h,key=f'last-free-{index}') for index in range(2)]
    gate=Barrier(2)
    def create(request):
        gate.wait()
        try:return ('accepted',(h.service.create('owner',request),request))
        except DomainRequestError as error:return ('rejected',error.error_code)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(create,requests))
    accepted=[value for status,value in results if status=='accepted']
    rejected=[value for status,value in results if status=='rejected']
    assert len(accepted)==1 and rejected==['resume_optimizer_quote_changed']
    job,original_request=accepted[0]
    assert job['billingClass']=='daily_pass_free' and job['pointsCharged']==0
    assert h.service.capabilities('owner')['dailyRemaining']==0
    assert h.service.create('owner',original_request)['jobId']==job['jobId']
    assert h.service.capabilities('owner')['dailyRemaining']==0
    h.service.cancel('owner',job['jobId']);h.service.cancel('owner',job['jobId'])
    assert h.service.capabilities('owner')['dailyRemaining']==1
    complete(h,h.service.create('owner',creation(h,key='replacement-free')))
    cap=h.service.capabilities('owner')
    assert cap['dailyRemaining']==0 and cap['entryPoints']==100 and cap['exhausted']
    assert h.billing.state_for_user(user_id='owner').balance==200 and not ledger(h)
    assert h.mock.quote('owner',NOW)['dailyFreeRemaining']==1


@pytest.mark.parametrize('terminal',['failure','queue_expiry','lease_expiry'])
def test_unfinished_last_free_slot_failure_and_recovery_release_original_day_once(harness,terminal):
    h=harness;member(h)
    for index in range(2):
        complete(h,h.service.create('owner',creation(h,key=f'completed-free-{index}')))
    job=h.service.create('owner',creation(h,key='last-free'))
    assert h.service.capabilities('owner')['dailyRemaining']==0
    claim=h.repo.claim(now_ms=NOW) if terminal!='queue_expiry' else None
    if terminal=='failure':
        h.repo.finish(user_id='owner',job_id=job['jobId'],token=claim['claim_token'],revision=claim['revision'],now_ms=NOW+1,error='invalid_output')
    else:
        h.repo.reap(now_ms=NOW+(h.repo.queue_lifetime_ms+1 if terminal=='queue_expiry' else h.repo.lease_ms+1))
    h.repo.reap(now_ms=NOW+2*h.repo.queue_lifetime_ms)
    h.service.cancel('owner',job['jobId'])
    assert h.service.capabilities('owner')['dailyRemaining']==1
    assert h.billing.state_for_user(user_id='owner').balance==200 and not ledger(h)


@pytest.mark.parametrize('starts,ends,active',[ (NOW,NOW+1,True),(NOW+1,NOW+2,False),(NOW-2,NOW,False)])
def test_admin_time_membership_exact_bounds(harness,starts,ends,active):
    h=harness;member(h,admin=True,starts=starts,ends=ends)
    assert h.service.capabilities('owner')['activeTimeMember'] is active
    assert h.service.capabilities('owner')['entryPoints']==(0 if active else 100)


def test_nonmember_point_charge_success_no_second_debit_and_visible_old_wallet_payload(harness):
    h=harness
    assert h.service.capabilities('owner')['entryPoints']==100
    job=h.service.create('owner',creation(h))
    assert job['pointsCharged']==100 and job['billingStatus']=='reserved'
    assert h.service.capabilities('owner')['availablePoints']==100
    assert h.billing.state_for_user(user_id='owner').balance==100
    done=complete(h,job)
    assert done['billingStatus']=='settled' and h.billing.state_for_user(user_id='owner').balance==100
    payload=h.billing.state_payload(h.billing.state_for_user(user_id='owner'))
    charges=[r for r in payload['ledger'] if r['kind']=='resume_optimizer_charge']
    assert len(charges)==1 and charges[0]['points']==-100 and charges[0]['description']=='简历优化扣费'
    h.service.cancel('owner',job['jobId']);h.service.delete('owner',job['jobId'])
    assert len(ledger(h))==1 and h.billing.state_for_user(user_id='owner').balance==100


@pytest.mark.parametrize('terminal',['cancel','delete','source','failure','queue_expiry','lease_expiry'])
def test_unfinished_paid_release_exactly_once_and_late_result_never_recharges(harness,terminal):
    h=harness;job=h.service.create('owner',creation(h))
    claim=h.repo.claim(now_ms=NOW) if terminal in ('failure','lease_expiry') else None
    if terminal=='cancel':h.service.cancel('owner',job['jobId'])
    elif terminal=='delete':h.service.delete('owner',job['jobId'])
    elif terminal=='source':h.document_service.delete_document(user_id='owner',document_id=h.source.document_id)
    elif terminal=='failure':
        h.repo.finish(user_id='owner',job_id=job['jobId'],token=claim['claim_token'],revision=claim['revision'],now_ms=NOW+1,error='invalid_output')
    else:h.repo.reap(now_ms=NOW+(h.repo.queue_lifetime_ms+1 if terminal=='queue_expiry' else h.repo.lease_ms+1))
    h.repo.reap(now_ms=NOW+2*h.repo.queue_lifetime_ms)
    h.service.delete('owner',job['jobId']);h.service.delete('owner',job['jobId'])
    if claim:
        assert h.repo.finish(user_id='owner',job_id=job['jobId'],token=claim['claim_token'],revision=claim['revision'],now_ms=NOW+2,review={},draft='late') is False
    entries=ledger(h)
    assert sorted(r.points for r in entries)==[-100,100]
    assert h.billing.state_for_user(user_id='owner').balance==200
    with h.repo.connect() as c:
        assert c.execute('SELECT status FROM cn_resume_optimizer_usage').fetchone()['status']=='released'


def test_midnight_replay_and_prior_day_refund_do_not_multiply_current_free(harness):
    h=harness;member(h)
    req=creation(h);first=h.service.create('owner',req)
    h.now[0]=NOW+60_000
    assert quota_day(h.now[0])!=quota_day(NOW) and reset_at(NOW)==NOW+30_000
    assert h.service.capabilities('owner')['dailyRemaining']==3
    assert h.service.create('owner',req)['jobId']==first['jobId']
    h.service.cancel('owner',first['jobId'])
    second=h.service.create('owner',creation(h,key='today'))
    h.service.cancel('owner',first['jobId'])
    assert second['quotaDay']!=first['quotaDay'] and h.service.capabilities('owner')['dailyRemaining']==2
    assert h.billing.state_for_user(user_id='owner').balance==200


def test_quote_changes_never_switch_free_to_points_and_confirmation_is_required(harness):
    h=harness;member(h)
    stale=creation(h)
    complete(h,h.service.create('owner',stale))
    for index in range(2):
        complete(h,h.service.create('owner',creation(h,key=f'exhaust-free-{index}')))
    assert_error('quote_changed',lambda:h.service.create('owner',stale.model_copy(update={'idempotency_key':'stale'})))
    unconfirmed=creation(h,key='unconfirmed',confirmPointsCharge=False)
    assert_error('points_confirmation_required',lambda:h.service.create('owner',unconfirmed))
    assert h.billing.state_for_user(user_id='owner').balance==200 and not ledger(h)


def test_matching_replay_ignores_changed_quotes_after_membership_expiry_without_new_charge(harness):
    h=harness;member(h,ends=NOW+1)
    job=complete(h,h.service.create('owner',creation(h)))
    h.now[0]=NOW+60_000
    replay=h.service.create('owner',creation(h,key='synthetic-key'))
    assert replay['jobId']==job['jobId'] and h.billing.state_for_user(user_id='owner').balance==200
    assert_error('idempotency_conflict',lambda:h.service.create('owner',creation(h,targetRole='另一岗位')))


def test_existing_index_and_answer_reservations_are_not_spendable_twice(harness):
    h=harness
    reserved=h.billing_repository.reserve_usage(usage={'reservation_id':'synthetic-reservation','usage_id':'synthetic-answer','user_id':'owner',
        'usage_kind':'answer','points_reserved':120,'wallet_only':True},created_at_ms=NOW)
    assert reserved['status']=='reserved'
    assert h.service.capabilities('owner')['availablePoints']==80
    assert_error('insufficient_balance',lambda:h.service.create('owner',creation(h)))
    assert not ledger(h)
    h.billing_repository.release_usage(usage_id='synthetic-answer',released_at_ms=NOW+1)
    job=h.service.create('owner',creation(h))
    assert h.service.capabilities('owner')['availablePoints']==100
    assert job['status']=='queued'


def test_same_wallet_concurrent_mock_creation_and_optimizer_cannot_overspend(harness):
    h=harness
    # Leave exactly 100 points. Both operations use billing-user:owner.
    with h.repo.connect() as c:c.execute("INSERT INTO points_redemption_ledger VALUES('synthetic-debit','owner','admin_adjustment',-100,%s,'synthetic-debit','合成余额调整')",(NOW,))
    gate=Barrier(2)
    def optimizer():
        gate.wait()
        try:return ('optimizer',h.service.create('owner',creation(h)))
        except DomainRequestError as e:return ('rejected',e.error_code)
    def mock():
        gate.wait()
        try:return ('mock',h.mock.create(user_id='owner',idempotency_key='synthetic-mock',title='合成模拟面试',target_role='后端',expected_billing_class='points',now_ms=NOW))
        except DomainRequestError as e:return ('rejected',e.error_code)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda f:f(),[optimizer,mock]))
    assert sum(r[0]!='rejected' for r in results)==1
    assert h.billing.state_for_user(user_id='owner').balance==0


def test_duplicate_concurrent_creation_is_one_charge_one_job(harness):
    h=harness;req=creation(h)
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(lambda _:h.service.create('owner',req),range(4)))
    assert len({r['jobId'] for r in results})==1 and len(ledger(h))==1
    assert h.billing.state_for_user(user_id='owner').balance==100


def test_completion_races_cancel_financial_terminal_is_consistent(harness):
    h=harness;job=h.service.create('owner',creation(h));claim=h.repo.claim(now_ms=NOW);gate=Barrier(2)
    def finish():
        gate.wait();return h.repo.finish(user_id='owner',job_id=job['jobId'],token=claim['claim_token'],revision=claim['revision'],now_ms=NOW+1,review={'synthetic':True},draft='合成优化稿')
    def cancel():gate.wait();return h.service.cancel('owner',job['jobId'])
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda f:f(),[finish,cancel]))
    done=h.service.get('owner',job['jobId'])
    assert (done['status'],done['billingStatus'],h.billing.state_for_user(user_id='owner').balance) in [('completed','settled',100),('cancelled','released',200)]


def test_admission_write_failure_rolls_back_charge_job_and_usage(harness,monkeypatch):
    h=harness;original=h.repo._row
    def fail(*args,**kwargs):raise RuntimeError('synthetic insertion failure')
    monkeypatch.setattr(h.repo,'_row',fail)
    with pytest.raises(RuntimeError):h.service.create('owner',creation(h))
    monkeypatch.setattr(h.repo,'_row',original)
    assert h.billing.state_for_user(user_id='owner').balance==200 and not ledger(h)
    with h.repo.connect() as c:
        assert c.execute('SELECT count(*) FROM cn_resume_optimizer_jobs').fetchone()['count']==0
        assert c.execute('SELECT count(*) FROM cn_resume_optimizer_usage').fetchone()['count']==0


def test_migration_preserves_custom_kind_original_amount_rules_and_immutability(harness):
    h=harness
    with h.repo.connect() as c:
        for name in ['points_redemption_ledger_kind_check','points_redemption_ledger_points_check']:
            expr=c.execute("SELECT pg_get_expr(conbin,conrelid) AS expr FROM pg_constraint WHERE conrelid='points_redemption_ledger'::regclass AND conname=%s",(name,)).fetchone()['expr']
            from psycopg import sql
            c.execute(sql.SQL('ALTER TABLE points_redemption_ledger DROP CONSTRAINT {}').format(sql.Identifier(name)))
            c.execute(sql.SQL("ALTER TABLE points_redemption_ledger ADD CONSTRAINT {} CHECK (({}) OR (kind='synthetic_custom_kind' AND points=7))").format(sql.Identifier(name),sql.SQL(expr)))
        c.execute("DELETE FROM offersteady_schema_migrations WHERE migration_name='0054_cn_resume_optimizer.sql'")
    CNResumeOptimizerRepository(h.settings)
    CNResumeOptimizerRepository(h.settings)
    with h.repo.connect() as c:
        c.execute("INSERT INTO points_redemption_ledger VALUES('custom','owner','synthetic_custom_kind',7,%s,'custom','合成自定义流水')",(NOW,))
    for kind,points in [('synthetic_custom_kind',8),('resume_optimizer_charge',-99),('resume_optimizer_refund',99),('answer_settlement',100),('mock_interview_refund',-100)]:
        with pytest.raises(psycopg.errors.CheckViolation):
            with h.repo.connect() as c:c.execute('INSERT INTO points_redemption_ledger VALUES(%s,%s,%s,%s,%s,%s,%s)',(uuid4().hex,'owner',kind,points,NOW,uuid4().hex,'合成非法流水'))
    with pytest.raises(psycopg.errors.RaiseException):
        with h.repo.connect() as c:c.execute("UPDATE points_redemption_ledger SET points=8 WHERE ledger_entry_id='custom'")


def test_failed_refund_transaction_keeps_original_job_and_charge_for_safe_retry(harness,monkeypatch):
    h=harness;job=h.service.create('owner',creation(h));original=h.repo._ledger
    def fail_after_write(cursor,**kwargs):
        original(cursor,**kwargs)
        raise RuntimeError('synthetic interruption after refund insert')
    monkeypatch.setattr(type(h.repo),'_ledger',staticmethod(fail_after_write))
    with pytest.raises(RuntimeError):h.service.cancel('owner',job['jobId'])
    assert h.service.get('owner',job['jobId'])['status']=='queued'
    assert h.billing.state_for_user(user_id='owner').balance==100
    assert len(ledger(h))==1
    monkeypatch.setattr(type(h.repo),'_ledger',staticmethod(original))
    result=h.service.cancel('owner',job['jobId'])
    assert result['status']=='cancelled' and result['billingStatus']=='released'
    assert h.billing.state_for_user(user_id='owner').balance==200 and len(ledger(h))==2


@pytest.mark.parametrize('member_free',[False,True])
def test_failure_diagnostic_and_financial_release_commit_atomically(harness,monkeypatch,member_free):
    h=harness
    if member_free:member(h)
    job=h.service.create('owner',creation(h));claim=h.repo.claim(now_ms=NOW)
    original=h.repo._release
    diagnostic=failure_diagnostic('fact_numbers_changed')
    finish=dict(user_id='owner',job_id=job['jobId'],token=claim['claim_token'],revision=claim['revision'],
        now_ms=NOW+1,error='invalid_output',diagnostic=diagnostic)
    def fail_after_release(cursor,job_id,now_ms):
        original(cursor,job_id,now_ms)
        raise RuntimeError('synthetic failure after financial release')
    monkeypatch.setattr(type(h.repo),'_release',staticmethod(fail_after_release))
    with pytest.raises(RuntimeError):h.repo.finish(**finish)
    row=h.repo.get(user_id='owner',job_id=job['jobId'],now_ms=NOW+1)
    assert row['status']=='running' and row['allowance_status']=='reserved'
    assert row['error_code'] is None and 'failureDiagnostic' not in row['payload']
    assert h.billing.state_for_user(user_id='owner').balance==(200 if member_free else 100)
    if member_free:assert h.service.capabilities('owner')['dailyRemaining']==2
    monkeypatch.setattr(type(h.repo),'_release',staticmethod(original))
    assert h.repo.finish(**finish) is True and h.repo.finish(**finish) is False
    row=h.repo.get(user_id='owner',job_id=job['jobId'],now_ms=NOW+1)
    assert row['status']=='failed' and row['allowance_status']=='released'
    assert row['payload']['failureDiagnostic']==diagnostic
    assert h.billing.state_for_user(user_id='owner').balance==200
    assert sorted(r.points for r in ledger(h))==([] if member_free else [-100,100])
    if member_free:assert h.service.capabilities('owner')['dailyRemaining']==3


def test_migration_missing_old_guard_fails_closed(harness):
    h=harness
    with h.repo.connect() as c:
        c.execute('ALTER TABLE points_redemption_ledger DROP CONSTRAINT points_redemption_ledger_kind_check')
        c.execute("DELETE FROM offersteady_schema_migrations WHERE migration_name='0054_cn_resume_optimizer.sql'")
    with pytest.raises(psycopg.errors.RaiseException,match='cn_resume_optimizer_missing_wallet_guards'):
        CNResumeOptimizerRepository(h.settings)
    with h.repo.connect() as c:
        assert c.execute("SELECT count(*) FROM offersteady_schema_migrations WHERE migration_name='0054_cn_resume_optimizer.sql'").fetchone()['count']==0
        assert c.execute("SELECT count(*) FROM pg_constraint WHERE conrelid='points_redemption_ledger'::regclass AND conname='points_redemption_ledger_points_check'").fetchone()['count']==1
