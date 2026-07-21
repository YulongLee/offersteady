# v0.1 Release Readiness Specification

## ADDED Requirements

### Requirement: Initialize required database capabilities
系统 MUST 在生产账务或向量仓储初始化时幂等启用 pgvector，并 MUST 在扩展不可用时使发布验收失败。

#### Scenario: Existing database volume predates the init script
- **WHEN** 新版本连接一个尚未安装 vector 扩展的已有数据卷
- **THEN** 应用迁移安装扩展且 pgvector 验证通过

### Requirement: Run authenticated production E2E scenarios
端到端测试 MUST 在注册后为全部受保护请求携带当前用户 Access Token，并 MUST 只报告当前运行实际发现的问题。

#### Scenario: Production ownership gate is enabled
- **WHEN** E2E 用户注册成功并创建知识库、上传资料和创建面试
- **THEN** 所有请求以该用户 Token 通过鉴权而不是依赖显式 userId

### Requirement: Ship required production verification dependencies
生产镜像 MUST 包含实时 ASR 集成验证需要的客户端依赖。

#### Scenario: Operator verifies realtime ASR in production
- **WHEN** 运维执行 realtime_asr 集成验证
- **THEN** 验证器能够完成 WebSocket 往返而不是在导入阶段失败

### Requirement: Enforce web security headers
Web 首页、静态资源和反向代理 API SHALL 返回 HSTS、CSP、nosniff、frame deny 和 referrer policy。

#### Scenario: Browser loads the production homepage
- **WHEN** 客户端通过 HTTPS 请求首页
- **THEN** 响应包含定义的安全头且页面资源仍能正常加载

### Requirement: Reject zero-frame desktop diagnostics
桌面诊断 MUST 将原生采集返回的 `ok=false` 视为失败，并 SHALL 使用稳定 Bundle ID 执行本地权限重置和打包。

#### Scenario: Capture permission or device is unavailable
- **WHEN** 原生麦克风或系统音频探测产生 0 帧并返回错误
- **THEN** 诊断命令失败并明确报告具体采集错误

### Requirement: Resolve known high-severity frontend advisories
发布依赖树 MUST 不包含 npm audit 当前识别的 high severity 生产依赖漏洞。

#### Scenario: Release dependency audit runs
- **WHEN** 使用官方 npm registry 执行生产依赖审计
- **THEN** high severity 漏洞数量为零

