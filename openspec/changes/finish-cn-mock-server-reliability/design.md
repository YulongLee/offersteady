## Context

状态：apply-ready；用户2026-10-31明确授权完成“不需更新伴随程序”的模拟面试修复。生产来源和本地已完成网页补丁见proposal引用。历史10月15日设计已有对应验收场景，当前实际基线仍缺少这些服务端补修，不能因旧tasks完成就认为现运行代码已具备。

## Goals / Non-Goals

目标：提交不再等待旧ASR关闭；旧音频先隔离，资源仍有界跟踪；断线清理幂等；失败可安全定位；与现有网页补丁组合交付。

非目标：本次自动部署、Git提交推送、助手升级、国际服或其他功能、模型/Prompt/输出质量策略、重试次数、收费/配额/60分钟规则、数据库/配置/新依赖。诊断不改变AI行为，无需新增内容评测；用现有合成模型响应做隐私和流程回归。

## Decisions

1. CN有效submit使用非等待清理：持久化状态转换、停止计时、撤销旧capture后，尽快发布generating并启动生成。进入新listening（listen/resume）也不等待此前已隔离的旧清理，否则下一题虽已生成，收音又被同一旧连接阻塞。保留pause/end/replay/detach/shutdown及Global原本的等待策略。拒绝直接丢弃任务或在事件循环里同步close。
2. 复用现有固定4线程执行器，分别跟踪observer和实际future。observer取消不取消实际关闭；取消前尚未执行或正在排队也保留资源归属。仅实际future完成才注销跟踪；drain超时不遗失后台工作。新轮采用独立capture，旧回调/清理不能影响替代资源。
3. CN收音端点finally容忍RuntimeError与WebSocketDisconnect；原有registration身份比较继续保护替代连接，不在异常处理中强制重建/终止用户会话。
4. CN诊断使用固定阶段、结果、错误枚举和非负耗时；只关联随机32位trace，不用账号/会话/设备ID。HTTP仅记录100–599整数状态。不记录异常正文、URL、headers、供应商响应、简历/问题/回答/音频、凭据。未知分类降为internal_error，未知字段不透传。日志失败不能改变业务结果或吞掉CancelledError。
5. Job与生成器共享上下文内随机trace，结束恢复ContextVar，隔离并发任务。记录resume_read、context_validation、slot_wait、provider_request、response_parse、output_validation、generation_total及安全清理事件；原provider_fault分类/失败计数/同场重试/报告简历fallback与deadline取消保持。
6. Global日志保持禁用，供应商调用与返回流程保持；无真实provider或用户测试。已知Global专用源码缺失导致的旧测试收集限制单独记录，不“修复”到国服。所有工作保留此前已测试的网页、权限与性能增量，不用完整旧源码覆盖。

## Risks / Trade-offs

- 旧ASR在后台持续较久 → 固定执行器、准确future跟踪、超时drain和旧epoch隔离，覆盖取消及替代连接场景。
- 诊断扩展泄漏私密值 → 白名单字段和值，合成隐私标记注入所有故障分支验证，无原始exception/response输出。
- 更详细分类改变重试/计费 → 保留原exception类型、公开文案、provider_fault判定和调用次数，进行真实本地PG账务/截止回归。
- 模型自身等待仍然存在 → 仅消除本轮确认的旧连接关闭串行等待，不承诺整体出题或API P95百分比。

## Migration Plan

本轮交付本地代码、检查结果和源文件清单；用户明确要求部署后，再核对目标实际镜像、静态图与用户工作门禁，执行最小CN Backend/Web增量及可回滚验收。原已本地验证的Web代码须保留，不可全量重建覆盖历史组件。

## Production addendum — 2026-11-01

用户已授权国服发布。只在实际Backend `sha256:3e56917daba635e780d9bd728694d823494b40a6ab67a9968c5371c1378abb3e` 231份输入及Web `sha256:99822e10e7b516aefe4ad96248f9eea631d90b057cb77b8dd386cff4830516fb` 353份公开字节之上叠加已冻结mock源码。Backend只替换4份并新增diagnostics，不改变配置/依赖/schema。Web只替换mock页面函数/专用播放器/3条新增CSS和反向依赖版本引用，保留报告/Word、共享API/初始化/状态优化及全部旧静态文件，兼容回退同时保留新chunks。

复用已审阅的冻结Compose/环境、归属journal、七项只读门禁和TCP8000门禁；原控制器入口不执行。当前容器归属锚点与财务历史分类锚点分开：后者继续固定为2026-10-21原进程 `1792600214792`，不得因本次或候选重启放宽。每次切换前重读全部门禁，unknown/读取失败同样停止，无准备页例外，不终止真实用户。私有配置只留服务器，实际镜像探针禁外部网络/DB/文件写入，仅受控合成内存工作。失败只在归属可信及门禁允许时回退固定原镜像/兼容Web，无DB或账务回滚。
