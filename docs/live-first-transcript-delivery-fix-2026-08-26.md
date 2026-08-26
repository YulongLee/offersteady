# 首句话实时交付延迟修复（2026-08-26）

## 范围

本次仅修复网页首次实时订阅和多标签页领导权交接。桌面伴随助手、系统音频采集、WebSocket 音频、Qwen Realtime ASR、问题识别、回答生成、积分和支付保持不变。

## 实现

- 同一浏览器的隐藏领导页会立即释放实时订阅；可见跟随页收到释放后立即接管。`visibilitychange`、`pagehide` 和 `pageshow` 共同覆盖后台、冻结与 BFCache 恢复。
- SSE 返回成功响应后必须在 2 秒内解析到首个权威 `snapshot`。超时会取消 reader，记录不含正文的 `first-snapshot-timeout` 指标，并进入恢复。
- 首流失败后只请求一次现有聚合 `snapshot`。恢复成功会重置退避并立即重建 SSE；恢复失败继续使用 0/2/4/8/15 秒非重叠退避。
- 健康 SSE 期间仍为零定时字幕刷新；游标、字幕 revision 和 final 状态继续单调归并。

## 验证

- 聚焦 Web 回归覆盖隐藏领导者释放、立即接管、资格恢复、timer 清理、首快照超时、reader 取消、指标分类和连续恢复。
- Backend 契约测试允许新的内容无关超时原因，同时继续拒绝正文进入指标。
- 发布门禁包括完整 Web/Backend 测试、Web 类型检查、生产构建清单、OpenSpec strict、公开健康检查和部署后错误日志。

## 回滚

该变更没有数据库迁移，也不改变 Redis 数据结构。生产发布前保留 Backend 和 Web 回滚镜像；若出现 SSE 连接放大、页面状态回退或首快照误超时，可同时或独立恢复旧 Web/Backend。Desktop、PostgreSQL、Redis、Admin 和 Analytics 无需回滚。
