"""Source fragment embedded in the single read-only actual-image probe."""


async def synthetic_cleanup_control(settings, request):
    from collections import deque
    from dataclasses import asdict
    import time
    from app.ports.realtime_speech import AccountDesktopDeviceRecord
    from app.services.cn_realtime_entity_state import CNRealtimeEntityState
    from app.services.redis_realtime_speech_repository import RedisRealtimeSpeechRepository
    from app.services import realtime_speech_service as realtime
    from app.services.dashscope_realtime_asr_gateway import DashScopeRealtimeAsrGateway, _SourceRealtimeSession
    from app.services.cn_provider_close_executor import CnProviderCloseExecutor
    from app.services.cn_realtime_io_executor import CnRealtimeIoExecutor

    target = fixture(settings)
    binding = replace(target.state.binding, capabilities={"array": [], "precision": 2**53+1})
    account = AccountDesktopDeviceRecord(OWNER, DEVICE, CODE, 1, 2)
    store = object.__new__(CNRealtimeEntityState)
    store._legacy_deadline = None; store.ttl = 300; store.base = "synthetic-runtime"
    store.keys = ["synthetic-key-"+str(i) for i in range(18)]
    calls = []
    def scripted(*, keys, args):
        calls.append(args[0])
        require(args[4:] == [OWNER], "owner_reference_identity_changed")
        record = binding if args[0] == "owner_bindings" else account
        require(args[0] in {"owner_bindings", "owner_accounts"}, "owner_read_operation_changed")
        return [[json.dumps(asdict(record)), 0]]
    store._script = scripted
    repository = object.__new__(RedisRealtimeSpeechRepository)
    repository._cn_controls = store
    require(repository.list_session_desktop_bindings_for_user(user_id=OWNER) == [binding]
        and repository.list_account_desktop_devices(user_id=OWNER) == [account]
        and calls == ["owner_bindings", "owner_accounts"], "owner_read_dispatch_changed")
    # Lua execution and scale budgets are proved by the real local Redis suite;
    # this isolated image probe only verifies the shipped Python dispatch.
    service = object.__new__(realtime.RealtimeSpeechService)
    service.settings = settings
    service.logger = logging.getLogger("synthetic-lightweight-ack")
    service.logger.setLevel(logging.INFO)
    access = Mock()
    service.session_service = SimpleNamespace(get_control_state=access, get_session=deny)
    service._trace_lock = threading.Lock(); service._trace_records = {}; service._trace_order = deque(maxlen=4096)
    service._latest_timing = lambda **kwargs: None
    with patch.object(realtime, "log_event", side_effect=deny):
        for stage in ("transcript-delivery", "transcript-render", "answer-first-render", "screenshot-first-render"):
            event = service.acknowledge_runtime_timing(user_id=OWNER, session_id=SESSION,
                trace_id="synthetic-trace", stage=stage, duration_ms=20)
            require(event.kind == "performance-ack" and event.payload["stage"] == stage, "ack_wire_changed")
    require(access.call_count == 4, "ack_lightweight_authority_missing")

    gateway = DashScopeRealtimeAsrGateway(settings, logging.getLogger("synthetic-close"))
    entered, release = threading.Event(), threading.Event()
    def slow_close():
        entered.set(); require(release.wait(3), "synthetic_physical_close_not_released")
    old = _SourceRealtimeSession(SimpleNamespace(close=slow_close), 16000,
        time.monotonic(), time.monotonic(), SESSION+":microphone", "microphone")
    gateway._source_sessions[SESSION+":microphone"] = old
    try:
        require(gateway.close_source_deferred(session_id=SESSION, source_kind="microphone") == 1,
            "deferred_close_capability_missing")
        await until(entered.is_set, "deferred_close_not_started")
        require(old.closed and not old.accepting_transcript_events
            and SESSION+":microphone" not in gateway._source_sessions, "old_source_not_fenced")
        replacement = Mock()
        gateway._source_sessions[SESSION+":microphone"] = _SourceRealtimeSession(replacement, 16000,
            time.monotonic(), time.monotonic(), SESSION+":microphone", "microphone")
        release.set(); gateway.drain_deferred_closes()
        require(replacement.close.call_count == 0, "old_close_touched_replacement")
    finally:
        release.set(); gateway.close_all_sessions()

    # Both lifecycle workers are occupied; preparation must still progress.
    executor = CnRealtimeIoExecutor()
    ready, finish = [], threading.Event()
    def block():
        ready.append(1); require(finish.wait(3), "synthetic_lifecycle_not_released")
    blockers = [asyncio.create_task(executor.run(block, lane="lifecycle",
        operation_name="publisher_disconnect")) for _ in range(2)]
    create_entered, create_finish, cleaned = threading.Event(), threading.Event(), []
    def create():
        create_entered.set(); require(create_finish.wait(3), "synthetic_prepare_not_released"); return "synthetic-created"
    pending = None
    try:
        await until(lambda: len(ready) == 2, "both_lifecycle_workers_not_occupied")
        require(await asyncio.wait_for(executor.run(lambda: 23, lane="preparation",
            operation_name="publisher_prepare"), 1) == 23, "preparation_blocked_by_lifecycle")
        pending = asyncio.create_task(executor.run(create, lane="preparation",
            operation_name="publisher_create", on_abandoned_result=cleaned.append))
        await until(create_entered.is_set, "preparation_create_not_started")
        pending.cancel(); create_finish.set(); finish.set()
        result = await asyncio.gather(pending, return_exceptions=True)
        require(isinstance(result[0], asyncio.CancelledError) and cleaned == ["synthetic-created"],
            "preparation_cancel_cleanup_lost_or_replayed")
        await asyncio.gather(*blockers)
        diag = executor.diagnostics()["preparation"]
        require((diag["configuredWorkers"], diag["configuredQueueMax"]) == (2, 8), "preparation_capacity_changed")
    finally:
        finish.set(); create_finish.set()
        await asyncio.gather(*blockers, *([pending] if pending is not None else []), return_exceptions=True)
        executor.shutdown()

    # A submit can fail after enqueue. A late queued call must be a no-op.
    closer = CnProviderCloseExecutor(logging.getLogger("synthetic-submit"), workers=1, queue_max=0)
    queued, closed = [], []
    def failed_submit(operation, *args):
        queued.append((operation, args)); raise RuntimeError("synthetic-start-failure")
    try:
        with patch.object(closer._pool, "submit", failed_submit):
            closer.close(lambda: closed.append(1))
            operation, args = queued[0]; operation(*args)
            require(closed == [1] and closer.diagnostics()["pending"] == 0,
                "ambiguous_submit_replayed_close_or_permit")
    finally:
        closer.shutdown()
    return {"ownerScopedReadDispatchPassed": True, "ownerScopedReadActualLuaExecuted": False,
        "lightweightAckStages": 4, "disabledAckDebugSerializationSkipped": True,
        "detachedOldCloseCannotTouchReplacement": True, "preparationIndependentFromBothLifecycleWorkers": True,
        "preparationCancelledResourceCompensatedOnce": True, "ambiguousCloseSubmitExactlyOnce": True}
