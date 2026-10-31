# 国服四页SEO内容优化：本地验收

## 范围与来源

- 用户批准四个既有公开页面的内容优化，并要求先在本地查看；未部署、未提交推送Git。
- 分支 `codex/cn-search-content-20261026`，起点 `release-cn-20261022.1`。
- Web基线为封版静态包：328份文件，实际镜像与恢复边界见[当前国服基线](../../docs/current-cn-baseline.md)。通用源码构建不能替代这一来源。

## 已完成

- 首页保留现有布局、视频、演示、下载及套餐交互；更新介绍、资料依据、场景文案和合成FAQ示例，同时同步初始HTML、源码与实际入口文案。
- 实时页补充本场资料作用、完整问题到建议的合成示例与核实步骤。
- 程序员页补充缓存设计追问及数组去重练习的输入约束、边界和验证方法。
- 价格页补齐国服会员每日模拟1场/简历3次、其余100积分、北京时间刷新与模拟60分钟期限；没有改变实际账务服务。
- 三份公开事实文件同步上述权益。关键词分工见[关键词映射](../research/KEYWORD-MAP-20261026.md)。

## 组装与隔离

运行 `python3 tools/cn_search_content/build_preview.py`：先核对归档及328份逐SHA清单，再应用8个文件的受限增量，其余320份保持不变。首页只在实际入口 `main-8b805158.js` 执行逐项唯一旧文案替换，不改变逻辑或模块引用。反向文案替换可精确恢复原字节，十个业务懒加载组件及其它资源保持。

本地沿用原模块文件名并禁用缓存，避免产生两套共享模块。**这不是可直接部署的缓存方案**：未来上线必须重新核对实际运行组件，进行完整模块引用图的资源版本处理，并重新核验当前价格。不得把候选目录直接覆盖生产。

价格区块逐字保留封版中的生成结果，包括2026-10-10同步时间；本地角标明确显示快照日期。所有JSON-LD脚本与原CSP保持，不新增FAQPage。原网站robots、sitemap与非目标HTML不变；本地HTTP额外禁止索引。

预览服务只绑定127.0.0.1，不转发线上请求。匿名夹具使用封版公开价格、已公开的客服和安装包元数据；用户、会话、资料、订单为空或合成。业务写入405，不提供真实登录、上传、支付、面试、下载包代理或模型调用。

## 验证

- 静态增量验收：7项通过，覆盖严格文件范围、业务组件/导入保持、模糊锚点拒绝、四页H1/canonical/内链/JSON-LD/CSP、套餐字节、首页两种渲染内容及原路由信号。
- 既有首页交互回归：14项通过，包含下载菜单、套餐切换、演示切换、视频与登录页作用域。
- Web TypeScript检查通过；候选入口JS `node --check`通过。
- 本地HTTP：四页、模拟/简历/笔试入口及匿名状态200；禁缓存和noindex有效；POST405。HTTP入口200不等于真实用户流程已验收。
- 浏览器：四页桌面与390px手机宽度未见横向溢出；检查合成示例、代码示例、权益卡片与目录定位。首页真实演示切换、套餐选择、FAQ展开通过，未发现控制台错误。
- 本地截图和HTTP摘要在 `artifacts/cn-search-content-20261026/`（生成物，不含真实用户内容）。
- OpenSpec严格校验与差异空白检查通过。

## 命令

```bash
python3 tools/cn_search_content/build_preview.py
python3 -m unittest discover -s tools/cn_search_content -p 'test_*.py' -v
node node_modules/typescript/bin/tsc -p apps/web/tsconfig.json --noEmit
node --check artifacts/cn-search-content-20261026/candidate/html/assets/main-8b805158.js
(cd apps/web && node ../../node_modules/vitest/vitest.mjs run src/homepage-layout.test.tsx --config vite.config.ts)
openspec validate refresh-cn-target-keyword-pages --strict
python3 -B tools/cn_search_content/preview_server.py --root artifacts/cn-search-content-20261026/candidate/html --port 5183
```

依赖来自本机已安装工具；workspace包必须指向本隔离分支。最初复用旧工作区整个node_modules时曾引入10条简历账本类型误报；改为本分支protocol/config依赖后TypeScript通过，没有为此改动账本代码。第一次从仓库根调用Vite测试的工作目录不符也已修正；最终结果以上述准确命令为准。

## 局限

没有运行整仓后端回归、真实支付/面试/模型或生产压测；没有把内容检查当作全站功能验收。排名、流量及转化收益仍需未来获授权发布后用真实数据观察，本轮不保证提升。
