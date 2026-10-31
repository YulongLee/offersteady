"""Same-session readiness recovery preserves real isolated-PG quota and deadlines."""
import asyncio

import pytest

from app.core.errors import DomainRequestError
from app.services.mock_interview_repository import round_state
from test_mock_interview_postgres import DATABASE_URL, mock_runtime_fixture, repositories


pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="Isolated PostgreSQL required")


@pytest.mark.parametrize("member", [False, True])
@pytest.mark.parametrize("permission,code", [
    ("unknown", "mock_microphone_checking"), ("denied", "mock_microphone_required"),
])
def test_pending_or_denied_recovery_preserves_real_charge_quota_and_start_deadline(
    repositories, member, permission, code,
):
    async def run():
        runtime, owner, sid, now, generator, billing = mock_runtime_fixture(repositories, member=member)
        device = runtime.realtime.repository.get_desktop_device_by_code.return_value
        device.capabilities["microphone"] = permission
        before_balance = billing.state_for_user(user_id=owner).balance
        def quota_and_price():
            # The quote includes server time; compare financial/quota fields.
            return {key: value for key, value in runtime.repository.quote(owner, now[0]).items()
                    if key != "nowMs"}
        before_quote = quota_and_price()
        messages = []
        async def send(value):
            messages.append(value)
        try:
            controller = await runtime.attach(user_id=owner, session_id=sid, send=send)
            initial = messages[-1]
            assert initial["preparation"]["code"] == code
            assert not initial["preparation"]["ready"]
            version = round_state(controller.record).version
            with pytest.raises(DomainRequestError) as error:
                await runtime.command(controller, action="start", version=version)
            assert error.value.error_code == code
            pending = runtime.repository.get(user_id=owner, session_id=sid)
            assert round_state(pending).phase == "preparing"
            assert pending["data"]["started_at_ms"] is None
            assert pending["data"]["deadline_at_ms"] is None
            assert pending["data"]["clock_at_ms"] is None
            generator.question.assert_not_called()
            assert runtime.audio.snapshot()["captures"] == 0
            # A heartbeat only refreshes readiness; the original paid/free record
            # and selected resume survive without creating or starting a session.
            now[0] += 5000
            device.capabilities["microphone"] = "granted"
            await runtime.heartbeat(controller)
            recovered = messages[-1]
            assert recovered["preparation"]["ready"]
            assert recovered["session"] == initial["session"]
            assert billing.state_for_user(user_id=owner).balance == before_balance
            assert quota_and_price() == before_quote
            generator.question.assert_not_called()
            assert controller.record["data"]["clock_at_ms"] is None
            # Only the user's later start starts the existing sixty-minute limit.
            await runtime.command(controller, action="start", version=version)
            await controller.generation
            started = runtime.repository.get(user_id=owner, session_id=sid)
            assert round_state(started).phase == "speaking"
            assert started["data"]["started_at_ms"] == now[0]
            assert started["data"]["deadline_at_ms"] == now[0] + 3_600_000
            assert billing.state_for_user(user_id=owner).balance == before_balance
            assert quota_and_price() == before_quote
            assert started["data"]["billed_minutes"] == 0
            assert runtime.audio.snapshot()["captures"] == 0
            assert len(runtime.repository.list(user_id=owner)) == 1
        finally:
            await runtime.shutdown()
    asyncio.run(run())
