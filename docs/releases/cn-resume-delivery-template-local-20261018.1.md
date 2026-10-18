# 国服专业简历 PDF 模板本地验收 20261018.1

状态：本地开发、自测、最终PDF验收及双根strict/链接检查通过，7/7本地任务完成；**未部署国服**。依据[OpenSpec](../../openspec/changes/add-cn-resume-delivery-template/proposal.md)与[逐场景结果](../../openspec/changes/add-cn-resume-delivery-template/verification.md)，本轮无生产发布GO。

现在下载PDF会将当前已保存稿排成简洁专业的单栏A4简历，统一抬头/联系方式、栏目细线、经历与列表层级，保留可复制的中文文字，长段落和长简历自然分页。仅确定性排版，不额外AI重写、不新增或修改事实、不改保存稿/原简历；缺少结构时保守保留正文。

开发位于国服工作区 `/Users/liyulong/.codex/worktrees/cn-resume-optimizer/offersteady`。DOCX、Global共享helper、现有字体/依赖、生成/Prompt、事实确认/owner/source/revision双重屏障、模拟面试和收费保持。时间会员每天3次免费、其余100积分仍仅用于优化生成；下载不新增费用。

## 实际验收

- Backend **154/154通过**，30.013秒：65新PDF、11原共享、16新隔离PG/API及62既有CN service；Web **586/586通过**，typecheck/build通过。
- 最终renderer SHA `6d466a27fef9bc5454420e00913c8bbb3275b6264cabc80e370de446ccb3d7db`；9项核心输入与辅助Web源已冻结。实际f6/2124基线完整230原输入中229逐字保持，唯一既有变化为CN service默认PDF分发，AST独立审查通过；Web导航/模拟面试/资料/计费保持，Page只改一段说明。
- **7份合成PDF共11页**，全部真实文本/字体/A4/内容顺序/独立几何通过，root已逐张查看全部最终页面。两份用户样例各1页，长混合稿/URL/分页边界/长段各2页；无裁切、重叠、孤标题、空页或可避免首页巨大空白。
- **20项本机HTTP检查通过**，真实PDF58164bytes精确匹配浏览器保存revision2（含SavedDraftQA91），真实Word同稿成功。浏览器编辑→保存→重新确认→下载链路通过；模拟面试导航可见。
- IAB下载event未提供磁盘路径，未宣称捕获浏览器落盘文件；界面下载成功与相同保存稿的真实HTTP文件解析分开验证。
- 本地标准build83文件排除全部样例/桥接器，正式输入仅index/guide。独立额外13边界/68页机器文本与45pt边界通过，未把这些机器检查宣称为全部逐页视觉审查。

真实验收发现并修复两项排版问题：中文标点悬挂越界，以及超长段落被整段搬页导致首页大空白。均先复现再补回归，最终11页重生成重看；旧失败/旧SHA证据保留，不用于替代最终验收。

## 本地查看

- 工作经历样例：[打开PDF](/Users/liyulong/liyulong/1_projects/offersteady/output/pdf/resume-template-experienced.pdf)；校园样例：[打开PDF](/Users/liyulong/liyulong/1_projects/offersteady/output/pdf/resume-template-campus.pdf)。均为合成材料。
- [本地工作经历场景](http://127.0.0.1:5178/test-previews/resume-optimizer.html?scenario=template)；[本地校园场景](http://127.0.0.1:5178/test-previews/resume-optimizer.html?scenario=template-campus)。外层醒目标记合成预览，实际下载当前合成已保存稿。
- 编辑后必须先保存，并重新确认事实才能下载；不要将预览当成已更新线上服务。

本机桥接只绑定127.0.0.1，固定Origin/路径/头/大小上限，不转发线上请求、不调用模型、不保存请求正文，不进入生产build。无线上写入/部署、真实用户简历读取、真实模型调用、DB/配置/依赖改动或Git提交推送。晚间用户另行授权后，需重新核对届时实际镜像与完整静态并做受保护增量发布，不能直接用本地标准build替换线上静态全集。

证据位于主工作区 `artifacts/cn-resume-delivery-template-20261018/`：final-natural-combined-junit.xml、web-vitest.json、web-build-exclusion.json、local-input-manifest.json、pdf-generation.json、pdf-geometry.json、visual-review.json、preview-http.json、browser-qa.json及independent-audit/。未知/奇特原稿按正文保留，用户仍需核实事实；本地合成验收不承诺所有招聘系统或线上容量。
