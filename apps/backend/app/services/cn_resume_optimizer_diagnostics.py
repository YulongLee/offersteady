"""Fixed, private-content-free failure labels and owner-facing explanations.

Only labels from this module may be persisted. Input dictionaries are never
returned directly, so extra fields or forged stage/reason pairs cannot escape.
Financial state is deliberately not inferred here; the service appends any
refund statement only after the repository has committed the release.
"""
from __future__ import annotations


_RETRY = "原简历无需重新上传，请稍后重试。"
_FORMAT = "AI 返回的结果格式不完整，未能生成优化稿。" + _RETRY
_FACT = "AI 改写未通过原文事实检查，已停止生成。" + _RETRY
_EVIDENCE = "AI 返回的依据与原简历或岗位描述不一致，已停止生成。" + _RETRY

# Values and messages are constants, never derived from documents or exceptions.
_FAILURES = {
    "provider_timeout": ("transport", "AI 服务响应超时，请稍后重试，原简历无需重新上传。"),
    "provider_http_error": ("transport", "AI 服务暂时不可用，请稍后重试，原简历无需重新上传。"),
    "provider_unconfigured": ("transport", "简历优化的 AI 服务尚未就绪，请联系支持人员检查服务配置。"),
    "response_too_large": ("transport", "AI 返回的结果超过处理上限，未能生成优化稿。" + _RETRY),
    "response_encoding_invalid": ("envelope", _FORMAT),
    "provider_envelope_invalid": ("envelope", _FORMAT),
    "provider_finish_length": ("envelope", "AI 返回的结果被截断，未能生成完整优化稿。" + _RETRY),
    "provider_finish_invalid": ("envelope", "AI 未正常完成生成，本次没有可用优化稿。" + _RETRY),
    "content_encoding_invalid": ("parsing", _FORMAT),
    "content_json_invalid": ("parsing", _FORMAT),
    "content_json_ambiguous": ("parsing", "AI 返回的结果存在重复字段，未能可靠读取。" + _RETRY),
    "review_schema_invalid": ("schema", _FORMAT),
    "dimension_set_invalid": ("schema", "AI 返回的评分维度不完整，未能生成可靠评估。" + _RETRY),
    "evidence_quote_missing": ("evidence", _EVIDENCE),
    "role_evidence_missing": ("evidence", _EVIDENCE),
    "explanation_language_invalid": ("language", "AI 未按要求提供中文说明，未能生成可用结果。" + _RETRY),
    "missing_facts_language_invalid": ("language", "AI 返回的待补充说明不符合要求，未能生成可用结果。" + _RETRY),
    "edit_quote_not_unique": ("evidence", "AI 返回的改写位置无法与原简历唯一对应，已停止生成。" + _RETRY),
    "fact_numbers_changed": ("facts", _FACT),
    "fact_contact_changed": ("facts", _FACT),
    "fact_english_content_added": ("facts", _FACT),
    "fact_english_content_removed": ("facts", _FACT),
    "fact_credentials_changed": ("facts", _FACT),
    "fact_dates_counts_changed": ("facts", _FACT),
    "fact_negation_changed": ("facts", _FACT),
    "fact_entities_changed": ("facts", _FACT),
    "fact_responsibility_changed": ("facts", _FACT),
    "fact_skills_changed": ("facts", _FACT),
    "edit_spans_overlap": ("draft", "AI 返回的修改位置相互重叠，未能安全合并优化稿。" + _RETRY),
    "draft_invalid": ("draft", "AI 优化稿未通过完整性检查，未能安全交付。" + _RETRY),
    "no_effective_edits": ("draft", "本次未生成可安全应用的有效修改，原简历已保留。"),
    "runtime_timeout": ("execution", "简历优化处理超时，请稍后重试，原简历无需重新上传。"),
    "runtime_interrupted": ("execution", "简历优化处理已中断，请稍后重新发起，原简历无需重新上传。"),
    "runtime_internal_error": ("execution", "简历优化处理遇到内部错误，请稍后重试；若仍失败请联系支持人员。"),
    "runtime_repository_unavailable": ("execution", "简历优化状态暂时无法处理，请稍后重试；若仍失败请联系支持人员。"),
}


def failure_diagnostic(reason: object) -> dict[str, str] | None:
    """Construct a fresh fixed pair, dropping unknown or non-string reasons."""
    if type(reason) is not str or reason not in _FAILURES:
        return None
    return {"stage": _FAILURES[reason][0], "reason": reason}


def normalize_failure_diagnostic(value: object) -> dict[str, str] | None:
    """Fail closed on unknown/extra fields and inconsistent stage/reason pairs."""
    if type(value) is not dict or value.keys() != {"stage", "reason"}:
        return None
    diagnostic = failure_diagnostic(value["reason"])
    if diagnostic is None or type(value["stage"]) is not str or value["stage"] != diagnostic["stage"]:
        return None
    return diagnostic


def error_message_for_diagnostic(value: object) -> str | None:
    diagnostic = normalize_failure_diagnostic(value)
    return _FAILURES[diagnostic["reason"]][1] if diagnostic is not None else None
