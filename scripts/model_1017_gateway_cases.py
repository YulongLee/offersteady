"""Synthetic adapter probes; no CLI, persistence, dependencies or raw output.

A reviewed caller may exec this source in a pinned regional image, then iterate
run_gateway_cases(candidate_settings). Model credentials remain inside the
existing adapters. Only fixed safe metadata is returned. The helper neither
changes global httpx behavior nor changes supplied Settings or feature flags.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import random
import re
from time import monotonic


TARGET_MODEL = "deepseek-v4.1-flash-1017"
_SAFE_ERRORS = {
    "chat_provider_unavailable", "chat_provider_rate_limited", "chat_provider_auth_failed",
    "chat_provider_request_rejected", "chat_config_missing", "chat_provider_invalid_response",
    "web_search_not_configured", "web_search_auth_failed", "web_search_rate_limited",
    "web_search_provider_rejected", "web_search_empty_result", "web_search_provider_unavailable",
}


def _result(operation, started, checks, first_text_ms=None, error=None, reason=None):
    import httpx
    checks = {key: bool(value) for key, value in checks.items()}
    passed = bool(checks) and all(checks.values()) and error is None and reason is None
    code = getattr(error, "code", None)
    if passed:
        error_type, diagnostic = None, None
    elif reason in _SAFE_ERRORS:
        error_type, diagnostic = "provider_unavailable", reason
    elif isinstance(error, (TimeoutError, httpx.TimeoutException)):
        error_type, diagnostic = "provider_timeout", "bounded_request_timeout"
    elif isinstance(error, (ImportError, ModuleNotFoundError)):
        error_type, diagnostic = "adapter_unavailable", "runtime_adapter_unavailable"
    elif error is not None:
        error_type = "adapter_error"
        diagnostic = code if type(code) is str and code in _SAFE_ERRORS else "adapter_request_failed"
    else:
        error_type, diagnostic = "validation_failed", "synthetic_checks_failed"
    return {
        "operation": operation, "model": TARGET_MODEL, "syntheticOnly": True,
        "passed": passed, "errorType": error_type, "diagnosticReason": diagnostic,
        "seconds": round(monotonic() - started, 3), "firstTextMs": first_text_ms,
        "checks": checks,
    }


def _locale(settings):
    return "en-US" if settings.product_edition == "global" else "zh-CN"


def _language_ok(text, locale):
    from app.interview_languages import output_language_violation
    return bool(text.strip()) and not output_language_violation(text, locale)


def _chat_case(settings, stage):
    from app.services.chat_service import FilePromptTemplateAdapter, InterviewPromptBuilder, QwenCompatibleGateway
    started, first_text = monotonic(), None
    operation = "chat_" + stage + ("_global" if settings.product_edition == "global" else "_cn")
    checks = {"adapterCompleted": False}
    gateway, iterator = None, None
    try:
        locale = _locale(settings)
        english = locale == "en-US"
        question = ("Why does a PostgreSQL unique constraint prevent duplicate order creation?" if english
            else "PostgreSQL的唯一约束为什么能防止重复创建订单？")
        source = ("SYNTHETIC: The candidate used PostgreSQL unique constraints for order identifiers. No performance metrics are available."
            if english else "合成示例：候选人只确认使用PostgreSQL唯一约束限制订单业务编号，没有实际性能指标。")
        system, config = FilePromptTemplateAdapter(settings).load_stage_prompt(stage, locale)
        prompt = InterviewPromptBuilder().build(question=question, session_title="Synthetic adapter check",
            system_prompt=system,
            conversation_history=(["Quick answer anchor: A unique constraint rejects duplicate business keys."]
                if english else ["本轮简要回答锚点：唯一约束会拒绝重复业务编号。"])
                if stage == "detail" else [],
            session_material_context_text=source, retrieval_context_text="", prompt_config=config)
        requests = []
        gateway = QwenCompatibleGateway(settings)

        def capture(request):
            payload = json.loads(request.content)
            requests.append({"model": payload.get("model") == TARGET_MODEL,
                "nonThinking": payload.get("enable_thinking") is False,
                "streaming": payload.get("stream") is True})

        gateway._client().event_hooks.setdefault("request", []).append(capture)
        iterator = gateway.stream_generate(question=question, prompt=prompt, attempt=0)
        chunks, length = [], 0
        for chunk in iterator:
            if chunk.text and first_text is None:
                first_text = round((monotonic() - started) * 1000, 2)
            length += len(chunk.text)
            if length > 24000:
                raise ValueError("synthetic output bound")
            chunks.append(chunk)
        text = "".join(chunk.text for chunk in chunks)
        checks = {
            "adapterCompleted": True,
            "oneCandidateNonThinkingStream": len(requests) == 1 and all(requests[0].values()),
            "providerStop": bool(chunks) and chunks[-1].is_final and chunks[-1].provider_finish_reason == "stop",
            "nonemptyAnswer": bool(text.strip()), "sessionLanguage": _language_ok(text, locale),
            "syntheticFactsRetained": "PostgreSQL" in text and ("unique" in text.lower() if english else "唯一" in text),
            "noInventedPercentage": not re.search(r"\d+(?:\.\d+)?\s*[%％]", text),
        }
        if stage == "quick":
            checks["normalizedQuestionFirst"] = bool(re.match(
                r"^\s*<normalized_question>[^<]+</normalized_question>\s*\S", text, flags=re.S))
        return _result(operation, started, checks, first_text)
    except Exception as error:
        return _result(operation, started, checks, first_text, error)
    finally:
        if iterator is not None:
            iterator.close()
        if gateway is not None:
            gateway.close()


def _image(settings, ordinal, lines):
    from PIL import Image, ImageDraw, ImageFont
    from app.ports.screenshot_answer import PreparedScreenshotImage
    from app.services.screenshot_answer_service import ScreenshotAnswerService
    width, height = 1280, 720
    noise = random.Random("synthetic-model-1017-" + str(ordinal)).randbytes(width * height)
    background = Image.frombytes("L", (width, height), noise).point(lambda p: 240 + p % 16).convert("RGB")
    draw = ImageDraw.Draw(background)
    font = ImageFont.load_default(size=64)
    draw.text((48, 30), "SYNTHETIC TEST", fill=(0, 0, 0), font=ImageFont.load_default(size=36))
    for index, line in enumerate(lines):
        draw.text((48, 130 + 125 * index), line, fill=(0, 0, 0), font=font)
    output = io.BytesIO()
    background.save(output, format="PNG")
    original = output.getvalue()
    service = object.__new__(ScreenshotAnswerService)
    service.settings = settings
    filename, content_type, payload = service._optimize_screenshot_for_vision(
        filename=f"synthetic-page-{ordinal:02}.png", content_type="image/png", payload=original)
    return PreparedScreenshotImage(image_id=f"synthetic-image-{ordinal}", session_id="synthetic-adapter-only",
        owner_user_id="synthetic-adapter-only", filename=filename, content_type=content_type,
        object_key="synthetic-no-storage", size_bytes=len(payload), ordinal=ordinal,
        content_sha256=hashlib.sha256(payload).hexdigest(), byte_length=len(payload), payload_bytes=payload)


def _sections_ok(text, locale):
    quick, detail = ("Quick Answer", "Detailed Answer") if locale == "en-US" else ("简要回答", "详细回答")
    first, second = text.find(quick), text.find(detail)
    divider = re.search(r"(?m)^\s*---\s*$", text)
    return first >= 0 and second > first and divider is not None and first < divider.start() < second


def _plain_markdown(value):
    # Preserve token boundaries: 4**2 and 7`3`19 must never become 42 or 7319.
    value = re.sub(r"\*\*|__|`", " ", value)
    return re.sub(r"(?m)^\s*#{1,6}\s*", "", value).strip()


def _unwrap_outer(value):
    value = re.sub(r"^\s*#{1,6}\s+", "", value).strip()
    for _ in range(3):
        for wrapper in ("**", "__", "`"):
            if (len(value) > 2 * len(wrapper) and value.count(wrapper) == 2
                    and value.startswith(wrapper) and value.endswith(wrapper)):
                value = value[len(wrapper):-len(wrapper)].strip()
                break
        else:
            break
    return value


def _normalize_conclusion_line(value):
    value = _unwrap_outer(value)
    label = r"(?:最终答案|最终结果|计算结果|拼接结果|答案|结果|(?:the\s+)?(?:final\s+)?(?:answer|result))"
    # A complete wrapped label may be unwrapped, but internal numeric fragments
    # may not. Numeric wrappers are handled only around the entire result below.
    return re.sub(r"^(\*\*|__|`)(" + label + r"[:：]?)\1", lambda m: m.group(2), value, flags=re.I)


def _numeric_result(value):
    value = value.strip()
    if value.endswith(("。", ".", "!")):
        value = value[:-1].rstrip()
    value = _unwrap_outer(value)
    return value if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value) else None


def _synthetic_conclusion(text, locale, requires_sections):
    """Parse one affirmative conclusion under the probe's synthetic format."""
    if not requires_sections:
        lines = [_normalize_conclusion_line(line) for line in text.splitlines()]
        answers = [line for line in lines if re.match(r"^Answer\s*:", line, flags=re.I)]
        if len(answers) != 1:
            return None
        return _numeric_result(re.sub(r"^Answer\s*:\s*", "", answers[0], count=1, flags=re.I))
    if not _sections_ok(text, locale):
        return None
    quick = "Quick Answer" if locale == "en-US" else "简要回答"
    divider = re.search(r"(?m)^\s*---\s*$", text)
    body = text[text.find(quick) + len(quick):divider.start()]
    header_end, newline, remainder = body.partition("\n")
    if newline and re.fullmatch(r"\s*(?:\*\*|__|`)?\s*", header_end):
        body = remainder
    paragraph = _normalize_conclusion_line(re.split(r"\n\s*\n", body.strip(), maxsplit=1)[0])
    prefix = (r"(?:最终答案|最终结果|计算结果|拼接结果|答案|结果|"
        r"(?:the\s+)?(?:final\s+)?(?:answer|result))")
    value = re.sub(r"^" + prefix + r"\s*(?:是|为|is|[:：=])?\s*", "", paragraph, count=1, flags=re.I)
    return _numeric_result(value)


