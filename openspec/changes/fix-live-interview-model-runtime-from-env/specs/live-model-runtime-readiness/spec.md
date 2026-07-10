## ADDED Requirements

### Requirement: Live answer runtime MUST read server-side model configuration from environment
实时面试问答运行时 MUST 由后端从服务端环境变量读取当前模型配置，包括模型基地址、模型名称和鉴权密钥。前端 MUST NOT 直接读取或拼接这些密钥，也 MUST NOT 通过浏览器判断模型是否已配置。

#### Scenario: Server environment is configured
- **WHEN** 后端运行环境中已经提供实时问答所需的 `.env` / 环境变量配置
- **THEN** live-answer 运行时使用这些服务端配置调用真实模型链路

#### Scenario: Frontend submits a manual interview question
- **WHEN** 用户在实时面试页输入问题并点击快答
- **THEN** 前端只提交会话标识、问题文本和认证信息，而不会提交模型密钥或完整 Prompt

### Requirement: Live answer runtime MUST classify model availability failures
系统 MUST 将实时问答中的模型可用性问题分类为至少以下几类：模型未配置、鉴权失败、供应商不可达、供应商限流、供应商返回无效结果。系统 MUST 返回结构化且安全的错误信息，前端 SHALL 直接使用该安全摘要提示用户。

#### Scenario: Model configuration is missing
- **WHEN** 后端未检测到问答模型所需的基地址或 API Key
- **THEN** live-answer 返回“模型未配置完成”类错误，而不是泛化成普通生成失败

#### Scenario: Provider authentication fails
- **WHEN** 上游模型供应商返回 401 或 403
- **THEN** 系统返回“模型鉴权失败，请检查服务配置”类安全错误，且不暴露密钥内容

#### Scenario: Provider is temporarily unavailable
- **WHEN** 上游模型供应商超时、网络不可达、返回 429 或 5xx
- **THEN** 系统返回可重试的暂时不可用错误，并允许用户保留原问题后再次尝试

### Requirement: Live answer runtime MUST surface readiness through stable diagnostics
系统 MUST 为实时面试问答提供稳定的运行时诊断边界，使开发和联调时可以确认当前失败属于会话状态、环境配置还是模型供应商问题。该诊断 MAY 通过结构化日志、模块状态接口或集成验证脚本体现，但 MUST 不暴露敏感配置值。

#### Scenario: Developer verifies live model readiness
- **WHEN** 开发者在本地使用已配置的 `.env` 启动后端并检查实时问答模块
- **THEN** 系统能够区分“会话未启动”和“模型配置/供应商不可用”两类问题，而不是混成同一种报错

#### Scenario: Logs are emitted for a failed live answer call
- **WHEN** 一次实时问答因为模型配置或供应商问题失败
- **THEN** 日志记录结构化错误类别、模块和 request id，但不会记录 API Key、完整 Prompt 或用户敏感原文
