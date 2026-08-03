## MODIFIED Requirements

### Requirement: Fall back to a single-column narrow layout

在手机尺寸视口中，系统 MUST 按既有顺序单列展示实时对话、手动输入、回答和回答操作。回答区域 MUST 提供足以阅读问题与回答的默认高度，并 MUST 提供扩大和恢复回答框高度的明确控制。尺寸切换 MUST NOT 丢失回答、流式状态、历史位置或当前面试状态。

#### Scenario: User reads an answer on a phone

- **WHEN** 用户在手机端进入已有回答的实时面试
- **THEN** 回答框使用比内容自适应最小值更大的默认可视高度
- **AND** 回答标题区显示“扩大回答框”控制

#### Scenario: User expands the answer workspace

- **WHEN** 用户点击“扩大回答框”
- **THEN** 回答框扩展到接近当前手机视口的高度
- **AND** 控制变为“恢复回答框高度”
- **AND** 当前问题、回答和历史位置保持不变

#### Scenario: User restores the answer workspace

- **WHEN** 用户点击“恢复回答框高度”
- **THEN** 回答框恢复默认手机高度
- **AND** 页面仍可按原顺序滚动访问实时对话和回答操作
