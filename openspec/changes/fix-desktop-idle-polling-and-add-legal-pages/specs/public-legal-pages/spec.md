## ADDED Requirements

### Requirement: Public legal pages are directly accessible
公开站点 SHALL 提供无需登录的 `/terms` 用户协议和 `/privacy` 隐私政策页面；两个地址 MUST 支持直接打开与浏览器刷新并返回 HTTP 200。

#### Scenario: Visitor opens the user agreement directly
- **WHEN** 访客请求 `/terms` 或刷新该地址
- **THEN** 服务端返回 Web 应用且页面显示用户协议，不返回通用 404

#### Scenario: Visitor opens the privacy policy directly
- **WHEN** 访客请求 `/privacy` 或刷新该地址
- **THEN** 服务端返回 Web 应用且页面显示隐私政策，不要求登录

### Requirement: Login consent links to both legal documents
登录页 SHALL 将用户协议和隐私政策作为可区分、可键盘访问的链接展示，MUST NOT 只显示不可点击的概括文字。

#### Scenario: User reviews terms before requesting an SMS code
- **WHEN** 用户在登录页查看同意说明
- **THEN** 用户可以分别打开用户协议和隐私政策，并能返回继续登录

### Requirement: Legal content reflects current product behavior
法律页面 MUST 清楚说明当前账号数据、简历/JD/知识材料、转录、截图、设备信息、支付订单、第三方处理、AI 建议边界、原始音频默认不保存、用户数据管理和联系方式；MUST NOT 承诺尚未实现的自动删除期限、退款结果或服务可用性。

#### Scenario: User reviews data collection and processing
- **WHEN** 用户阅读隐私政策
- **THEN** 页面区分账号与设备数据、用户上传内容、实时处理数据、支付记录及第三方处理目的

#### Scenario: User reviews AI and interview-use boundaries
- **WHEN** 用户阅读用户协议
- **THEN** 页面说明 AI 输出仅为建议、用户应基于真实经历并遵守面试方规则

#### Scenario: User wants data support
- **WHEN** 用户需要管理或删除资料与会话记录
- **THEN** 页面指向产品内现有管理入口及客服联系方式，不虚构未实现的自动化能力

### Requirement: Legal links remain discoverable outside login
首页页脚 SHALL 提供用户协议和隐私政策入口，链接文字必须明确，不能只依赖首页折叠式隐私摘要。

#### Scenario: Visitor reaches the public footer
- **WHEN** 访客浏览首页页脚
- **THEN** 可以直接进入用户协议或隐私政策

### Requirement: Legal routes have safe indexing and security behavior
法律页面 SHALL 继承公开站点 HTTPS 与安全响应头，并 SHALL 使用 `noindex, follow`，避免草案内容成为主要搜索落地页；站内链接仍可被跟随。

#### Scenario: Search crawler requests a legal page
- **WHEN** `/terms` 或 `/privacy` 被直接请求
- **THEN** 响应包含 `X-Robots-Tag: noindex, follow` 和现有公开站点安全响应头
