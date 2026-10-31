# 国服状态读取减负：本地候选 20261028.1

> 后续用户授权的国服发布已于2026-10-29完成，见[生产发布记录](cn-state-control-20261029.1.md)。下文保留10月28日本地交付时的状态与结果。

状态：**本地开发与相关回归完成，未部署、未提交或推送 Git**。用户要求晚上再部署；本文不是生产发布完成记录。

## 改动与预期影响

1. 国服 Web 仅合并相同身份、凭据和生命周期下**同时进行**的 `/web/state` 请求。请求结束后立即清理，无成功或失败 TTL；后续读取仍请求服务端。各调用方独立取消、独立取得状态对象。
2. CN Backend 在一次状态聚合中复用已经读到的原始资料记录，避免会话绑定再次读取相同资料。仅接通国服已认证的聚合入口；跨请求不复用，列表未覆盖的资料仍沿原查询处理。
3. 配套保护登录切换、退出、同会话令牌刷新、跨客户端写入及流式回答结束后的新鲜度；显式刷新绕过旧请求。存储受限和不支持 `structuredClone` 的旧浏览器有回归覆盖。

目的是减少重复网络与数据库工作，缓解并发时状态查询的额外负担。没有修改模型、Prompt、音频处理、收费规则或界面布局；不能据本地结果承诺线上 P95 降幅。

## 来源与范围保护

- 对照[当前国服基线](../current-cn-baseline.md)和[10月27日网页发布记录](cn-search-content-20261027.1.md)。本轮开始前 Backend 的 230 份实际运行输入清单与本地源码一致。
- Backend 仅修改 `modules/web.py`、`services/document_service.py`、`services/session_service.py`；其余 227 份运行输入保持。三个文件内的非目标 AST 对照通过，权威开始/回答校验与原资料刷新算法保持。
- Web 保留任务开始前的首页 SEO 内容及全部路由；模拟面试、简历优化、笔试多屏、支付、助手入口保留。既有异步面试工作区、数学与 Word 导出不进入首页同步启动范围。
- 国际服、桌面助手、依赖清单、AI 配置和 Prompt 没有本轮修改。当前工作树原有已发布 SEO 改动被保留，不能把全部未提交差异都归为本轮优化。

## 可复核的本地结果

证据目录：`artifacts/cn-state-read-local-20261028/`（本地忽略目录）。

| 验证 | 实际结果 |
| --- | --- |
| 相同合成数据的 24 个并发状态读取 | 原直接客户端 24 次网络请求，候选 1 次；完成后的下一次读取重新请求，累计 2 次 |
| 12 个合成会话共享 6 份资料，真实隔离本地 PostgreSQL | 资料/会话读取部分从 8 次连接、8 次 SELECT 降至 2 次连接、2 次 SELECT；两组均 0 写入，输出等价 |
| 前端最终完整测试 | 67 文件、662 项通过；包含本轮专项 7 文件、78 项 |
| 后端相关测试，按测试标识去重 | 413 项通过、0 失败；1 项 Global 专属生命周期测试跳过 |
| 独立代码审查 | 发现并修复 3 项 P2；独立执行 63 项通过，无剩余本轮阻断发现 |
| 类型检查与生产模式构建 | 通过；最终构建记录 `web-build-verified.txt` |
| 本地浏览器检查 | 构建首页和公开导航正常渲染；未启动 API 时明确显示状态重试提示。没有真实登录、真实面试或模型调用 |

后端最初因未设置专用数据库而跳过的测试，已在隔离合成库补跑；不能把重复运行的条数相加为独立测试数量。最终去重结果见 `test-summary.json`。

## 能力场景验收

| 场景 | 覆盖与结果 |
| --- | --- |
| 并发合并、深层返回值隔离、结束后重读、失败后重试 | `backend-adapter-state.test.ts`；通过 |
| 独立取消、全部取消、预先取消、旧请求清理不删除新请求 | 同上；通过 |
| 匿名/认证、不同适配器、换账号、同账号退出再登录、迟到刷新与当前用户响应 | 同上及 `App.auth-state-scope.test.tsx`；通过 |
| 合法 401 刷新、两个独立客户端的令牌轮换竞争 | 同上及既有鉴权回归；通过 |
| 写入开始/结束、未知提交结果、支付同步、独立资料/简历客户端、force 刷新 | `state-read-scope.test.ts` 与状态适配器回归；通过 |
| SSE completed/failed/cancelled/EOF/abort 后重新读取 | `backend-adapter-state-stream.test.ts` 五种终结；通过，原解析及输出 AST 保持 |
| 心跳和 ACK 不无谓失效；持续变化只有限重读 | 状态作用域与适配器回归；通过 |
| 重名资料显示与原名绑定、缺失/过滤/删除回源 | `test_cn_state_document_reuse.py`；通过 |
| 外部 owner、错误键、非原始记录拒绝 seed；下一请求版本和生命周期更新 | 同上；通过 |
| 并发删除时点、不同用户隔离、mock 选定版本、Global/匿名原分支与 wire 等价 | 同上；通过 |
| 模拟面试收费/60分钟截止、资料权限、简历优化、回答完整性 | 相关既有后端与完整前端回归；通过 |

