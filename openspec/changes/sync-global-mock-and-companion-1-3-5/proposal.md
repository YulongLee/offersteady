## Why

用户于 2026-10-15 要求同步优化国际服及伴随程序，完成测试后部署，并明确保留国际服现有收费，仅同步性能、收音和稳定性优化。国服已验证的麦克风恢复、能力登记和模拟面试资源清理需要在独立 Global 实际版本中检查并安全同步。

## What Changes

- 从实际运行 Global Backend/客户端版本审计差异，保留已上线 heartbeat、P95 诊断、英文模拟面试、联网回答与独立会员权益。
- 核验并保留普通网页 heartbeat 的轻量权威投影调用，避免回退为完整会话及资料读取，保持页面租约、结束状态和空闲检测语义。
- 模拟面试提交后先隔离旧轮采集，再启动下一题；有界跟踪 ASR 关闭，避免慢关闭阻塞换题或污染新轮。修复断连清理的次生异常，补充安全生成诊断。
- 同步尚未生效的 Global 网页状态请求协调，修复强制刷新被旧请求合并和换账号短期缓存串用问题，保留已有首屏分包及遥测采样。
- Global Windows x64、macOS arm64/x64 发布正式 1.3.5：同步实际音频输入签名权限、麦克风错误恢复、采集状态及周期能力登记修复，保持英文 UI 和独立国际服身份。
- 完善 Global Mac 正式发布的签名、公证与终检；发布元数据必须反映实际产物验证结果。先完整验证三平台不可变对象，再统一更新下载清单。
- 只部署获准必要 Global 组件与下载元数据，基于实际镜像增量、用户活动门禁和精确回滚；不发布整个混合工作区。

## Capabilities

### New Capabilities

- `global-mock-turn-reliability`: 国际服模拟面试换题、收音关闭、断线清理及隐私诊断。
- `global-companion-1-3-5-publication`: 独立国际服三平台助手的构建、真实验证及统一发布。
- `global-web-state-refresh`: 网页状态请求去重、权威刷新及登录身份缓存隔离。

### Modified Capabilities

无已归档对应主 Spec。沿用 [Global 模拟面试](../add-global-web-search-and-mock-interview/proposal.md) 和 [Global 性能同步](../sync-global-performance-parity/proposal.md) 的已批准产品行为，仅改可靠性及分发实现。

## Impact

网页增量另涉及 Global 状态协调器与静态依赖，保留其他业务函数、旧静态资源及线上 Nginx/CSP。

Desktop 共用修复与 Global 打包/元数据、Global 模拟 Runtime/Audio/Jobs/诊断及必要依赖、独立 Global 安装对象和下载清单。保留 Global UTC 每日三场、七天及以上购买套餐会员准入和无积分收费；不新增国服 60 分钟期限，不改支付、模型/Prompt、英文输出政策或正常面试限额。不持久化原始音频，不操作真实用户测试数据，不部署国服。用户已明确授权验证通过后国际服上线。
