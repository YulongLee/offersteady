# 国服简历优化安全局部改写 — 20261018.4

状态：本地开发、完整回归、实际编译浏览器及三例隔离真实 Provider QA 验收完成。未切换生产服务、未提交推送 Git。开发目录为 `/Users/liyulong/.codex/worktrees/cn-resume-optimizer/offersteady`。范围见[安全局部改写合同](../../openspec/changes/add-cn-resume-optimizer/safe-edit-application.md)，历史上线与失败事实保持。

## 本轮行为

模型提出的每条修改独立通过原引用、事实和格式检查；合格且没有重叠的实质修改才应用。所有重叠参与者均不采用，不按先后顺序任选一条。违规提议的正文、位置和替换内容不保存，其他合格修改可以交付。整个 JSON/schema、评分依据、语言和最终稿硬限制仍可使任务整体失败。

整份无有效改写时失败并原路退还创建日免费次数或 100 积分，不用原文冒充成功稿。部分成功按原规则结算一次，编辑、下载和另存不重复收费。会员每日三次、其余每次 100 积分、模拟面试每日一次等既有规则保持。

新增独立中文 Prompt v2，要求每条引用内的英文内容词和事实保留，不从同段、其他项目或 JD 借词。保留 v1；历史结果可继续读、编辑和下载。规则不能证明全部语义真实性，仍要求用户核实事实。

页面现在实际使用本地固定消息白名单显示已知失败原因，退款另按已提交状态显示。此前 `.3` 后端固定原因虽然已返回，实际网页未读取，仍显示泛化提示；本轮补齐并验证这条展示路径。未知或私密内容不能直接显示。成功稿可显示 AI 初稿采用/未采用提议的计数；计数不是未修改段落数，也不随用户后来编辑改变。

## 已完成验证

- 根代理合并八个 Backend 测试文件，禁止 Python 非回环网络，391 项通过，无失败或跳过；最后仅增加两项控制字符 AI eval，新 Provider 套 88 项通过，去重共 393 项。包括 42 条新 AI eval、22 项真实本地隔离 PostgreSQL/FastAPI 测试，覆盖部分成功结算、零有效退款、事务故障回滚、重放、取消/删除/源删迟到屏障和旧 v1 兼容。
- Web 60 文件全量 568 项通过、类型检查和显式 production 构建通过。追加真实 PG/FastAPI wire 四项后，全套 572 项通过、类型检查通过；IAB/Chrome 实际编译资源 13 个观察点通过，明确原因及退款实际可见，编辑/模拟面试保留。合成 HTTP harness 1003 项检查通过，候选 315 文件/CSP/SHA 保持。
- 独立审查已修复一项 P2：边缘控制字符不能先被 strip 隐去后污染整稿；现在独立拒绝该提议，12 项边缘正反回归通过。原全部事实/parser 守卫和请求预算保持，无未解决 P1/P2。
- 实际国服 Backend 229 输入中 227 项逐字保持，只改本功能 Provider/diagnostics，新增 v2 Prompt，共 230 输入。Service、Repository、schema、迁移、钱包、源删除、鉴权和其他功能未改。
- 实际 Web 305 旧路径均保留：旧 JS/CSS/媒体/SEO 等逐字相同；4 个 HTML 只更新模块 URL，构建标识仅标记本地版本。新增 10 个 JS，只有本功能 Page 有语义变化，其他 9 个模块反向恢复 URL 后逐字相同。CSS 和 NGINX 不改，不用完整本地 dist 覆盖线上静态。

精确后端命令（工作目录项目根）：

```sh
PYTHONPATH=/Users/liyulong/.codex/worktrees/cn-resume-optimizer/offersteady/apps/backend:/Users/liyulong/.codex/worktrees/cn-resume-optimizer/offersteady/apps/backend/tests /Users/liyulong/liyulong/1_projects/offersteady/.venv/bin/python artifacts/cn-resume-optimizer-safe-edits-20261018/run-combined-tests.py
```

