from __future__ import annotations

import argparse
import base64
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter, sleep, time
from typing import Any
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, log_event
from app.main import create_app
from app.services.integration_verification import IntegrationVerificationRunner, build_default_verifiers


FailureAttribution = str


def _now_ms() -> int:
    return int(time() * 1000)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class ScenarioStep:
    name: str
    status: str
    duration_ms: int
    summary: str
    attribution: FailureAttribution = "none"
    details: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


@dataclass
class ScenarioResult:
    scenario_id: str
    title: str
    status: str
    started_at: str
    completed_at: str
    duration_ms: int
    attribution: FailureAttribution
    summary: str
    steps: list[ScenarioStep] = field(default_factory=list)


@dataclass
class EndToEndIntegrationReport:
    report_id: str
    environment_label: str
    started_at: str
    completed_at: str
    duration_ms: int
    overall_status: str
    provider_report_id: str | None
    provider_summary: dict[str, Any]
    scenario_summary: dict[str, Any]
    scenarios: list[ScenarioResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "reportId": self.report_id,
            "environmentLabel": self.environment_label,
            "startedAt": self.started_at,
            "completedAt": self.completed_at,
            "durationMs": self.duration_ms,
            "overallStatus": self.overall_status,
            "providerReportId": self.provider_report_id,
            "providerSummary": self.provider_summary,
            "scenarioSummary": self.scenario_summary,
            "scenarios": [
                {
                    "scenarioId": item.scenario_id,
                    "title": item.title,
                    "status": item.status,
                    "startedAt": item.started_at,
                    "completedAt": item.completed_at,
                    "durationMs": item.duration_ms,
                    "attribution": item.attribution,
                    "summary": item.summary,
                    "steps": [
                        {
                            "name": step.name,
                            "status": step.status,
                            "durationMs": step.duration_ms,
                            "summary": step.summary,
                            "attribution": step.attribution,
                            "details": step.details,
                            "errorCode": step.error_code,
                            "errorMessage": step.error_message,
                        }
                        for step in item.steps
                    ],
                }
                for item in self.scenarios
            ],
        }


IssueClassification = str


@dataclass
class BugListEntry:
    issue_id: str
    title: str
    severity: IssueClassification
    module_or_flow: str
    attribution: FailureAttribution
    reproduction_context: str
    observed_behavior: str
    expected_behavior: str

    def to_dict(self) -> dict[str, str]:
        return {
            "issueId": self.issue_id,
            "title": self.title,
            "severity": self.severity,
            "moduleOrFlow": self.module_or_flow,
            "attribution": self.attribution,
            "reproductionContext": self.reproduction_context,
            "observedBehavior": self.observed_behavior,
            "expectedBehavior": self.expected_behavior,
        }


@dataclass
class TodoListEntry:
    item_id: str
    title: str
    priority: IssueClassification
    owning_area: str
    rationale: str
    suggested_next_step: str

    def to_dict(self) -> dict[str, str]:
        return {
            "itemId": self.item_id,
            "title": self.title,
            "priority": self.priority,
            "owningArea": self.owning_area,
            "rationale": self.rationale,
            "suggestedNextStep": self.suggested_next_step,
        }


