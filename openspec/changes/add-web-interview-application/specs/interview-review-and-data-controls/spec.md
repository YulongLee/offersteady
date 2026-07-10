## ADDED Requirements

### Requirement: Show a lightweight interview review
系统 SHALL 在面试结束后展示持续时间、已确认问题、回答建议和使用过的资料类型，并 MUST 将原始记录与 AI 生成复盘分区展示。

#### Scenario: Ended interview opens
- **WHEN** 用户进入一场已结束面试的复盘页
- **THEN** 系统展示可核对的问题时间线、回答建议及资料来源，而不生成未经请求的能力评分

### Requirement: Represent review-generation status honestly
系统 MUST 显示 AI 复盘的等待、生成、失败和完成状态，并 SHALL 在失败时保留原始问题记录。

#### Scenario: Review generation fails
- **WHEN** AI 复盘服务返回错误或超时
- **THEN** 系统显示可重试状态且仍允许用户查看和删除原始会话记录

### Requirement: Manage session and source data
系统 SHALL 允许用户查看本场会话关联的简历、JD、知识材料、截图和记录的保存状态，并 SHALL 提供适用的单项删除和整场删除操作。

#### Scenario: User deletes a screenshot
- **WHEN** 用户确认删除一张已处理截图
- **THEN** 系统在服务端确认后移除原图及其直接派生的视觉识别数据，并清除客户端缓存

#### Scenario: User deletes the entire interview
- **WHEN** 用户确认删除整场面试
- **THEN** 系统删除该会话、问题、回答和会话专属附件，同时明确说明可复用资料是否仍被保留

### Requirement: Prevent sensitive-content exposure
系统 MUST 避免在页面标题、系统通知、前端日志和未授权设备上暴露完整简历、问题、截图或回答内容。

#### Scenario: Unauthorized device opens a review URL
- **WHEN** 未授权设备访问复盘链接
- **THEN** 系统只展示身份验证界面且不返回可渲染的面试正文

### Requirement: Support empty and deleted review states
系统 SHALL 为没有问题记录、复盘尚未生成和会话已删除提供明确状态，而不是展示误导性的空白成功页面。

#### Scenario: Interview ended without questions
- **WHEN** 一场面试结束但没有已确认问题
- **THEN** 系统说明没有可复盘记录，并提供返回首页或删除会话的操作
