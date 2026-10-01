from __future__ import annotations

import asyncio
import json
import re

import httpx
from pydantic import ValidationError

from app.core.config import REPO_ROOT, Settings
from app.core.errors import DomainRequestError
from app.ports.document_repository import DocumentRepository
from app.ports.storage import FileStoragePort
from app.schemas.mock_interview import MockQuestion, MockReport
from app.services.material_object_keys import MaterialObjectKeyFactory
from app.services.mock_interview_rounds import MockRound


class MockGenerationUnavailable(RuntimeError):
    pass


class MockResumeReader:
    """Reads only the explicitly selected parsed version; never stores a copy."""
    max_characters = 12_000
    max_artifact_bytes = 2 * 1024 * 1024

    def __init__(self, settings: Settings, documents: DocumentRepository, storage: FileStoragePort):
        self.documents = documents
        self.storage = storage
        self.keys = MaterialObjectKeyFactory(settings)

    def read(self, *, user_id: str, document_id: str, version_id: str) -> str:
        doc = self.documents.get_by_id(document_id)
        if doc is None or doc.owner_user_id != user_id:
            raise DomainRequestError("mock-interview", "resume", "简历不存在或无权访问。", 404)
        if (doc.document_kind != "resume" or doc.status != "ready" or doc.index_state != "indexed"
                or doc.deleted_at_ms is not None or not version_id or doc.document_version_id != version_id):
            raise DomainRequestError("mock-interview", "resume", "请重新选择已就绪的简历版本。", 409)
        key = self.keys.processed_artifact_key(owner_user_id=user_id, document_kind="resume",
            document_id=document_id, document_version_id=version_id, artifact_kind="normalized_markdown")
        try:
            content = self.storage.load_object_bytes(object_key=key)
            if not content or len(content) > self.max_artifact_bytes:
                raise ValueError("artifact size")
            text = content.decode("utf-8").strip()
        except Exception:
            raise DomainRequestError("mock-interview", "resume", "简历解析正文不可读，请重新处理资料。", 409) from None
        text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[已省略邮箱]", text)
        text = re.sub(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)", "[已省略手机号]", text)
        if not text:
            raise DomainRequestError("mock-interview", "resume", "简历正文为空，请重新处理资料。", 409)
        return text[:self.max_characters] + ("\n[简历上下文已截断]" if len(text) > self.max_characters else "")


class MockInterviewGenerator:
    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport
        self._slots = asyncio.Semaphore(settings.mock_interview_provider_concurrency)
        root = REPO_ROOT / "ai/prompts/mock-interview"
        if settings.product_edition == "global":
            root /= "en"
        self.prompts = {name: (root / f"{name}.md").read_text(encoding="utf-8") for name in ("question", "report")}
        self.answer_structure = (root / "answer-structure.md").read_text(encoding="utf-8").strip()

    async def _generate(self, kind: str, *, resume: str, target_role: str, rounds: tuple[MockRound, ...]) -> dict:
        if len(rounds) > 10 or len(resume) > 12_100 or len(target_role) > 120:
            raise MockGenerationUnavailable("模拟面试上下文超过限制。")
        if not self.settings.chat_qwen_api_key or not self.settings.chat_qwen_base_url:
            raise MockGenerationUnavailable("模拟面试文本模型尚未配置。")
        context = {"resume": resume, "target_role": target_role,
                   "rounds": [{"question_id": r.question_id, "question": r.question, "answer": r.answer} for r in rounds],
                   "remaining_questions": 10 - len(rounds)}
        try:
            async with asyncio.timeout(self.settings.mock_interview_provider_timeout_seconds):
                async with self._slots:
                    async with httpx.AsyncClient(transport=self.transport, timeout=40) as client:
                        response = await client.post(
                            self.settings.chat_qwen_base_url.rstrip("/") + "/chat/completions",
                            headers={"Authorization": f"Bearer {self.settings.chat_qwen_api_key}"},
                            json={"model": self.settings.chat_qwen_model, "stream": False, "enable_thinking": False,
                                  "max_tokens": 600 if kind == "question" else 6000,
                                  "messages": [{"role": "system", "content": self.prompts[kind]},
                                               {"role": "user", "content": json.dumps(context, ensure_ascii=False)}]},
                        )
                        response.raise_for_status()
                        if len(response.content) > 128 * 1024:
                            raise ValueError("oversized model response")
                        payload = response.json()
                        choice = payload["choices"][0]
                        if choice.get("finish_reason") != "stop":
                            raise ValueError("incomplete model response")
                        content = choice["message"]["content"].strip()
                        if content.startswith("```json\n") and content.endswith("```"):
                            content = content[8:-3].strip()
                        result = json.loads(content)
                        if not isinstance(result, dict):
                            raise ValueError("invalid structured output")
                        return result
        except (httpx.HTTPError, TimeoutError, ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise MockGenerationUnavailable("模拟面试生成暂时不可用，请在本场重试。") from None

    async def question(self, *, resume: str, target_role: str, rounds: tuple[MockRound, ...]) -> MockQuestion:
        if len(rounds) >= 10 or any(not r.answer for r in rounds):
            raise MockGenerationUnavailable("请完成当前回答，或查看本场报告。")
        payload = await self._generate("question", resume=resume, target_role=target_role, rounds=rounds)
        try:
            question = MockQuestion.model_validate(payload)
            # One published question per turn. A model can append an unsolicited
            # follow-up despite the prompt; retain only its first full question.
            first_end = re.search(r"[？?]", question.question)
            if first_end:
                question.question = question.question[:first_end.end()]
            if any(r.question == question.question for r in rounds):
                raise ValueError("duplicate question")
            return question
        except (ValidationError, ValueError):
            raise MockGenerationUnavailable("出题格式异常或内容重复，请重试。") from None

    async def report(self, *, resume: str, target_role: str, rounds: tuple[MockRound, ...]) -> MockReport:
        answered = tuple(r for r in rounds if r.answer and r.answer.strip())
        if not answered:
            return MockReport(summary="No confirmed answers were submitted. There is insufficient evidence to assign a score." if self.settings.product_edition == "global" else "本场没有已确认的有效回答，证据不足，暂不评分。")
        payload = await self._generate("report", resume=resume, target_role=target_role, rounds=answered)
        try:
            report = MockReport.model_validate(payload)
            expected = {r.question_id: r.answer for r in answered}
            if report.dimensions is None or len(report.feedback) != len(expected):
                raise ValueError("incomplete feedback")
            if {f.question_id for f in report.feedback} != set(expected):
                raise ValueError("unknown or duplicate round")
            if any(f.answer_quote not in expected[f.question_id] for f in report.feedback):
                raise ValueError("fabricated answer evidence")
            if any(not item.strip() or len(item) > 600 for item in report.practice_priorities):
                raise ValueError("invalid priority")
            # A fluent first-person example can invent unprovided achievements
            # even when its evidence quote is valid. Only build sample answers
            # from a literal user quote and explicit, unfilled evidence slots.
            # The model's per-question strengths/improvements remain contextual.
            for feedback in report.feedback:
                feedback.suggestion = self.answer_structure.format(answer_quote=feedback.answer_quote)
            if len(answered) < 10:
                prefix = f"Partial report ({len(answered)}/10 questions answered). " if self.settings.product_edition == "global" else f"部分报告（已回答 {len(answered)}/10 题）。"
                report.summary = prefix + report.summary
            return report
        except (ValidationError, ValueError):
            raise MockGenerationUnavailable("报告证据校验未通过，请重试；本次未生成可信评分。") from None
