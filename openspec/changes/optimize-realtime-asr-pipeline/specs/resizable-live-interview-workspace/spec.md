## MODIFIED Requirements

### Requirement: Present conversation and answers as resizable desktop columns
在桌面视口中，实时工作台 MUST 将“实时对话”放在左栏、“回答”放在右栏，并 MUST 在两栏之间提供可拖动分隔条。左侧实时对话栏 MUST 优先消费当前面试 session 的流式 Partial Transcript 与 Final Transcript，并 MUST 对同一句话执行增量覆盖更新，而不是为每次局部修订重复插入一条新转录。系统 MUST 抑制静音误触发、空白文本和失效 partial 引起的无意义刷新。拖动 SHALL 实时调整两栏比例，且任一栏不得小于保证核心内容可读和可操作的最小宽度。

#### Scenario: User opens the desktop workspace
- **WHEN** 视口达到桌面断点并加载实时面试页
- **THEN** 实时对话和回答以左右两栏出现，回答历史翻页和紧凑问题操作位于右侧回答栏

#### Scenario: Partial transcript updates the current utterance
- **WHEN** 当前面试 session 收到某一句话的 Partial Transcript 更新
- **THEN** 左侧实时对话栏原地更新该句对应的当前内容，而不是追加一条重复对话

#### Scenario: Final transcript replaces the partial transcript
- **WHEN** 某一句话对应的 Final Transcript 到达
- **THEN** 系统将该句的 partial 状态替换为 final 状态，并保留同一条对话记录的角色和顺序

#### Scenario: Empty or phantom transcript is suppressed
- **WHEN** 实时链路返回空白文本、静音误触发结果或已失效的旧 partial
- **THEN** 左侧实时对话栏不新增无意义内容，也不因该结果触发明显闪动

#### Scenario: User drags the divider
- **WHEN** 用户向左或向右拖动两栏之间的分隔条
- **THEN** 两栏宽度随指针移动并在达到任一最小宽度时停止继续压缩

#### Scenario: Streaming content updates during drag
- **WHEN** 用户调整分栏比例时对话修订或回答流式内容到达
- **THEN** 系统保持同一对话、答案、草稿和截图任务状态，不卸载或重复创建业务组件