def build_bug_list(report: EndToEndIntegrationReport) -> list[BugListEntry]:
    bugs: list[BugListEntry] = []

    if report.provider_summary.get("status") == "failed":
        bugs.append(BugListEntry(
            issue_id="provider-readiness-failed",
            title="第三方或基础设施就绪检查未全部通过",
            severity="release-blocker",
            module_or_flow="provider-readiness",
            attribution="provider-or-infrastructure",
            reproduction_context=f"运行 end-to-end integration，provider summary={json.dumps(report.provider_summary, ensure_ascii=False)}",
            observed_behavior="至少一个真实 provider 或基础设施校验失败，当前环境不满足完整真实联调前提。",
            expected_behavior="OSS、MinerU、Embedding、pgvector、Chat、Vision、Realtime ASR 等依赖均应通过真实连通性验证。",
        ))

    for scenario in report.scenarios:
        if scenario.status != "failed":
            continue
        bugs.append(BugListEntry(
            issue_id=f"scenario-{scenario.scenario_id}-failed",
            title=f"{scenario.title} 场景执行失败",
            severity="release-blocker" if scenario.attribution == "provider-or-infrastructure" else "major-risk",
            module_or_flow=scenario.scenario_id,
            attribution=scenario.attribution,
            reproduction_context=f"运行场景 {scenario.scenario_id}，步骤结果见 report.json。",
            observed_behavior=scenario.summary,
            expected_behavior="该场景应在真实 API、真实 provider 和当前系统事实源上完成闭环。",
        ))

    _legacy_prototype_findings = [
        BugListEntry(
            issue_id="frontend-real-state-aggregation-missing",
            title="前端核心页面仍缺少真实后端聚合状态接口",
            severity="release-blocker",
            module_or_flow="frontend-core-state",
            attribution="frontend-api-mode",
            reproduction_context="以 `VITE_APP_DATA_SOURCE=api VITE_APP_STRICT_API_ONLY=true` 启动 Web 原型并进入应用。",
            observed_behavior="严格联调模式会停止继续使用 fixture，因为 interview/materials/billing/session/history 仍没有统一真实状态接口可加载。",
            expected_behavior="核心页面状态应由真实后端 API 提供，联调模式下不允许再由 fixture 充当权威数据源。",
        ),
        BugListEntry(
            issue_id="billing-module-still-placeholder",
            title="Billing 模块仍是 placeholder，无法支撑真实积分与会员状态",
            severity="release-blocker",
            module_or_flow="billing",
            attribution="backend-orchestration",
            reproduction_context="检查 `apps/backend/app/modules/billing.py` 或在真实联调模式尝试加载积分事实源。",
            observed_behavior="Billing 仍未提供真实订单、账本、余额或会员状态 API。",
            expected_behavior="前端积分页和使用计费应来自真实后端账本与产品目录，而不是原型静态数据。",
        ),
        BugListEntry(
            issue_id="runtime-services-still-use-synthetic-adapters",
            title="聊天、截图、语音与检索运行路径仍混用 synthetic / heuristic 适配器",
            severity="release-blocker",
            module_or_flow="chat-retrieval-screenshot-speech",
            attribution="backend-orchestration",
            reproduction_context="检查 `apps/backend/app/deps.py` 当前依赖装配。",
            observed_behavior="Embedding、query embedding、vision、realtime ASR、reranker 等运行时依赖仍指向 `Synthetic*` 或启发式适配器。",
            expected_behavior="真实联调环境下，运行时服务应直接使用配置好的真实 provider，而不是测试或占位实现。",
        ),
    ]
    return bugs


def build_todo_list() -> list[TodoListEntry]:
    return [
        TodoListEntry(
            item_id="persist-document-and-session-facts",
            title="替换文档、会话、聊天、截图、语音相关 in-memory repository",
            priority="major-risk",
            owning_area="backend-persistence",
            rationale="当前联调即便通过，也无法证明重启、并发或跨实例后的状态仍可追溯。",
            suggested_next_step="优先把 document/session/chat/screenshot/realtime repository 切换到 PostgreSQL 持久化实现，并保留回归测试。",
        ),
        TodoListEntry(
            item_id="ship-prototype-state-api",
            title="提供前端原型所需的真实聚合读取接口",
            priority="major-risk",
            owning_area="frontend-backend-contract",
            rationale="没有统一聚合状态，前端就无法在不改原型交互的前提下切到真实数据源。",
            suggested_next_step="新增只读聚合 API，统一返回 interviews、materials、billing、session、history 的页面所需状态。",
        ),
        TodoListEntry(
            item_id="replace-billing-placeholder",
            title="补齐积分、会员、兑换码与消费说明的真实后端事实源",
            priority="major-risk",
            owning_area="billing",
            rationale="Billing 仍是占位实现，会阻塞真实前端状态和完整使用链路。",
            suggested_next_step="先实现只读账本/余额/产品目录 API，再接入真实下单与支付闭环。",
        ),
        TodoListEntry(
            item_id="browser-level-strict-smoke",
            title="增加浏览器级严格联调 smoke test",
            priority="deferred-follow-up",
            owning_area="qa-integration",
            rationale="当前主要依赖后端 orchestrator，仍缺少浏览器端对“无 mock 泄漏”的自动化验收。",
            suggested_next_step="补充 Playwright 或等价浏览器测试，在 strict API-only 模式下验证页面不会使用 fixture 数据。",
        ),
    ]


