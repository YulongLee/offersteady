## Why

当前代码题回答默认倾向 Python，用户无法在面试开始前声明本场是否包含编程题及希望使用的语言，导致生成代码与岗位要求或用户熟悉的技术栈不一致。需要把编程偏好提升为会话级配置，让实时问答与截图代码题稳定使用同一语言，同时不干扰非编程面试。

## What Changes

- 在面试准备页增加“需要编程”开关，默认关闭；开启后展示编程语言选择器并默认选择 Python。
- 首期支持 Python、Java、C++、JavaScript、TypeScript 和 Go，配置在面试开始后锁定，并可在刷新、跨设备恢复和重新开始时保持一致。
- 后端将编程需求与语言作为会话权威配置持久化，并通过所有权和会话状态校验更新。
- 实时文字问答、自动语音问题回答和截图代码题统一注入编程策略：仅在题目要求代码或算法实现时使用所选语言，非代码题不强行输出代码。
- 未开启编程时保持当前回答逻辑，不新增开始面试门禁，不改变音频、截图或个人资料的保存范围。
- 增加前后端回归测试、Prompt 质量测试及合成 AI eval 样本。

## Capabilities

### New Capabilities

- `interview-programming-preference`: 定义会话级编程开关、语言选择、持久化、状态锁定及回答链路约束。

### Modified Capabilities

- `streamlined-interview-entry`: 准备页需要展示、保存并恢复可选的本场编程配置，但该配置不增加新的开始门禁。

## Impact

- Web：准备页控件、领域类型、Backend Adapter 和恢复状态。
- Backend：会话 schema、领域记录、仓储、数据库迁移、更新 API 与重启继承逻辑。
- AI：Chat 与 Screenshot Answer 的集中式 Prompt 策略、合成评测及语言组合测试。
- 兼容性：历史会话与旧客户端默认 `programmingRequired=false`；不新增客户端密钥或敏感数据持久化。
