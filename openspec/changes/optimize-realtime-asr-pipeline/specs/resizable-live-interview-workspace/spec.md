## MODIFIED Requirements

### Requirement: Present conversation and answers as resizable desktop columns
在桌面视口中，实时工作台 MUST 将“实时对话”放在左栏、“回答”放在右栏，并 MUST 在两栏之间提供可拖动分隔条。左侧实时对话栏 MUST 优先消费当前面试 session 的流式 Partial Transcript 与 Final Transcript，并 MUST 对同一句话执行增量覆盖更新，而不是为每次局部修订重复插入一条新转录。系统 MUST 抑制静音误触发、空白文本和失效 partial 引起的无意义刷新。拖动 SHALL 实时调整两栏比例，且任一栏不得小于保证核心内容可读和可操作的最小宽度。

#### Scenario: User opens the desktop workspace
- **WHEN** 视口达到桌面断点并加载实时面试页
- **THEN** 实时对话和回答以左右两栏出现，回答历史翻页和紧凑问题操作位于右侧回答栏

#### Scenario: Partial transcript grows or corrects
- **WHEN** 当前面试 session 收到某一句话的合法新 Partial Transcript revision
- **THEN** 左侧实时对话栏在同一 React render 中显示该 revision 的新增或纠正文本，不追加重复对话、不生成供应商未返回的内容

#### Scenario: Provider corrects the mutable tail
- **WHEN** ASR 的新 revision 与上一 revision 具有相同前缀但改写了尾部假设
- **THEN** 渲染层保留最长公共前缀对应的稳定 DOM 内容，并在当前 render 中直接替换可变尾部，页面文本必须与新 revision 完全一致

#### Scenario: Batched provider revision contains several new characters
- **WHEN** ASR 一次返回由多个字符组成的新 revision
- **THEN** 页面立即显示该 revision 的全部已接收字符，不得以逐字动画、debounce、throttle 或蓄水池延迟已收到的文本

#### Scenario: Transcript presentation does not schedule motion
- **WHEN** 任意 Partial 或 Final revision 进入网页状态层
- **THEN** 页面直接显示当前权威文本，不为字幕内容创建动画帧、定时器或后台展示队列

#### Scenario: Provider temporarily retracts a partial transcript
- **WHEN** 同一未定稿 utterance 的较新 revision 比当前可见文本更短
- **THEN** 左侧实时对话栏保留当前较长可见文本，不得让临时回缩删除用户已经看到的内容；后续增长或 Final 仍按各自规则继续更新

#### Scenario: Final transcript replaces the partial transcript
- **WHEN** 某一句话对应的 Final Transcript 到达
- **THEN** 系统在同一 render 中使用权威 Final Transcript 更新业务状态和全部可见文本，不执行尾字动画，并保留同一条对话记录的角色和顺序；若 Final 只是当前可见文本的严格短前缀，则保留较完整可见文本并将其冻结为 Final

#### Scenario: Empty or phantom transcript is suppressed
- **WHEN** 实时链路返回空白文本、静音误触发结果或已失效的旧 partial
- **THEN** 左侧实时对话栏不新增无意义内容，也不因该结果触发明显闪动

#### Scenario: User drags the divider
- **WHEN** 用户向左或向右拖动两栏之间的分隔条
- **THEN** 两栏宽度随指针移动并在达到任一最小宽度时停止继续压缩

#### Scenario: Streaming content updates during drag
- **WHEN** 用户调整分栏比例时对话修订或回答流式内容到达
- **THEN** 系统保持同一对话、答案、草稿和截图任务状态，不卸载或重复创建业务组件

#### Scenario: User creates or enters a different interview session
- **WHEN** 用户新建面试或从另一场面试进入当前实时工作台
- **THEN** 实时对话、待确认问题和当前回答任务只显示当前 `sessionId` 的内容，不继承或合并上一场面试的临时状态

#### Scenario: Current session has no realtime transcript yet
- **WHEN** 新面试 session 尚未收到任何 Partial 或 Final Transcript
- **THEN** 实时对话区显示当前 session 的等待状态，而不是继续展示上一场面试的转录

### Requirement: Quick answer SHALL assemble the latest interviewer turn

没有手动输入问题时，系统 MUST 根据当前 session 的实时双角色对话整理最近一轮面试官问题。系统 MUST 以候选人最近一次完整发言作为轮次边界，MUST 合并该边界后的面试官完整片段，MAY 补充比最新完整片段更新的未定稿片段，并 MUST NOT 把候选人发言正文作为待回答问题。

#### Scenario: Interviewer asks one question across several transcript segments
- **WHEN** 面试官在候选人最近一次发言后产生多个连续的完整转录片段，且用户未填写手动问题并点击快答
- **THEN** 系统按时间顺序去重并合并这些面试官片段，再提交现有回答模型

#### Scenario: Latest interviewer fragment is still partial
- **WHEN** 已有完整问题片段，且存在时间更新的面试官未定稿片段
- **THEN** 系统将最新未定稿片段补充到问题末尾，但不重复已经出现的文字

#### Scenario: Candidate speech separates conversation turns
- **WHEN** 候选人在两个面试官问题之间完成了一次发言
- **THEN** 快答只整理该候选人发言之后的最新面试官轮次