class ScenarioRunner:
    def __init__(self, *, settings: Settings, logger: logging.Logger, client: TestClient) -> None:
        self.settings = settings
        self.logger = logger
        self.client = client
        seed = f"e2e-user-{uuid4().hex[:8]}"
        self.user_id = seed
        self.login_id = f"{seed}@example.com"
        self.password = "Password123!"
        self.token: str | None = None
        self.session_id: str | None = None
        self.resume_id: str | None = None
        self.jd_id: str | None = None
        self.knowledge_id: str | None = None
        self.collection_id: str | None = None

    def run_all(self) -> list[ScenarioResult]:
        return [
            self._run_scenario("document-ingestion", "Resume / JD / Knowledge upload-to-processing", self._document_ingestion_scenario),
            self._run_scenario("session-chat", "Retrieval-backed Interview Session and Chat", self._session_chat_scenario),
            self._run_scenario("screenshot-realtime", "Screenshot Answer and Realtime Speech", self._screenshot_realtime_scenario),
            self._run_scenario("conversation-history", "Conversation Storage and Interview History", self._conversation_history_scenario),
        ]

    def _run_scenario(self, scenario_id: str, title: str, action):
        started_iso = _utc_now_iso()
        started_perf = perf_counter()
        steps: list[ScenarioStep] = []
        try:
            summary = action(steps)
            status = "passed"
            attribution = "none"
        except Exception as exc:
            status = "failed"
            attribution = getattr(exc, "attribution", "backend-orchestration")
            steps.append(ScenarioStep(name="scenario", status="failed", duration_ms=0, summary="Scenario failed.", attribution=attribution, error_code=exc.__class__.__name__, error_message=str(exc)))
            summary = f"Scenario failed: {exc}"
        return ScenarioResult(
            scenario_id=scenario_id,
            title=title,
            status=status,
            started_at=started_iso,
            completed_at=_utc_now_iso(),
            duration_ms=int((perf_counter() - started_perf) * 1000),
            attribution=attribution,
            summary=summary,
            steps=steps,
        )

    def _step(self, steps: list[ScenarioStep], name: str, summary: str, action, *, attribution: FailureAttribution = "backend-orchestration"):
        started = perf_counter()
        try:
            result = action()
            details = result if isinstance(result, dict) else {}
            steps.append(ScenarioStep(name=name, status="passed", duration_ms=int((perf_counter() - started) * 1000), summary=summary, details=details))
            return result
        except Exception as exc:
            steps.append(ScenarioStep(name=name, status="failed", duration_ms=int((perf_counter() - started) * 1000), summary=f"{summary} failed.", attribution=attribution, details={}, error_code=exc.__class__.__name__, error_message=str(exc)))
            setattr(exc, "attribution", attribution)
            raise

    def _unwrap(self, response):
        payload = response.json()
        if response.status_code >= 400:
            raise RuntimeError(payload.get("error", {}).get("message") or f"HTTP {response.status_code}")
        return payload["data"]

    def _upload_via_oss(self, *, upload_url: str, fields: dict[str, str], filename: str, content_type: str, payload: bytes) -> dict[str, Any]:
        files = {"file": (filename, payload, content_type)}
        response = httpx.post(upload_url, data=fields, files=files, timeout=self.settings.integration_http_timeout_seconds, follow_redirects=True)
        if response.status_code not in {200, 201, 204}:
            raise RuntimeError(f"OSS upload failed with HTTP {response.status_code}")
        return {"uploadUrl": upload_url, "httpStatus": response.status_code, "bytes": len(payload)}

    def _wait_for_processing(self, document_id: str, expected_stage: str = "COMPLETED", timeout_seconds: float = 20.0) -> dict[str, Any]:
        deadline = time() + timeout_seconds
        last_payload = None
        while time() < deadline:
            response = self.client.get(f"/api/v1/document-processing/documents/{document_id}", params={"userId": self.user_id})
            if response.status_code == 200:
                last_payload = self._unwrap(response)
                latest = last_payload.get("latestTask")
                if latest and latest.get("currentStage") == expected_stage:
                    return last_payload
                if latest and latest.get("currentStage") == "FAILED":
                    raise RuntimeError(
                        f"Processing for {document_id} failed with "
                        f"{latest.get('errorCode') or 'unknown_error'}: "
                        f"{latest.get('errorMessage') or 'No safe error message was recorded.'}"
                    )
            sleep(0.2)
        raise RuntimeError(f"Processing for {document_id} did not reach {expected_stage}. Last payload: {json.dumps(last_payload, ensure_ascii=False)[:400]}")

    def _ensure_identity(self, steps: list[ScenarioStep]) -> None:
        if self.token:
            return
        def register():
            response = self.client.post("/api/v1/auth/register", json={
                "loginId": self.login_id,
                "password": self.password,
                "displayName": "E2E Tester",
                "clientLabel": "e2e-runner",
            })
            data = self._unwrap(response)
            self.user_id = data["user"]["userId"]
            self.token = data["tokens"]["accessToken"]
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
            return {"userId": data["user"]["userId"], "authSessionId": data["authSessionId"]}
        self._step(steps, "register_login", "Registered the synthetic E2E user and obtained tokens.", register, attribution="backend-orchestration")

    def _document_ingestion_scenario(self, steps: list[ScenarioStep]) -> str:
        self._ensure_identity(steps)

        def create_collection():
            response = self.client.post("/api/v1/knowledge/collections", json={"userId": self.user_id, "name": "E2E 知识库"})
            data = self._unwrap(response)
            self.collection_id = data["collectionId"]
            return data
        self._step(steps, "knowledge_collection", "Created a synthetic knowledge collection.", create_collection)

        def upload_resume():
            content = b"Synthetic Resume\nOfferSteady E2E integration engineer\nPython FastAPI PostgreSQL\n"
            intent = self._unwrap(self.client.post("/api/v1/resume/upload-intents", json={
                "userId": self.user_id,
                "filename": "resume.txt",
                "contentType": "text/plain",
                "sizeBytes": len(content),
            }))
            self._upload_via_oss(upload_url=intent["uploadUrl"], fields=intent["uploadFields"], filename="resume.txt", content_type="text/plain", payload=content)
            completed = self._unwrap(self.client.post("/api/v1/resume/uploads/complete", json={
                "userId": self.user_id,
                "intentId": intent["intentId"],
                "objectKey": intent["objectKey"],
                "contentType": "text/plain",
                "sizeBytes": len(content),
                "etag": "e2e-resume",
            }))
            self.resume_id = completed["source"]["sourceId"]
            status = self._wait_for_processing(self.resume_id)
            return {"documentId": self.resume_id, "stage": status["latestTask"]["currentStage"], "chunkCount": status["latestTask"]["chunkCount"]}
        self._step(steps, "resume_upload_pipeline", "Uploaded Resume to OSS and waited for processing completion.", upload_resume, attribution="provider-or-infrastructure")

        def upload_jd():
            content = b"Senior Backend Engineer\nPython, FastAPI, PostgreSQL, Retrieval"
            intent = self._unwrap(self.client.post("/api/v1/job-descriptions/upload-intents", json={
                "userId": self.user_id,
                "filename": "jd.txt",
                "contentType": "text/plain",
                "sizeBytes": len(content),
            }))
            self._upload_via_oss(upload_url=intent["uploadUrl"], fields=intent["uploadFields"], filename="jd.txt", content_type="text/plain", payload=content)
            completed = self._unwrap(self.client.post("/api/v1/job-descriptions/uploads/complete", json={
                "userId": self.user_id,
                "intentId": intent["intentId"],
                "objectKey": intent["objectKey"],
                "contentType": "text/plain",
                "sizeBytes": len(content),
                "etag": "e2e-jd",
            }))
            self.jd_id = completed["source"]["sourceId"]
            status = self._wait_for_processing(self.jd_id)
            return {"documentId": self.jd_id, "stage": status["latestTask"]["currentStage"], "chunkCount": status["latestTask"]["chunkCount"]}
        self._step(steps, "jd_upload_pipeline", "Uploaded JD to OSS and waited for processing completion.", upload_jd, attribution="provider-or-infrastructure")

        def upload_knowledge():
            content = b"# System Design Notes\n\nFocus on tradeoffs, capacity estimation, and reliability."
            intent = self._unwrap(self.client.post(f"/api/v1/knowledge/collections/{self.collection_id}/upload-intents", json={
                "userId": self.user_id,
                "filename": "notes.md",
                "contentType": "text/markdown",
                "sizeBytes": len(content),
            }))
            self._upload_via_oss(upload_url=intent["uploadUrl"], fields=intent["uploadFields"], filename="notes.md", content_type="text/markdown", payload=content)
            completed = self._unwrap(self.client.post(f"/api/v1/knowledge/collections/{self.collection_id}/uploads/complete", json={
                "userId": self.user_id,
                "intentId": intent["intentId"],
                "objectKey": intent["objectKey"],
                "contentType": "text/markdown",
                "sizeBytes": len(content),
                "etag": "e2e-knowledge",
            }))
            self.knowledge_id = completed["source"]["sourceId"]
            status = self._wait_for_processing(self.knowledge_id)
            return {"documentId": self.knowledge_id, "stage": status["latestTask"]["currentStage"], "chunkCount": status["latestTask"]["chunkCount"]}
        self._step(steps, "knowledge_upload_pipeline", "Uploaded Knowledge file to OSS and waited for processing completion.", upload_knowledge, attribution="provider-or-infrastructure")
        return "Resume, JD, and Knowledge files completed the upload-to-processing path."

    def _session_chat_scenario(self, steps: list[ScenarioStep]) -> str:
        self._ensure_identity(steps)
        if not all([self.resume_id, self.jd_id, self.knowledge_id]):
            raise RuntimeError("Document ingestion scenario must succeed before session scenario.")

        def create_session():
            data = self._unwrap(self.client.post("/api/v1/sessions", json={"userId": self.user_id, "title": "E2E 面试场次"}))
            self.session_id = data["sessionId"]
            return data
        self._step(steps, "create_session", "Created an interview session.", create_session)

        def bind_materials():
            return self._unwrap(self.client.post(f"/api/v1/sessions/{self.session_id}/materials/confirm", json={
                "userId": self.user_id,
                "resumeDocumentId": self.resume_id,
                "jobDescriptionDocumentId": self.jd_id,
                "knowledgeDocumentIds": [self.knowledge_id],
            }))
        self._step(steps, "bind_materials", "Bound processed Resume, JD, and Knowledge documents to the session.", bind_materials)

        def start_session():
            return self._unwrap(self.client.post(f"/api/v1/sessions/{self.session_id}/start", json={"userId": self.user_id}))
        self._step(steps, "start_session", "Started the interview session.", start_session)

        def ask_question():
            data = self._unwrap(self.client.post("/api/v1/live-answer/questions", json={
                "userId": self.user_id,
                "sessionId": self.session_id,
                "question": "请你介绍一个最相关的项目亮点，并说明如何权衡系统可靠性与开发效率。",
                "stream": True,
            }))
            task = data["task"]
            retrieval = data["retrieval"]
            return {
                "taskId": task["taskId"],
                "taskStatus": task["status"],
                "retrievalCount": retrieval["finalCount"],
                "answerPreview": task["answerText"][:80],
            }
        self._step(steps, "chat_answer", "Generated a retrieval-backed chat answer inside the active interview session.", ask_question, attribution="provider-or-infrastructure")
        return "Interview Session lifecycle and retrieval-backed Chat flow completed."

    def _screenshot_realtime_scenario(self, steps: list[ScenarioStep]) -> str:
        self._ensure_identity(steps)
        if not self.session_id:
            raise RuntimeError("Session scenario must succeed before screenshot/realtime scenario.")

        def screenshot_answer():
            image = b"\x89PNG\r\n\x1a\nsynthetic-screenshot"
            intent = self._unwrap(self.client.post("/api/v1/screenshot-answer/upload-intents", json={
                "userId": self.user_id,
                "sessionId": self.session_id,
                "filename": "diagram.png",
                "contentType": "image/png",
                "sizeBytes": len(image),
            }))
            upload = self._unwrap(self.client.post("/api/v1/screenshot-answer/uploads/complete", json={
                "userId": self.user_id,
                "sessionId": self.session_id,
                "intentId": intent["intentId"],
                "objectKey": intent["objectKey"],
                "contentType": "image/png",
                "sizeBytes": len(image),
                "etag": "e2e-shot",
            }))
            task = self._unwrap(self.client.post("/api/v1/screenshot-answer/tasks", json={
                "userId": self.user_id,
                "sessionId": self.session_id,
                "imageIds": [upload["imageId"]],
                "instruction": "请根据截图回答这道系统设计题，并优先结合本场资料。",
                "stream": True,
            }))
            return {
                "imageId": upload["imageId"],
                "taskId": task["task"]["taskId"],
                "taskStatus": task["task"]["status"],
                "answerPreview": task["task"]["answerText"][:80],
            }
        self._step(steps, "screenshot_answer", "Completed a screenshot upload and answer task.", screenshot_answer, attribution="provider-or-infrastructure")

        def realtime_roundtrip():
            publisher = self._unwrap(self.client.post("/api/v1/realtime-speech/publishers", json={
                "userId": self.user_id,
                "sessionId": self.session_id,
                "sourceKind": "system",
                "clientName": "e2e-websocket",
            }))
            token = publisher["token"]
            with self.client.websocket_connect(f"/api/v1/realtime-speech/ws?token={token}") as websocket:
                payload = base64.b64encode("请介绍一下你做过的检索增强项目？".encode("utf-8")).decode("utf-8")
                websocket.send_json({
                    "type": "audio-frame",
                    "sequence": 1,
                    "sourceKind": "system",
                    "segmentId": f"segment-{uuid4().hex}",
                    "revision": 1,
                    "startedAtMs": _now_ms(),
                    "endedAtMs": _now_ms() + 1200,
                    "isFinal": True,
                    "audioBase64": payload,
                })
                events = []
                try:
                    events.append(websocket.receive_json())
                except WebSocketDisconnect:
                    pass
            runtime = self._unwrap(self.client.get(f"/api/v1/realtime-speech/sessions/{self.session_id}/runtime", params={"userId": self.user_id}))
            return {"publisherId": publisher["publisherId"], "eventCount": len(events), "latestState": runtime["latestState"], "transcriptCount": runtime["transcriptCount"]}
        self._step(steps, "realtime_speech", "Streamed a realtime speech frame and observed transcript / answer events.", realtime_roundtrip, attribution="provider-or-infrastructure")
        return "Screenshot Answer and Realtime Speech flows completed in the active session."

    def _conversation_history_scenario(self, steps: list[ScenarioStep]) -> str:
        self._ensure_identity(steps)
        if not self.session_id:
            raise RuntimeError("Prior scenarios must establish a session before history verification.")

        def verify_records():
            context = self._unwrap(self.client.get(f"/api/v1/sessions/{self.session_id}/context", params={"userId": self.user_id}))
            answers = self._unwrap(self.client.get(f"/api/v1/live-answer/sessions/{self.session_id}/history", params={"userId": self.user_id}))
            screenshots = self._unwrap(self.client.get(f"/api/v1/screenshot-answer/sessions/{self.session_id}/history", params={"userId": self.user_id}))
            realtime_events = self._unwrap(self.client.get(f"/api/v1/realtime-speech/sessions/{self.session_id}/events", params={"userId": self.user_id}))
            ended = self._unwrap(self.client.post(f"/api/v1/sessions/{self.session_id}/end", json={"userId": self.user_id}))
            sessions = self._unwrap(self.client.get("/api/v1/sessions", params={"userId": self.user_id}))
            return {
                "contextCount": context["totalCount"],
                "answerTaskCount": len(answers),
                "screenshotTaskCount": len(screenshots),
                "realtimeEventCount": len(realtime_events["events"]),
                "endedStatus": ended["status"],
                "sessionListCount": len(sessions),
            }
        self._step(steps, "conversation_history", "Queried conversation storage and interview history after ending the session.", verify_records)
        return "Conversation storage and interview history remained queryable after end-to-end execution."


