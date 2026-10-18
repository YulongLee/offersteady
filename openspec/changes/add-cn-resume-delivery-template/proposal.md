## Why

专业单栏与商务深蓝两轮共11/11本地任务已完成，最终769模板通过170项后端、14彩页/2灰度与真实本机下载验收。用户现明确授权将已验收简历优化商务PDF模板部署国服，完成后由其测试；原本地过程与旧失败保持历史。

## What Changes

- 国服已有 PDF 下载默认采用一套专业商务深蓝、单栏 A4 简历模板：强化抬头、克制的深蓝强调色、淡色栏目背景/左色条、经历子标题重点及留白；正文保持高对比与舒适阅读，延续完整换行和自然分页。
- 对当前已保存稿进行确定性结构识别与排版，保持全部可见内容、事实和原文顺序；识别不明确时按普通正文保留，不调用 AI 重写、不改变已保存稿或补造姓名、日期、经历与技能。
- PDF 使用内嵌中文字体和真实可选择文字，不含产品品牌、评分报告、照片、技能进度条或远程资源。长简历自然分页，不通过删内容、极小字号或强制一页实现美观。
- 保持原下载按钮、API、事实确认、当前 revision 与 owner/source 删除屏障；下载不重复收费。Word（DOCX）继续使用原导出，不改变 Global 共享格式模块。
- 已交付纯合成中文/中英文/多页PDF、逐页渲染图和验证报告；1–5.x只本地，现6.x按[生产追加规范](production-release.md)上线已验收CN renderer与service默认PDF分发。默认仅Backend单组件，原Web下载入口可用，Global/DOCX/生成及费用保持。

非目标：AI 内容或 Prompt/评测策略变更、模板商城/多主题、所见即所得编辑器、新预览接口/持久化缓存、原文件排版复刻、自动投递、收费/次数/DB/依赖变更、Global/助手/模拟面试等其他功能、Git 提交推送。本轮不得调用真实模型或读取真实用户简历作测试。

## Capabilities

### New Capabilities

- `cn-resume-delivery-template`: 国服已保存稿的专业 PDF 默认模板、保守内容映射、真实文本与分页、私有有界导出和本地可审查验收。

### Modified Capabilities

无已归档主能力修改；既有国服导出规则仍见 [CN 导出规范](../add-cn-resume-optimizer/specs/cn-grounded-resume-review-and-export/spec.md) 与 [合同](../add-cn-resume-optimizer/contract.md)。本变更仅对 CN PDF 模板表现追加优先规则；原 DOCX、API、事实确认及权限语义保持。

## Impact

- 以新鲜只读实际镜像 `f6dbe8fd…` Backend 的完整 230 输入及国服工作区逐字绑定为基线；实际 Web `2124eee8…` 保持。本地证据位于 `artifacts/cn-resume-delivery-template-20261018/`。
- 新增 CN 专用 PDF renderer，仅更换 CN service 默认导出分发。共享 `resume_optimizer_export.py`、Global service、原 DOCX 与其他运行时输入保持；复用已有 ReportLab 和已许可的内嵌字体，不新增依赖。
- 只在授权导出时延迟加载排版资源，以有界内存/锁保护渲染，不接入面试实时执行池；文件即时返回，不保存到 OSS、数据库或日志，不增加外部数据处理。
- 本地严格校验、合成回归/真实PDF及逐页视觉已通过；用户现授权按生产追加规范重新冻结实际基线、禁网候选探针、重复七门禁、固定digest切换与独立验收，之后由其正常账号测试。

## 2026-10-18 商务深蓝外观追加（5.x）

此前黑白版的7/7任务、最终renderer6d466a27…与D1–12验收保留为历史，不代表新外观已完成。本次明确修订黑白风格为受控高对比商务深蓝，允许仅CN PDF的局部填色细栏、栏目淡底/左色条、字距字号与层级留白调整；数据模型、全部事实/顺序、已保存稿、分页守卫、字体/依赖、API/费用/双重权限复核不变。新增D13外观验收，追加约4项本地任务；不新增模板选择/照片/图表/评分/品牌或接口，不更新Web/Global/DOCX/生成，真实模型/线上/Git仍未授权。5.x仅规划，root严格校验和设计冻结GO前不得实现。

## 用户授权国服上线（6.x）

用户已明确要求部署国服，最新授权仅将本地最终769商务PDF和最小默认分发生效；原优化主体/计费/AI/Web已上线，不夹带重发无关内容。执行[生产追加规范](production-release.md)，默认Backend-only两源，Web/static/NGINX及其余组件全部非目标；只有root另行冻结并修订具体Web范围才可扩大。重新绑定实际image/完整源/schema/Settings/配置/非目标，禁网纯合成PDF/Word/字号/全文探针、完整七门禁至少两次加实际Backend TCP8000/netns临近保守检查、固定digest/精确归属切换恢复、独立verify和脱敏短观察。真实活跃用户则defer保留原服务；unknown/readfail/drift停止，不结束面试或清理jobs。11/11本地与所有旧记录保持；无模型/真实用户简历/生产测试钱包任务/压测/Git/Global/助手授权。当前6.x为计划，实际基线/GO/候选/发布结果待真实记录。

6.x新鲜实际绑定已取得（007c9fdd…，详见生产规范）：Backend-only230→231两源，Web为第7非目标。既有金融门禁只保护订单/近期callback，不操作任何后台worker。额外TCP读数非零defer、未知停止；仅恢复本次严格双确认已退出candidate时可用明确stoppedProcessProof替代读取，不能当作读到0或用于正常部署。现有graceful机制不变，不承诺零在途/零竞态；root生产strict/实施GO与实际候选/部署仍待执行。
