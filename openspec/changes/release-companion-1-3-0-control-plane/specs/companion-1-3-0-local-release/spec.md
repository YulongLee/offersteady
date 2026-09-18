## ADDED Requirements

### Requirement: Local companion metadata reports version 1.3.0
本地伴随程序 MUST 从桌面包元数据报告版本 `1.3.0`；根工作区版本、线上发布清单和历史发布记录 MUST NOT 因本变更被修改。

#### Scenario: Electron starts locally
- **WHEN** 用户启动本地构建的伴随程序
- **THEN** 应用版本和构建元数据为 `1.3.0`

### Requirement: Control-plane polling remains bounded and non-overlapping
伴随程序 MUST 在绑定等待和稳定 live 状态使用 10 秒控制面轮询间隔，并 MUST 在上一笔请求完成前不发起同类并行请求；失败 MUST 使用已有有界退避。

#### Scenario: Waiting or live binding is healthy
- **WHEN** 伴随程序处于等待绑定或稳定 live 状态
- **THEN** 同类控制面请求之间间隔为 10 秒且最多只有一个在途请求

#### Scenario: Control request fails
- **WHEN** 一次控制面请求失败
- **THEN** 后续请求按照既有 5、10、20、30 秒上限退避，并在成功后恢复正常间隔

### Requirement: Existing interview media behavior is preserved
本地 1.3.0 MUST 继续使用现有音频采集、ASR、截图、回答和绑定协议，不因轮询版本更新改变用户面试链路。

#### Scenario: User runs a local interview
- **WHEN** 用户在本地 1.3.0 中开始面试
- **THEN** 音频、实时转写、截图和回答仍通过既有协议工作，控制面轮询不重复创建采集或回答任务

### Requirement: Local-only release boundary
本变更 MUST 只生成和启动本地开发构建，不上传发布产物、不更新线上清单、不部署或重启线上服务。

#### Scenario: Local verification completes
- **WHEN** 本地测试和构建通过
- **THEN** 产物留在本地，用户可以直接启动进行验收，线上服务状态保持不变