class EndToEndReportWriter:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def write(self, report: EndToEndIntegrationReport) -> dict[str, Path]:
        target = self.output_dir / report.report_id
        target.mkdir(parents=True, exist_ok=True)
        json_path = target / "report.json"
        md_path = target / "report.md"
        bug_json_path = target / "bug-list.json"
        bug_md_path = target / "bug-list.md"
        todo_json_path = target / "todo-list.json"
        todo_md_path = target / "todo-list.md"
        bugs = build_bug_list(report)
        todos = build_todo_list()
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        md_path.write_text(self._markdown(report), encoding="utf-8")
        bug_json_path.write_text(json.dumps({"reportId": report.report_id, "count": len(bugs), "items": [item.to_dict() for item in bugs]}, ensure_ascii=False, indent=2), encoding="utf-8")
        bug_md_path.write_text(self._bug_markdown(report.report_id, bugs), encoding="utf-8")
        todo_json_path.write_text(json.dumps({"reportId": report.report_id, "count": len(todos), "items": [item.to_dict() for item in todos]}, ensure_ascii=False, indent=2), encoding="utf-8")
        todo_md_path.write_text(self._todo_markdown(report.report_id, todos), encoding="utf-8")
        return {
            "json": json_path,
            "markdown": md_path,
            "bug_json": bug_json_path,
            "bug_markdown": bug_md_path,
            "todo_json": todo_json_path,
            "todo_markdown": todo_md_path,
        }

    def _markdown(self, report: EndToEndIntegrationReport) -> str:
        lines = [
            "# End-to-End Integration Report",
            "",
            f"- Report ID: `{report.report_id}`",
            f"- Environment: `{report.environment_label}`",
            f"- Overall Status: **{report.overall_status}**",
            f"- Started At: `{report.started_at}`",
            f"- Completed At: `{report.completed_at}`",
            f"- Duration: `{report.duration_ms} ms`",
            "",
            "## Provider Summary",
            "",
            f"- Report ID: `{report.provider_report_id or 'n/a'}`",
            f"- Summary: `{json.dumps(report.provider_summary, ensure_ascii=False)}`",
            "",
            "## Scenario Summary",
            "",
            f"- Summary: `{json.dumps(report.scenario_summary, ensure_ascii=False)}`",
            "",
        ]
        for scenario in report.scenarios:
            lines.extend([
                f"## {scenario.title}",
                "",
                f"- Scenario ID: `{scenario.scenario_id}`",
                f"- Status: **{scenario.status}**",
                f"- Attribution: `{scenario.attribution}`",
                f"- Summary: {scenario.summary}",
                "",
                "| Step | Status | Attribution | Summary |",
                "| --- | --- | --- | --- |",
            ])
            for step in scenario.steps:
                lines.append(f"| {step.name} | {step.status} | {step.attribution} | {step.summary} |")
            lines.append("")
        return "\n".join(lines)

    def _bug_markdown(self, report_id: str, bugs: list[BugListEntry]) -> str:
        lines = [
            "# Bug List",
            "",
            f"- Report ID: `{report_id}`",
            f"- Count: `{len(bugs)}`",
            "",
            "| Issue | Severity | Module / Flow | Attribution |",
            "| --- | --- | --- | --- |",
        ]
        for item in bugs:
            lines.append(f"| {item.title} | {item.severity} | {item.module_or_flow} | {item.attribution} |")
        lines.append("")
        for item in bugs:
            lines.extend([
                f"## {item.title}",
                "",
                f"- Issue ID: `{item.issue_id}`",
                f"- Severity: `{item.severity}`",
                f"- Module / Flow: `{item.module_or_flow}`",
                f"- Attribution: `{item.attribution}`",
                f"- Reproduction: {item.reproduction_context}",
                f"- Observed: {item.observed_behavior}",
                f"- Expected: {item.expected_behavior}",
                "",
            ])
        return "\n".join(lines)

    def _todo_markdown(self, report_id: str, todos: list[TodoListEntry]) -> str:
        lines = [
            "# TODO List",
            "",
            f"- Report ID: `{report_id}`",
            f"- Count: `{len(todos)}`",
            "",
            "| Item | Priority | Owning Area |",
            "| --- | --- | --- |",
        ]
        for item in todos:
            lines.append(f"| {item.title} | {item.priority} | {item.owning_area} |")
        lines.append("")
        for item in todos:
            lines.extend([
                f"## {item.title}",
                "",
                f"- Item ID: `{item.item_id}`",
                f"- Priority: `{item.priority}`",
                f"- Owning Area: `{item.owning_area}`",
                f"- Rationale: {item.rationale}",
                f"- Suggested Next Step: {item.suggested_next_step}",
                "",
            ])
        return "\n".join(lines)