def _correct_image_result(text, expected, locale, requires_sections=True):
    """Require a unique affirmative conclusion, not a number mention."""
    conclusion = _synthetic_conclusion(text, locale, requires_sections)
    if conclusion not in {expected, "+" + expected}:
        return False
    whole = _plain_markdown(text)
    number = r"[+-]?\d+(?:\.\d+)?"
    # A later explicit opposite conclusion invalidates a correct first line.
    explicit = (r"(?:最终答案|最终结果|正确答案|正确结果|计算结果|拼接结果|拼接数字|正确序列|答案|结果|"
        r"(?:the\s+)?(?:final\s+|correct\s+)?(?:answer|result)|concatenated\s+(?:number|digits)|sequence)"
        r"\s*(?:应为|应该是|是|为|is|[:：=])\s*(" + number + r")(?!\d|\.\d)")
    if any(match.group(1) not in {expected, "+" + expected} for match in re.finditer(explicit, whole, flags=re.I)):
        return False
    token = r"(?<![\d.+-])" + re.escape(expected) + r"(?!\d|\.\d)"
    if (re.search(r"(?:不是|并非|不等于|非|not\s+)\s*" + token, whole, flags=re.I)
            or re.search(token + r"\s*(?:不对|不正确|是错|错误|is\s+(?:incorrect|wrong|not\s+correct))", whole, flags=re.I)):
        return False
    if expected == "42":
        equations = re.finditer(r"17\s*\+\s*25\s*=\s*(" + number + r")(?!\d|\.\d)", whole)
        if any(match.group(1) not in {expected, "+" + expected} for match in equations):
            return False
    return True


