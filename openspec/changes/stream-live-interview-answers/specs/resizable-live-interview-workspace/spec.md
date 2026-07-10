## MODIFIED Requirements

### Requirement: Present conversation and answers as resizable desktop columns
在桌面视口中，实时工作台 MUST 将“实时对话”放在左栏、“回答”放在右栏，并 MUST 在两栏之间提供可拖动分隔条。拖动 SHALL 实时调整两栏比例，且任一栏不得小于保证核心内容可读和可操作的最小宽度。实时回答区 MUST 在模型生成过程中持续展示已收到的回答正文片段，而不是等待完整回答完成后才显示主要内容。

#### Scenario: User opens the desktop workspace
- **WHEN** 视口达到桌面断点并加载实时面试页
- **THEN** 实时对话和回答以左右两栏出现，回答历史翻页和紧凑问题操作位于右侧回答栏

#### Scenario: User drags the divider
- **WHEN** 用户向左或向右拖动两栏之间的分隔条
- **THEN** 两栏宽度随指针移动并在达到任一最小宽度时停止继续压缩

#### Scenario: Streaming content updates during drag
- **WHEN** 用户调整分栏比例时对话修订或回答流式内容到达
- **THEN** 系统保持同一对话、答案、草稿和截图任务状态，不卸载或重复创建业务组件

#### Scenario: Streamed answer text appears before completion
- **WHEN** 用户点击快答且后端返回第一个回答 chunk
- **THEN** 右侧回答区立即展示该 chunk 的正文，并保持正在生成状态直到完成、失败或取消

#### Scenario: User views history while latest answer streams
- **WHEN** 用户查看历史答案时最新回答仍在流式生成
- **THEN** 历史答案保持可读，页面提示有新内容可回到最新，且最新回答继续累积流式状态