精确网页命令（工作目录 CN worktree）：

```sh
npm run test -w @offersteady/web -- --reporter=default --reporter=json --outputFile=/Users/liyulong/liyulong/1_projects/offersteady/artifacts/cn-resume-optimizer-safe-edits-20261018/web/web-vitest.json
npm run typecheck -w @offersteady/web
VITE_APP_ENV=production VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=cn-resume-optimizer-safe-edits-20261018.local npm run build -w @offersteady/web
```

主要证据位于项目根 `artifacts/cn-resume-optimizer-safe-edits-20261018/`：`source-and-backend-verification.json`、`combined-junit.xml`、`final-provider-junit.xml`、`safe-edits-http-wire.json`、`web/web-verification.json`、`web/overlay-manifest.json` 和 `independent-audit/local-core-review.json`。原冻结 wire 及历史发布 artifacts 不覆盖。

## 交付和限制

本地合成预览为 `http://127.0.0.1:5178/test-previews/resume-optimizer.html?scenario=partial`。它演示局部成功、具体失败/退还、历史和原模拟面试入口，不调用真实模型或产生费用。

真实模型质量须以单独隔离 QA 结果说明；准备脚本或本地测试通过不代表已调用模型。当前不读取用户原简历或重放原失败任务。后续上线仍须重新冻结实际运行组件、通过完整七门禁、固定候选及归属恢复，不能结束真实用户工作制造空闲。

## 真实长简历 QA 最终结果

从实际国服 6f2a53f5… 父镜像生成的隔离候选 f6dbe8fd… 通过最终 verify：完整 230 源、202 路径/schema、340 Settings、原配置和非目标/原静态保持，真实 DOCX/PDF 探针通过，网络/数据库/文件写/线程/子进程/依赖解析/lifespan 七类副作用均为零。未启动应用生命周期或切换任何线上组件。

三例仅直接 Provider，各一次请求，总计三次：

| 合成输入 | 字数 | 模型耗时 | 有效改写 | 未采用 |
| --- | --- | --- | --- | --- |
| 混合后端项目 | 2830 | 19.693 秒 | 5 | 0 |
| 受控表格和 JD | 2879（规范化后） | 21.130 秒 | 7 | 2 项无实质变化 |
| 精确英文词与重复短句 | 2967 | 22.835 秒 | 5 | 0 |

三例都通过实际结构、依据和事实守卫，确实生成了不同于原文的合规稿。本次模型样本没有事实违规提议被过滤，不能称真实模型已覆盖这一负例；违规提议与合格提议混合的行为由 42 项 AI eval 和真实 PG/API 回归证明。三次成功不代表用户原失败任务已重跑成功、所有未来模型采样均成功或生产长期耗时改善。

首轮测试工具曾在 Docker/runc 初始化嵌套只读挂载阶段失败；安全分类确认容器进程未启动、模型请求零。旧目录和 consumed marker 完整保留，未重试旧标记。经合同第九节窄修正、26 项工具回归及独立审核，新目录使用预先存在的 0600 合成 case 和单目录只读挂载，实际 Linux 禁网演练通过后才恢复原三次预算。产品源、Prompt 和输入没有因这次测试工具修正而变化。

每例均通过完整七门禁、实际禁网探针、同命令形状挂载演练和单次持久标记，未读取用户简历/原模型输出，未创建业务任务、扣费或写入资料。私有配置/原 stderr 留在服务器，公开证据仅固定结果/摘要/时长/计数。`qa/actual-case1-v2.json`、`actual-case2-v2.json`、`actual-case3-v2.json`、`actual-verify-v2.json` 和 `first-attempt-safe-diagnosis.json` 保留各阶段真实结果。线上仍为原 b955…/6f2a… Backend 和 029e…/20d6… Web，尚未发布本轮增量。
