# 国服商务深蓝简历模板本地验收 20261018.2

状态：新版实现、本地自测、真实PDF逐页验收及双根strict/链接检查通过，当前总11/11本地任务完成；**未部署国服**。用户认为上一版太素，本轮在[同一OpenSpec](../../openspec/changes/add-cn-resume-delivery-template/proposal.md)内追加商务深蓝外观；[上一版本地记录](cn-resume-delivery-template-local-20261018.1.md)及全部历史样例保持。

新版用深蓝抬头集中呈现原姓名、短行和联系方式，浅蓝栏目条及克制的teal装饰区分经历、项目、技能，正文仍为可复制的真实中文。保持单栏A4、45pt侧边距和10.2pt正文/14.8pt行距；常见抬头约110pt，超180pt完整回退为深色独立段落。仅展示原文，不推断身份/角色、改写事实或改变顺序。

本轮只有国服工作区的CN PDF renderer及其纯测试改变。service、原解析分类、Web/导航、模拟面试、Global/DOCX、现有字体、Prompt/模型、费用、schema、依赖及生产配置全部保持。没有生产连接写入、真实用户简历读取、模型调用或Git操作。

## 本轮实际验证

- 最终renderer SHA `76925432e1c8c7ac7801e8cc4978fba67641af65f8c1a7e748bf0593fc0f523d`，纯测试SHA `5bcde6dd7cf9403b4466ef28f02a2958bbd9e9ceaee7734c7ecbc46640f5733d`。9项核心输入重新冻结，其他7项非目标保持；旧230运行输入仍仅有前轮已授权CN service默认PDF分发差异。
- 后端 **170/170通过**，34.61秒，0失败/0错误/0跳过；包含81项新PDF、11项原共享导出、16项隔离PG/API、62项既有CN service。只有原第三方Starlette弃用警告。
- 10份纯合成PDF共 **14页彩色**，root逐页查看全部页面及两份用户样例共 **2页灰度**；A4、内嵌字体、全文原序、无主动动作、文字/矢量边界和行间无重叠均通过。实际文字与所在背景的最低对比约6.9:1，回退无白底白字。
- 工作经历/校园样例各1页；长混排、长URL、分页边界和长段落各2页；额外超高抬头回退、无title及长栏目各1页。独立另核11组抬头边界/12页的全文原序、180pt回退、浅白字背景和45pt边界；该机器边界审查不冒称全部逐页视觉。
- 初版长混排出现一行尾页。统一将经历前间距6pt微调为5pt后恢复2页，补真实PDF回归；没有缩小字号、删字或按样例特判。初稿报告保留，最终重新生成、检查全部14页。
- 本机真实HTTP **6项通过**：两份PDF返回字节分别精确等于最终交付文件、修改输入即时生成新内容、原Word同稿为真文件、外来Origin阻断、本地入口可达。test-only桥接代码与上轮一致，仅绑定127.0.0.1且不转发线上、不记录正文。
- 本轮没有重复运行Web/browser/typecheck/build。相关源码完全未改；前轮586项Web与83静态排除检查仅作为已核SHA的历史基线，不能当成本轮重跑。最终PDF的实际本机HTTP和170项后端检查属于本轮执行。

## 本地查看

- [商务工作经历样例](/Users/liyulong/liyulong/1_projects/offersteady/output/pdf/resume-template-business-experienced.pdf)、[商务校园样例](/Users/liyulong/liyulong/1_projects/offersteady/output/pdf/resume-template-business-campus.pdf)均为合成材料，使用同一个默认模板。
- [本地工作经历预览](http://127.0.0.1:5178/test-previews/resume-optimizer.html?scenario=template)及[校园预览](http://127.0.0.1:5178/test-previews/resume-optimizer.html?scenario=template-campus)继续使用原测试入口；下载实时调用新版renderer，当前编辑须先保存并确认事实。

证据位于主工作区 `artifacts/cn-resume-delivery-template-business-20261018/`：final-combined-junit.xml、pdf-generation.json、pdf-geometry.json、visual-review.json、preview-http.json、local-input-manifest.json及independent-audit/。

本轮仅合成本地验收，不代表真实用户简历、所有打印设备、招聘系统或线上容量已验证。PDF版式改进不新增收费；事实确认和已保存revision双重守卫保持。晚间用户另行确认后再进行生产准备，届时必须重新冻结实际镜像和完整输入、执行受保护增量验证；本地通过不构成生产发布GO。
