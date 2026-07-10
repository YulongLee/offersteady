## MODIFIED Requirements

### Requirement: Present conversation and answers as resizable desktop columns
在桌面视口中，实时工作台 MUST 将“实时对话”放在左栏、“回答”放在右栏，并 MUST 在两栏之间提供可拖动分隔条。拖动 SHALL 实时调整两栏比例，且任一栏不得小于保证核心内容可读和可操作的最小宽度。实时对话区 MUST 消费桌面伴随程序发布的双声道转录事件，并继续只展示“面试官”和“我”两个角色；麦克风/耳机来源显示为“我”，系统音频来源显示为“面试官”。

#### Scenario: User opens the desktop workspace
- **WHEN** 视口达到桌面断点并加载实时面试页
- **THEN** 实时对话和回答以左右两栏出现，回答历史翻页和紧凑问题操作位于右侧回答栏

#### Scenario: User drags the divider
- **WHEN** 用户向左或向右拖动两栏之间的分隔条
- **THEN** 两栏宽度随指针移动并在达到任一最小宽度时停止继续压缩

#### Scenario: Streaming content updates during drag
- **WHEN** 用户调整分栏比例时对话修订或回答流式内容到达
- **THEN** 系统保持同一对话、答案、草稿和截图任务状态，不卸载或重复创建业务组件

#### Scenario: Desktop dual-channel transcript updates during drag
- **WHEN** 用户调整分栏比例时桌面伴随程序发送新的麦克风或系统音频转录事件
- **THEN** 系统将麦克风/耳机事件显示为“我”、系统音频事件显示为“面试官”，且不丢失当前分栏比例、手动草稿、回答流或历史查看状态

#### Scenario: Audio source becomes degraded
- **WHEN** 桌面伴随程序或服务端报告来源混合、断开、缺失或不兼容
- **THEN** 实时对话区显示来源降级提示并保持手动输入可用，不显示“角色待确认”或角色修正控件
