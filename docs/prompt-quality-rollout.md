# Prompt quality rollout

Chat候选版本为v4，截图候选版本为v2。发布前运行后端Prompt测试和合成评测，编造、来源隔离、隐私和完整代码答案不得回归。只记录模板ID、版本、策略、来源数量、长度桶、首字与完成耗时、状态和安全错误码，不记录原始Prompt、问题、回答、资料、截图或转录。

Chat回滚设置`OFFERSTEADY_CHAT_PROMPT_TEMPLATE_PATH=ai/prompts/chat-service/system-v3.md`与`OFFERSTEADY_CHAT_PROMPT_VERSION=v3`。截图回滚设置`OFFERSTEADY_SCREENSHOT_PROMPT_TEMPLATE_PATH=ai/prompts/screenshot-answer/system-v1.md`与`OFFERSTEADY_SCREENSHOT_PROMPT_VERSION=v1`。重启后端后，新任务应记录旧版本；现有会话和资料无需迁移。