## 连接复用评估：未接入产品

独立实验使用专属 localhost 合成 PostgreSQL（1 CPU / 512 MiB）及临时隔离的 `psycopg_pool 3.3.3`；产品环境没有安装该依赖。每组 120 次操作，每操作相同 3 次点查询，池大小 4、最大等待 16；操作计时包含借连接等待，启动单列。

| 并发 | 短连接操作 P95 | 有界池操作 P95 |
| --- | --- | --- |
| 1 | 33.136 ms | 3.248 ms |
| 4 | 61.912 ms | 5.597 ms |
| 8 | 116.034 ms | 12.405 ms |

每组短连接实测创建 360 个连接；池启动 4 个、测量期间新增 0 个。正常工作负载均 0 错误；异常回滚、归还、等待超时、队列上限和关闭清理通过，工具安全单测 37 项通过。最终目标检查拒绝间接服务/环境路由；实验 schema 和连接清理已核对。

这是同机点查询实验，**不是应用全链路回放或生产 API P95 对照**，没有验证生产池大小、多进程、全部事务模式和鉴权撤销合同；本轮不把池加入产品运行时。版本与行为依据 [Psycopg 官方池文档](https://www.psycopg.org/psycopg3/docs/api/pool.html)，原始结果及最终生命周期/目标保护复核分别保存在 `pool-*.json`。

## 仍未通过的历史附加检查

三项既有附加脚本已实际运行，不能报为通过：

- `test:seo-p0`：源码 Nginx 未满足 `www` 重定向断言；本轮 Nginx 与修改前源码逐字一致。
- `test:seo-build`：总 JS 超过旧 1,350,000 字节预算。
- `test:route-split`：入口超过旧 410,000 字节预算；此前的异步模块隔离断言通过。

在相同生产环境执行两次不写产物的构建，基线精确覆写任务开始前的 7 份源码，候选使用最终源码。结果：基线入口 461,821 字节、总 JS 1,466,588 字节；候选入口 464,339 字节、总 JS 1,471,235 字节。旧预算在本轮之前已超标；本轮入口增加 2,518 字节，启动 JS gzip 增加 1,633 字节。比较记录为 `web-source-baseline-comparison.json`，未放宽任何预算或 Nginx 断言。

首次完整测试另有 6 项旧 SEO 文案/指纹断言失败。对照冻结首页确认来自此前已批准内容；保留全部断言，只更新 3 项文案和 3 项源码指纹预期，明确源码与生产组装字节的区别。最终完整测试通过，初始失败证据保留在 `preexisting-seo-test-alignment.json` 与 `web-all-junit.xml`。

本地构建不能代表当前线上 Web 静态包完全等价。晚间不能直接整体覆盖线上；需重新核对实际镜像与发布差异。上述源码 SEO/预算问题另行保留，不能通过复用旧标签包或更改阈值掩盖。

## 验证命令与交付限制

前端实际执行：

```bash
npm run typecheck -w @offersteady/web
npm run test -w @offersteady/web -- --maxWorkers=2
VITE_APP_ENV=production VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=cn-state-read-local-20261028.1 npm run build -w @offersteady/web
npm run test:seo-p0 -w @offersteady/web
npm run test:seo-build -w @offersteady/web
VITE_APP_ENV=production VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=cn-state-read-local-20261028.1 npm run test:route-split -w @offersteady/web
openspec validate reduce-cn-state-read-overhead --strict
git diff --check
```

后端使用现有 `.venv/bin/python`、`PYTHONPATH=apps/backend`、测试环境、空产品数据库/Redis配置和 fake SMS；需要 PostgreSQL 的用例显式指向专属本地合成库。具体分组及 JUnit 文件列于 `test-summary.json`，涵盖鉴权、foundation 状态场景、state-read、下载/资料 RAG、heartbeat、回答完整性、mock、CN 简历与收费。实验安全测试命令为 `.venv/bin/python -m pytest tools/state_read_optimization/test_connection_pool_eval.py -q`。没有记录 DSN 或用户数据到交付文件。

旧 `review:live` 脚本仍依赖过时原型登录标记和布局约定，本轮未将它冒充真实登录端到端验证；执行了构建浏览器只读检查和合成场景自动化。未测试真实供应商、操作系统收音或真实支付，均不属于本轮改动。

晚间发布前仍需取得当时实际 CN Backend/Web 镜像与来源、制作最小增量并检查现有功能、确认用户工作门禁、固定候选镜像及回退目标。生产发布和线上 P95 观察应在新的授权执行中另行记录。
