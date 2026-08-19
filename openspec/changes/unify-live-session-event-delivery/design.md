## Context

活动面试当前同时依赖四类状态来源：Realtime Speech SSE 周期性发送完整快照，快答接口单独返回回答 SSE，网页对截屏请求每 200ms 查询一次，桌面助手对待处理截屏任务按 live/idle 策略轮询。历史回答接口还会在页面进入或恢复时重新水合状态。客户端虽然用 taskId、revision 和时间做单调归并，但来源之间没有共同的事件标识，仍可能重复更新、迟到覆盖或制造额外请求。

Realtime Speech Repository 已将会话事件写入 Redis Stream，并维护会话活动游标，因此本轮不新增消息中间件或数据库表，而是把它提升为跨模块的内部会话事件事实源。敏感内容仍遵循现有保存策略：不把音频或截图二进制写入事件，只记录任务状态和已有回答任务的必要展示字段。

## Goals / Non-Goals

**Goals:**

- 为转写、问题候选、显式回答和截屏任务提供有序、可续传、可去重的统一会话事件。
- 正常联网时让网页和新版桌面助手通过 SSE 被动接收变化，停止高频任务状态查询。
- 保持现有快答即时流式正文体验，同时让同一回答生命周期进入统一事件流用于恢复和跨端同步。
- 完整删除停用的自动回答执行器和内部方法，保证语音转写本身永不创建回答任务。
- 兼容已安装的旧桌面助手，并在实时流断开时提供有上限、非重叠的退避降级。

**Non-Goals:**

- 不更换 ASR、视觉或回答模型，不修改 Prompt、积分费率或资料检索逻辑。
- 不用统一事件流传输原始音频、截图二进制或模型密钥。
- 不删除现有截图 `next`、任务查询、回答 SSE 或历史接口；它们继续作为兼容和恢复接口。
- 不让识别出的面试官问题自动触发模型回答。

## Decisions

### 1. Redis 会话事件是活动会话的事实源

所有跨模块事件使用统一 envelope：`eventId`、`sessionId`、`ownerUserId`、`kind`、`payload`、`createdAtMs`，流本身提供单调 `cursor`。新增 `answer-task-updated` 和 `screenshot-capture-updated`，既有 transcript/candidate 事件保持兼容。生产环境沿用 Redis Stream，测试环境沿用内存仓库。

选择现有 Redis Stream 而不是新增 Kafka、数据库 outbox 或第三方推送，是因为当前单体后端已经可靠维护同一会话的事件和游标，能够用最小改动获得断线续传与多进程可见性。替代方案是进程内 WebSocket registry；它在多 worker 部署和重启后会丢失连接状态，因此不采用。

### 2. 会话 SSE 发送增量事件，并保留低频快照校准

首次连接发送完整 snapshot；此后按 cursor 发送新增 events，并只在需要时携带变化后的 transcript/candidate/runtime。服务端保留 keepalive 和租约校验。客户端按 eventId 去重、按 cursor 前进，并用 task revision/updatedAtMs 做同任务单调归并。历史接口只在首次进入、显式翻阅历史或实时流重连失败后执行校准，不再正常并行刷新当前状态。

选择增量事件而不是每次活动都重新拉取四份完整列表，可降低 Redis 读取、JSON 序列化和 React 重算。首次 snapshot 和恢复校准仍能处理事件保留窗口之外的断线。

### 3. 回答保留专用正文 SSE，但生命周期同时写入会话事件

快答的专用 SSE 继续承担最低延迟的正文分片交付。路由在 queued/generating/completed/failed/cancelled 更新时发布 `answer-task-updated`，payload 携带现有任务响应和触发来源 `manual`；网页统一 reducer 同时接收专用 SSE 与会话事件，利用 taskId/revision 幂等合并。语音服务不再拥有 ChatService 自动回答执行器，也不再发布旧 `answer-stream` 事件。

选择双路交付、单一 reducer，而不是立即删除专用回答 SSE，是为了不增加首字延迟并保持停止生成能力。长期可以在统一事件流支持逐分片背压后再收敛传输通道。

### 4. 截屏状态由服务端在每次状态转换时发布

创建、认领、上传受理、完成、失败和取消均发布 `screenshot-capture-updated`。事件 payload 只包含 requestId、deviceId、status、stage、updatedAtMs、安全错误信息和完成后的回答任务摘要，不包含截图原图。网页创建请求后注册 requestId waiter，由已有会话 SSE 唤醒；只有会话流不可用或超时才按 1、2、4、8 秒上限退避查询任务接口。

选择状态转换时发布而不是让 SSE 端自行扫描截图表，可以避免持续数据库查询并确保每个变化都有明确因果事件。

### 5. 新版桌面助手复用同一事件仓库的设备 SSE

新增认证的设备截屏事件端点。端点先验证 deviceId、manualCode 和 live binding，再从该 session 的统一事件流筛选目标设备的 `screenshot-capture-updated` requested 事件。桌面主进程保持一条可取消的长连接，收到 requestId 后复用现有捕获上传函数。连接失败才启动现有非重叠退避轮询；连接恢复后立即停止轮询。快捷键本机创建的请求可直接用响应中的 requestId 执行，无需再查询 `next`。

该方案比 WebSocket registry 更适合当前多 worker 部署，也能复用现有 SSE 解析和 Redis cursor。旧桌面版本继续使用 `next`，因此后端升级无破坏性。

## Risks / Trade-offs

- [同一回答由专用 SSE 和会话 SSE 重复到达] → eventId 去重之外继续使用 taskId、revision、updatedAtMs 单调归并，测试乱序与重复投递。
- [Redis Stream 有保留上限，长时间离线会缺事件] → 初次连接和游标过期时发送完整 snapshot，并用历史接口校准。
- [SSE 经代理缓冲导致桌面推送延迟] → 保持 `X-Accel-Buffering: no`、keepalive 和小帧；桌面在建立失败或静默超时后退避轮询。
- [新旧桌面客户端并存造成同一任务被重复认领] → 现有 claim 幂等和 processing 状态继续作为服务端仲裁，客户端按 requestId 加本地 in-flight 锁。
- [截图后台任务异常时没有发布最终事件] → 背景包装器在成功和捕获异常后的最终持久状态上统一发布，并有回归测试。
- [跨模块直接依赖 RealtimeSpeechService 增加耦合] → 仅暴露 `publish_session_event` 边界，业务服务不访问 ASR 内部状态；后续可替换为独立 SessionEventPublisher port。

## Migration Plan

1. 先部署 Backend：支持新事件、设备 SSE 和旧接口兼容；此时旧 Web/Desktop 行为不变。
2. 部署 Web：订阅统一事件，截屏正常路径取消 200ms 查询；保留断线退避查询。
3. 构建并发布新版 Desktop：优先设备 SSE，失败才退避轮询；旧安装包继续正常使用。
4. 观察截屏请求到认领延迟、SSE 重连次数、fallback 查询次数、事件重复率和错误率。
5. 若 Web 回归，只回滚 Web；若 Desktop 回归，只回滚安装包；Backend 新接口与旧接口并存，无数据库迁移。

## Open Questions

无阻塞问题。统一事件流本轮继续使用 SSE；只有在未来需要双向高频控制或连接数超过当前部署容量时，再评估 WebSocket 或专用消息网关。
