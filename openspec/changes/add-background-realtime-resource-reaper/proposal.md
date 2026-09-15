## Why

面试页面关闭、网络中断或桌面伴随程序退出后，部分实时资源可能继续驻留到进程生命周期结束。当前 ASR 持久会话模式会跳过空闲扫描，且空闲会话回收主要依赖后续请求触发，导致管理平台已无面试时容器 RSS 仍维持较高，多个异常会话叠加会放大内存和连接压力。

## What Changes

- 增加独立的后台会话回收循环，定期发现并幂等终止超时的 live 面试。
- 为持久 ASR 会话增加会话生命周期联动和异常断开兜底，确保空闲 provider source 最终关闭。
- 扩展运行时资源指标，区分当前活跃资源与历史累计计数，便于确认回收是否完成。
- 增加回归测试覆盖后台回收、重复回收、ASR 连接归零和进程关闭。

## Capabilities

### New Capabilities

- `background-realtime-resource-reaper`: 后台发现并回收空闲或异常中断的实时面试资源。

### Modified Capabilities

<!-- No main capability spec exists for this lifecycle change; the existing cleanup change remains the implementation baseline. -->

## Impact

- `apps/backend/app/main.py` 生命周期与后台任务。
- `apps/backend/app/services/realtime_speech_service.py` 会话回收与指标。
- `apps/backend/app/services/dashscope_realtime_asr_gateway.py` 持久会话空闲兜底。
- Backend 配置、回归测试和 OpenSpec 能力规范。
- 不改变面试页面布局、回答模型提示词、外部供应商协议或敏感数据持久化策略。
