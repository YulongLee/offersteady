## ADDED Requirements

### Requirement: 场景内容具体可核实
实时辅助页和程序员页 MUST 在初始 HTML 提供与资料选择、问题输入、回答建议和用户核实相关的具体问答。说明示例 MUST 标明为合成示例，不冒充用户评价或真实运行输出。

#### Scenario: 访客了解建议来源
- **WHEN** 访客不执行 JavaScript 读取两个功能页
- **THEN** 能看到简历、JD 和知识资料的作用、识别错误时的处理方式，以及 AI 建议需要自行核实的边界

### Requirement: 商业入口清楚且不改变业务
价格页 MUST 继续由原生产目录生成价格和费率；下载说明 MUST 指向已有官方入口，不复制安装包版本号或要求访客为查看下载先登录。MUST NOT 新增支付、模型或下载 API 请求。

#### Scenario: 查看价格和下载
- **WHEN** 未登录访客打开价格或下载页
- **THEN** 价格页初始 HTML 展示构建时从生产读取的金额；下载页可以抵达首页现有下载区，原购买和登录流程保留

### Requirement: GEO 事实与可见页面一致
llms.txt、llms-full.txt 与 public-facts.json MUST 区分公开价格查询与登录购买，使用技术场景页的程序员定位，且不得固定存储价格或宣称收录、排名、准确率和竞品优越性。

#### Scenario: 机器读取价格指引
- **WHEN** 读取任一公开发现文件
- **THEN** 能明确找到匿名公开 /pricing 及登录后购买的区别，而不是只有登录后查看的指引

### Requirement: 索引和轻量交付不回退
四页 MUST 继续具有唯一 Title、一个 H1、自引用 canonical、核心正文与内链，不含 noindex；sitemap URL 集合 MUST 保持30个。JSON-LD 的精确哈希 MUST 与候选 Nginx 匹配，页面 MUST NOT 增加运行时 JS。

#### Scenario: 构建后检查
- **WHEN** 检查生产模式候选构建
- **THEN** 上述静态信号、对应修改日期、HTML/CSS预算和 JSON-LD 哈希校验通过，价格与生产目录核对通过

### Requirement: 阅读与业务隔离
四页 MUST 提供清晰的章节导航与可见焦点，并在390px和1440px视口无页面横向溢出。首页设计、海外版和已登录业务代码 MUST 不受本轮变更影响。

#### Scenario: 本地验收
- **WHEN** 访客在手机和桌面浏览本地四页并点击章节导航
- **THEN** 内容可读、锚点正确；操作只导航，不触发真实订单、收音或资料上传