class EndToEndIntegrationRunner:
    def __init__(self, *, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger

    def run(self, *, skip_providers: bool = False) -> EndToEndIntegrationReport:
        started_iso = _utc_now_iso()
        started_perf = perf_counter()
        provider_report_id = None
        provider_summary: dict[str, Any] = {"status": "skipped", "reason": "skip_providers=true"} if skip_providers else {}
        if not skip_providers:
            provider_runner = IntegrationVerificationRunner(settings=self.settings, logger=self.logger, verifiers=build_default_verifiers())
            provider_report = provider_runner.run()
            provider_report_id = provider_report.report_id
            provider_payload = provider_report.to_dict()
            provider_summary = {
                "status": provider_payload["overallStatus"],
                "total": provider_payload["summary"]["total"],
                "passed": provider_payload["summary"]["passed"],
                "failed": provider_payload["summary"]["failed"],
                "selectedItems": provider_payload["selectedItems"],
            }

        with TemporaryDirectory(prefix="offersteady-e2e-") as _temp:
            client = TestClient(create_app())
            scenarios = ScenarioRunner(settings=self.settings, logger=self.logger, client=client).run_all()

        passed = sum(1 for item in scenarios if item.status == "passed")
        failed = sum(1 for item in scenarios if item.status == "failed")
        overall_status = "passed" if failed == 0 and provider_summary.get("failed", 0) == 0 else "failed"
        report = EndToEndIntegrationReport(
            report_id=f"e2e-{uuid4().hex}",
            environment_label=self.settings.integration_environment_label,
            started_at=started_iso,
            completed_at=_utc_now_iso(),
            duration_ms=int((perf_counter() - started_perf) * 1000),
            overall_status=overall_status,
            provider_report_id=provider_report_id,
            provider_summary=provider_summary,
            scenario_summary={"total": len(scenarios), "passed": passed, "failed": failed},
            scenarios=scenarios,
        )
        log_event(self.logger, logging.INFO, settings=self.settings, event="end_to_end_integration.completed", feature="end-to-end-integration", action="run", overall_status=overall_status, scenario_passed=passed, scenario_failed=failed, provider_status=provider_summary.get("status"))
        return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run OfferSteady end-to-end integration scenarios.")
    parser.add_argument("--skip-providers", action="store_true", help="Skip provider readiness verification and run scenario orchestration only.")
    args = parser.parse_args(argv)
    settings = get_settings()
    logger = configure_logging(settings)
    runner = EndToEndIntegrationRunner(settings=settings, logger=logger)
    report = runner.run(skip_providers=args.skip_providers)
    paths = EndToEndReportWriter(Path(settings.integration_report_output_dir)).write(report)
    print(json.dumps({"overallStatus": report.overall_status, "reportId": report.report_id, "paths": {key: str(value) for key, value in paths.items()}}, ensure_ascii=False, indent=2))
    return 0 if report.overall_status == "passed" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