def _vision_case(settings, four):
    from app.services.screenshot_answer_service import OpenAICompatibleVisionGateway
    started, first_text = monotonic(), None
    operation = ("vision_four_ordered" if four else "vision_single_arithmetic") + (
        "_global" if settings.product_edition == "global" else "_cn")
    checks, iterator = {"adapterCompleted": False}, None
    try:
        locale = _locale(settings)
        gateway = OpenAICompatibleVisionGateway(settings)
        loaded_system = gateway._load_system_prompt(locale)
        requires_sections = settings.product_edition == "cn" or (
            "Quick Answer" in loaded_system and "Detailed Answer" in loaded_system)
        if four:
            images = [_image(settings, index, [f"PAGE {index} OF 4", "DIGIT", str(value)])
                for index, value in enumerate((7, 3, 1, 9), start=1)]
            instruction = ("Read all images in capture order. Concatenate their DIGIT values without separators and report the resulting number."
                if locale == "en-US" else "按截图提交顺序阅读全部图片，将各页DIGIT值无分隔拼接，给出这个数，并使用规定的双段回答格式。")
            expected = "7319"
        else:
            images = [_image(settings, 1, ["Solve the arithmetic:", "17 + 25 = ?", "Give the numeric result."])]
            instruction = ("Solve the arithmetic visible in the image."
                if locale == "en-US" else "计算图片中算式的结果，使用规定的双段回答格式。")
            expected = "42"
        if requires_sections:
            instruction += (" Use Quick Answer, then ---, then Detailed Answer. In Quick Answer, make the first paragraph only the final numeric result, optionally prefixed by Answer:. Put explanations in Detailed Answer."
                if locale == "en-US" else "简要回答的第一段只写一个最终结果数字，可加答案前缀；解释放在详细回答中。")
        else:
            instruction += " Include exactly one standalone line 'Answer: <number>' with only the final numeric result. Put any explanation in other paragraphs."
        original_payload, original_extract = gateway._request_payload, gateway._extract_stream_text
        requests, endings = [], []

        def capture_payload(**kwargs):
            payload = original_payload(**kwargs)
            content = payload["messages"][-1]["content"]
            urls = [part["image_url"]["url"] for part in content if part.get("type") == "image_url"]
            expected_urls = ["data:" + image.content_type + ";base64," + base64.b64encode(image.payload_bytes).decode("ascii") for image in images]
            requests.append({"candidateModel": payload.get("model") == TARGET_MODEL,
                "nonThinking": payload.get("enable_thinking") is False, "streaming": payload.get("stream") is True,
                "allImagesInOrder": urls == expected_urls, "oneOrderedMessage": len(urls) == len(images)})
            return payload

        def capture_extract(line):
            raw = line[5:].strip() if line.startswith("data:") else line.strip()
            if raw and raw != "[DONE]":
                try:
                    body = json.loads(raw)
                    for choice in body.get("choices", []):
                        if isinstance(choice, dict) and choice.get("finish_reason") is not None:
                            endings.append(choice.get("finish_reason"))
                except (ValueError, TypeError, AttributeError):
                    pass
            return original_extract(line)

        gateway._request_payload, gateway._extract_stream_text = capture_payload, capture_extract
        iterator = gateway.stream_analyze(session_id="synthetic-adapter-only", instruction=instruction,
            images=images, attempt=0, interview_language=locale)
        parts, length = [], 0
        for text in iterator:
            if text and first_text is None:
                first_text = round((monotonic() - started) * 1000, 2)
            length += len(text)
            if length > 24000:
                raise ValueError("synthetic output bound")
            parts.append(text)
        text = "".join(parts)
        checks = {"adapterCompleted": True,
            "oneCandidateOrderedNonThinkingStream": len(requests) == 1 and all(requests[0].values()),
            "existingJpegOptimization": all(image.content_type == "image/jpeg" and image.payload_bytes.startswith(b"\xff\xd8") for image in images),
            "providerStop": bool(endings) and endings[-1] == "stop",
            "nonemptyAnswer": bool(text.strip()), "sessionLanguage": _language_ok(text, locale),
            "existingOutputContract": _sections_ok(text, locale) if requires_sections else _language_ok(text, locale),
            "syntheticAnswerContract": _synthetic_conclusion(text, locale, requires_sections) is not None,
            "correctImageOnlyResult": _correct_image_result(text, expected, locale, requires_sections),
            "resultNotLeakedInInstruction": expected not in instruction,
        }
        return _result(operation, started, checks, first_text)
    except Exception as error:
        return _result(operation, started, checks, first_text, error)
    finally:
        if iterator is not None:
            iterator.close()


