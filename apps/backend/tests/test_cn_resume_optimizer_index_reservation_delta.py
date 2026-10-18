"""One post-freeze delta exercising the actual old index-quote reservation path."""
import pytest
from app.core.errors import DomainRequestError
from cn_resume_optimizer_test_support import harness,ensure_synthetic_database,creation


def test_actual_knowledge_index_reservation_blocks_optimizer_until_released(harness):
    h=harness
    # This invokes the unchanged BillingService and real PostgreSQL quote,
    # billing-user lock, reservation and release. No direct reservation INSERT.
    version='synthetic-owned-knowledge-version'
    quote=h.billing.quote_knowledge_index(user_id='owner',document_version_id=version,
        token_estimate=30_000,idempotency_key='synthetic-index-budget')
    assert quote.points_required==120
    reserved=h.billing.reserve_knowledge_index_for_quote(user_id='owner',quote_id=quote.quote_id,
        document_version_id=version)
    assert reserved.status=='reserved' and reserved.points_reserved==120 and reserved.billing_source=='points'
    assert h.billing.state_for_user(user_id='owner').balance==200
    assert h.service.capabilities('owner')['availablePoints']==80
    with pytest.raises(DomainRequestError) as exc:
        h.service.create('owner',creation(h))
    assert exc.value.error_code=='resume_optimizer_insufficient_balance'
    assert h.service.provider.calls==0
    with h.repo.connect() as connection:
        assert connection.execute('SELECT count(*) FROM cn_resume_optimizer_jobs').fetchone()['count']==0
        assert connection.execute('SELECT count(*) FROM cn_resume_optimizer_usage').fetchone()['count']==0
    assert not [row for row in h.billing.state_for_user(user_id='owner').ledger if row.kind.startswith('resume_optimizer_')]

    released=h.billing.release_knowledge_index(quote_id=quote.quote_id)
    assert released.status=='released'
    assert h.service.capabilities('owner')['availablePoints']==200
    request=creation(h)
    job=h.service.create('owner',request)
    assert job['billingClass']=='points' and job['pointsCharged']==100 and job['billingStatus']=='reserved'
    assert h.service.capabilities('owner')['availablePoints']==100
    assert h.billing.state_for_user(user_id='owner').balance==100
    assert h.service.create('owner',request)['jobId']==job['jobId']
    assert h.billing.release_knowledge_index(quote_id=quote.quote_id).status=='released'
    assert h.billing.state_for_user(user_id='owner').balance==100

    first=h.service.cancel('owner',job['jobId'])
    second=h.service.cancel('owner',job['jobId'])
    assert first['billingStatus']==second['billingStatus']=='released'
    state=h.billing.state_for_user(user_id='owner')
    assert state.balance==200
    optimizer=[row for row in state.ledger if row.kind.startswith('resume_optimizer_')]
    assert sorted((row.kind,row.points) for row in optimizer)==[
        ('resume_optimizer_charge',-100),('resume_optimizer_refund',100)]
    assert not [row for row in state.ledger if row.kind=='knowledge_index_settlement']