def _web_case(settings):
    from app.services.web_search_gateway import DashScopeWebSearchGateway
    started = monotonic()
    checks, gateway = {"actualSearchSucceeded": False}, None
    try:
        quiet = logging.Logger("synthetic-model-1017-web", level=logging.CRITICAL + 1)
        quiet.disabled, quiet.propagate = True, False
        gateway = DashScopeWebSearchGateway(settings, logger=quiet)
        requests, tool_execution = [], []

        def capture(request):
            payload = json.loads(request.content)
            requests.append({"candidateModel": payload.get("model") == TARGET_MODEL,
                "nonThinking": payload.get("reasoning", {}).get("effort") == "none",
                "searchTool": {"type": "web_search"} in payload.get("tools", [])})

        def capture_response(response):
            # A citation alone is not proof of tool execution. Inspect only the
            # fixed execution type/status, discard all source/provider content.
            try:
                response.read()
                body = response.json()
                output = body.get("output", []) if isinstance(body, dict) else []
                completed = any(isinstance(item, dict) and item.get("type") == "web_search_call"
                    and item.get("status") in {"completed", "succeeded", "success"} for item in output)
                tool_execution.append(completed)
            except (ValueError, TypeError, AttributeError):
                tool_execution.append(False)

        gateway._client().event_hooks.setdefault("request", []).append(capture)
        gateway._client().event_hooks.setdefault("response", []).append(capture_response)
        result = gateway.answer(question="site:docs.python.org/3/tutorial/datastructures.html list.append list.extend 有什么区别？",
            system_prompt="只回答公开的Python文档事实，提供真实来源，不涉及任何候选人或用户资料。",
            user_prompt="这是合成接入测试问题。只检索 site:docs.python.org/3/tutorial/datastructures.html 这一Python官方公开页面，解释list.append与list.extend的区别，并引用该官方页面。不要使用其他域名作为来源。",
            model=TARGET_MODEL, max_tokens=settings.chat_detail_max_tokens, language="Chinese")
        lower = result.answer_text.casefold()
        executed = len(tool_execution) == 1 and tool_execution[0]
        semantics = ("append" in lower and "extend" in lower
            and any(term in lower for term in ("单个", "一个元素", "single", "one item", "one element"))
            and any(term in lower for term in ("可迭代", "逐个", "iterable", "multiple elements", "each element")))
        checks = {"actualSearchSucceeded": result.status == "succeeded" and executed,
            "webSearchExecutionCompleted": executed, "appendExtendSemantics": semantics,
            "noLocalFallbackCountedAsSearch": result.status == "succeeded" and result.safe_error_code is None,
            "oneCandidateNonThinkingSearch": len(requests) == 1 and all(requests[0].values()),
            "nonemptyAnswer": bool(result.answer_text.strip()), "sourceLinksReturned": bool(result.sources),
            "publicPythonSource": any(re.match(r"https://(?:docs\.|www\.)?python\.org/", source.url) for source in result.sources),
        }
        reason = result.safe_error_code if result.safe_error_code in _SAFE_ERRORS else None
        return _result("web_search_cn", started, checks, reason=reason)
    except Exception as error:
        return _result("web_search_cn", started, checks, error=error)
    finally:
        if gateway is not None and gateway._http_client is not None:
            gateway._http_client.close()


def run_gateway_cases(settings, operations=None):
    """Yield 5 CN or 4 Global bounded, safe adapter results sequentially.

    Global search stays disabled and is never called. No setting is changed and
    no retries are added; each provider keeps its existing timeout/token budget.
    """
    started = monotonic()
    if settings.product_edition not in {"cn", "global"} or any(getattr(settings, key, None) != TARGET_MODEL
            for key in ("chat_qwen_model", "chat_quick_model", "chat_detail_model", "screenshot_vision_model")):
        yield _result("gateway_configuration", started, {"candidateModelAndRegionConfigured": False})
        return
    suffix = "_global" if settings.product_edition == "global" else "_cn"
    cases = [("chat_quick" + suffix, lambda: _chat_case(settings, "quick")),
        ("chat_detail" + suffix, lambda: _chat_case(settings, "detail")),
        ("vision_single_arithmetic" + suffix, lambda: _vision_case(settings, False)),
        ("vision_four_ordered" + suffix, lambda: _vision_case(settings, True))]
    if settings.product_edition == "cn":
        cases.append(("web_search_cn", lambda: _web_case(settings)))
    known = {operation for operation, _ in cases}
    if operations is not None and (type(operations) not in {tuple, list} or not operations
            or any(type(operation) is not str or operation not in known for operation in operations)
            or len(set(operations)) != len(operations)):
        yield _result("gateway_configuration", started, {"requestedOperationsValid": False})
        return
    selected = known if operations is None else set(operations)
    for operation, call in cases:
        if operation in selected:
            yield call()
