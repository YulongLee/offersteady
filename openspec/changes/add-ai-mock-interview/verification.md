# AI 模拟面试本地验收 — 2026-09-26

当前状态：**已按用户“部署完成后我这边测试”的最新授权部署国服；未发布/升级助手，未更新国际服。真人麦克风验收仍待用户上线后测试。** 下文早期“未部署”等记录为历史状态，最新发布见文末。

最新热修：2026-09-26 04:05:22 +0800 已发布准备阶段旧助手 unknown 权限兼容修复，见 [热修发布记录](../../../docs/releases/cn-mock-readiness-20260926.2.md)。真实麦克风完整验收仍未完成，不把准备检查通过视为物理收音验证。

命名后续（仅本地，未部署）：按用户要求将国服功能名改为“模拟面试”，涉及桌面/移动端导航、新建默认标题、未开放提示和新账本描述；保留 AI 面试官身份披露、旧记录标题/账本，不改金额、路由与交互逻辑。48 项前端测试、41 项后端标签/隔离/就绪测试及 Web 类型检查通过，OpenSpec strict 通过。导航测试明确模拟功能已开放，不关闭原默认隐藏门禁。任务 5.8 完成，真人验收 6.5 仍待完成；未操作服务器或助手。

## Word 报告下载增量（2026-09-26，仅本地，未部署）

- 按用户追加需求，已完成报告顶部新增“下载 Word”，导出可编辑 `.docx`。包含场次名称、目标岗位、部分/完整状态、总体与分项评分、总结、逐题问答、证据、优点、不足、建议和下一次练习重点。
- 使用当前已加载报告在浏览器生成；按需加载既有 docx 依赖并复用普通复盘下载工具，不更改普通复盘导出、后端、模型、助手、计费或保存上限。零分保留零分，无评分保留“不评分”，未回答不伪造反馈。导出中防重复点击，失败可重试，不修改报告。
- 82 项测试通过（8 个文件）：MockInterviewPage、mock-interview-word-export、MockPlaybackIndicator、mock-interview-client、interview-review-word-export、interview-review-export、App 及 mock-interview-release-contract。覆盖十题长回答、多行/中文/Unicode、非法 XML 字符、安全文件名、临时下载资源回收、无后台请求与不改变原数据、评分空值及失败重试。
- Web 类型检查与生产构建通过；本地构建标记 `mock-word-local-verification`，既有构建流程只读拉取公网已发布价目，未发布构建产物。
- Chromium 1440px 与 390px 实际下载并校验 DOCX 内容；下载前未加载 Word 依赖，下载未发送 API 请求，无页面错误/横向溢出。已人工检查两种宽度截图。可用 [本地回归脚本](../../../apps/web/scripts/verify-mock-report-word.cjs) 重跑，需本地合成预览运行于 4291 端口。
- 文档技能检查发现隔离 LibreOffice 缺少中文字体，使用本次临时 fontconfig 指向已有系统中文字体后重新渲染，未改系统/运行库配置或安装字体。实际网页下载样本 1 页、应用导出器的较长合成样本 2 页，所有页面已检查，中文、换行、评分和分页正常；未使用真实用户资料。未宣称已人工测试所有 Word/WPS 版本。
- OpenSpec strict、变更 Markdown 本地链接及 `git diff --check` 已校验。任务 5.9、5.10 完成；原真实麦克风验收任务 6.5 仍待用户完成。
- 本轮没有部署、重启线上服务、升级助手或推送 Git。上方正式发布版本保持不变。

## 已实现

- 国服默认关闭的独立入口、创建、简历准备、机器码绑定、AI 面试官、最多十题手动推进、报告。
- 创建 100 积分＋累计实际朗读/回答每开始一分钟 5 分；北京时间每天有效时间会员前三场全程免费，第四场起收费，创建时锁定本场类别。准备、生成等待、暂停、断线、报告不计分钟费。
- 原子创建/扣费/会员名额、幂等、跨日恢复、每人两条，删除保留财务及免费配额元数据，不自动覆盖。
- 读取选中的本人简历解析正文，独立出题、报告与指定 Qwen realtime TTS；不修改原快答模型配置。
- 独立麦克风通道、按题授权、播放期间拒收音频、迟到转录丢弃、暂停后保留页面已有回答、手动校正不被覆盖。
- 独占控制租约、断线取消任务、结束解绑、离线过期、逐轮 ASR 实例和有界音频。ASGI 取消不打断最终清理；助手准备→进行中不重建收音连接。
- 无回答不评分；引文必须来自该题原回答；示范结构仅逐字引文＋待填槽位。验证过的连续三次首题供应商失败会一次性退本场积分/恢复免费次数，客户端不能声明故障退款。
- 原始音频不保存，历史不复制完整简历，测试均用合成数据。

## 已执行自动验证

- 后端最新合并批次：**226 passed，12.26 秒**，仅既有 Starlette/httpx 弃用提醒。隔离的本机 PostgreSQL，只使用随机合成账号；普通数据库和 Redis 环境变量为空，测试数据库为本机临时容器，不写入线上。
- 后端覆盖原计费、手机音频、空闲生命周期、多语、编程、控制面、问题检测、资源回收、快答、截图、联网；新增七个 mock 测试文件覆盖状态机、文本/TTS、账本并发、身份隔离、音频和实际进程内 WebSocket。
- HTTP/WS 集成：非法凭证、跨用户、错误机器码、双页控制、伪造字段、播放窗口拒收、浏览器＋助手通信、音频转写、提前结束及单次扣费/清理。
- 音频重复测试：100 个合成轮次结束后 captures/draft 为零；100 个独立 ASR 适配器均关闭。这不等同生产 RSS 必须恢复初值。
- 后续新增八场完整十题合成会话：每题双次提交仍只出十题、一次报告、一笔创建费和一笔分钟费；每场结束后采集/转录/控制器/后台任务回到零。该测试连同其他 PostgreSQL 测试 **28 passed，12.39 秒**；与合并批次有重叠，不能直接相加。
- 网页组件和音频测试：**46 passed**（MockInterviewPage、mock-interview-client、App），包括暂停续答、旧轮丢弃及人工编辑不覆盖。
- 助手相关测试：**56 passed**（mock-microphone、permission-session-separation、dual-channel-publisher-recovery、audio-core）。
- Web、desktop 类型检查通过；Web 生产构建、desktop 本地构建通过。没有打包安装包、公证或上传；正式版本号未变。
- Web 生产构建使用 VITE_APP_ENV=production、VITE_API_BASE_URL=/、VITE_PUBLIC_APP_VERSION=mock-local-verification；既有构建流程只读获取已发布价目。
- 创建页/工作台/报告各验证 1440px 与 390px，共六个合成页面；无横向溢出、无页面错误；人工复查了工作台配色与布局。演示不连接生产、不收费。
- 已执行 OpenSpec strict、git diff --check 及本变更 Markdown 本地链接检查，通过。

后端重跑方法：设置 OFFERSTEADY_DATABASE_URL=''、OFFERSTEADY_REDIS_URL='' 及隔离的 OFFERSTEADY_TEST_DATABASE_URL，执行 .venv/bin/python -m pytest 对以下 apps/backend/tests/ 文件：

test_interview_usage_billing.py、test_interview_audio_mode.py、test_interview_idle_lifecycle.py、test_interview_language.py、test_interview_programming_preference.py、test_realtime_control_plane.py、test_realtime_question_detection.py、test_realtime_resource_cleanup.py、test_realtime_session_reclamation.py、test_realtime_asr_gateway_lifecycle.py、test_answer_failure_contracts.py、test_screenshot_inline_delivery.py、test_web_search_chat_integration.py，以及所有 test_mock_interview_*.py。

## 真实百炼联调

脚本：[verify_mock_interview_providers.py](../../../apps/backend/scripts/verify_mock_interview_providers.py)。显式 --tts-asr / --evals 才调用供应商，合成输入，不保存音频/密钥。

- TTS→ASR 回环：首音频 **0.616 秒**；约 6.04 秒测试音频（含尾部静音），9 次转录更新，总联调 11.67 秒。正确识别“这是一次模拟面试收音测试，我使用唯一约束避免重复写入。”，结束后采集数和供应商连接数为零。
- 仅证明 TTS 权限、音频格式及 ASR 协议连通，**不是物理麦克风、耳机、扬声器回声或系统权限验收**。
- 九条评测定义：六次真实文本调用、一次无回答本地报告、两个确定性回归场景（十题上限/重复题）不调用模型。
- 最后一次真实运行：四个问题 1.17–2.18 秒；两个报告 3.61–4.22 秒。结构和逐字引文校验通过，人工核对岗位相关、上下文追问、注入不执行、无证据不评分、部分报告及未编造成果。
- 早期运行曾发现额外追问、示范回答编造百分比/定性成果；已加输出边界和回归，最后一次输出未再出现这些问题。有限合成样本不能保证所有未来回答质量。

## 原创面试官资产

内置 imagegen 模式生成、视觉检查后保存：[interviewer-v1.png](../../../apps/web/public/assets/mock-interview/interviewer-v1.png)。原创虚拟人物，不是外部真人照片；未用外部生成命令。

最终提示词：

> Use case: stylized-concept. Asset type: original AI interviewer portrait for a dark mint-green interview practice web application. Primary request: a fictional professional female AI interviewer, bust portrait, age around 35, warm attentive expression, dark simple blazer over light neutral blouse, subtle stylized 3D editorial realism, clearly a polished virtual character rather than a photograph of any real person. Composition: centered head and shoulders, portrait canvas 3:4, some headroom, subject filling frame, looking toward the viewer. Backdrop: minimal deep charcoal navy (#101821) studio, subtle soft mint accent rim light, no decorative clutter. Lighting: soft flattering natural studio, calm and welcoming, refined high-quality materials and believable facial details. Constraints: one person only, no text, no logos, no watermark, no border, no UI, no props or desk, do not resemble a celebrity or known real person. Designed to remain readable at 320px width.

## 头像下方播放声波增量验收（本地）

- 新增实际浏览器 PCM 输出旁路分析与独立声波组件，21 条声波、最多 25 Hz 刷新。采样不接触麦克风、不发送计费命令、不调用供应商、不保存音频；分析器异常只停动效，不打断音频。
- 音量变化、首音频等待、静音、自然播完、停止、关闭/断线、AudioContext 暂停、取消订阅及减少动态效果均有自动验证；播放结束后取消动画循环，静音时不伪造跳动。
- 最新前端批次 **53 passed，4.19 秒**：`npm --workspace @offersteady/web run test -- src/mock-interview-client.test.ts src/MockPlaybackIndicator.test.tsx src/MockInterviewPage.test.tsx src/App.test.tsx`。仅既有 Node localstorage-file 提醒。
- Web 类型检查及生产构建通过，环境参数沿用上文的本地验证值。OpenSpec 严格校验通过。
- 真实 Chromium 播放本地合成 PCM 测试音，确认声波实际变化、自然结束和停止后清零、减少动态效果时保持静态。1440px / 390px 创建、工作台、报告页面无溢出、无页面错误，另保存两张播放中截图并人工检查。手机端将状态区放到照片下方，避免遮挡人脸。
- 预览地址：`http://127.0.0.1:4291/test-previews/mock-interview.html?view=workbench`，顶部“播放声波演示（合成测试音）”不冒充正式 TTS 女声，不连接生产。
- 本次只修改本地前端及验收文件，未改后端/助手/计费/收音，未部署。此增量验收不替代下列真实麦克风和正式发布门槛。

## 2026-09-26 国服发布前核查

用户再次授权部署且要求不影响现有功能。本次只执行只读核查，未切换服务：

- 北京时间约 03:05，国服 `/healthz` 返回 HTTP 200、status ok；`/offersteady-build.json` 返回 production、同源 API 配置。健康探针成功不等于所有业务端到端验收。
- `/api/v1/mock-interviews/capabilities` 返回 HTTP 404，线上尚未提供本次模拟面试能力，不能仅发布声波组件就声称全链路上线。
- 本地 `mock_interview_runtime.py` 明确要求设备 `mockInterviewProtocol: 1`，否则返回更新助手提示；该能力目前仅在本地新版助手实现。原有正式助手不足以完成新模式的按题收音。
- 当前 35/37 项完成。任务 6.5 真实设备验收仍未完成，任务 6.8 不标记完成。依据发布验收要求暂停切换，待真实机器码/麦克风验收及正式助手打包、公证、上传范围确认后继续。
- 未 SSH、未查询生产用户会话、未停止面试、未更新配置或数据库、未部署任何容器。没有据此宣称线上当前无进行中面试；实际切换前必须即时重新核查。

## 2026-09-26 现有正式版助手兼容增量（本地）

本节覆盖之前“必须升级助手”的实现限制，不代表新增助手已发布。用户明确不升级助手，本轮仅修改网页、后端和本变更文档/测试；已有未发布的桌面实验代码保留但不作为兼容验证依据，也不打包/上传。

- 后端复用已发布助手 v2 的 `/realtime-speech/publishers` 和 `/ingest-ws`，保持 `mock` 会话和 `mobile` 单麦克风音频模式，独立令牌/轮次/ASR/账本。现有普通入口不允许消费 mock 令牌，不调用普通回答或普通分钟计费。
- 准备时只要求已绑定的现有正式助手在线、v2 麦克风协议和麦克风权限，不再强制 `mockInterviewProtocol: 1`。准备就绪与实际音频连接分开；连接等待不开始回答分钟计时，重连不自动恢复收音/计时。
- 序号去重、跨轮旧片段/系统声道/播放时段丢弃；固定准入 epoch，关闭后不能追加下一题；格式/大小/速率有界，错设备、过期/伪造令牌和未来时钟拒绝。播放结束后 1.5 秒准备间隔不收费，覆盖已发布 VAD 最多 1.2 秒尾段。电脑需自动校时，不静默调整时间戳。
- 旧助手仍可能采集上传提问时段音频，后端丢弃，不转写/不保存；已在准备页说明，不能宣称物理麦克风立刻停止。每场单发布记录，结束/网页断线清除进程注册和发布凭证，避免刷新累积。
- 最新模拟面试后端批次 **114 passed / 16.10s**：`test_mock_interview_*.py`；隔离本地临时 PostgreSQL，仅合成账号，普通数据库及 Redis URL 置空。包括真实进程内 HTTP→v2 WS→独立 ASR 路径、binary/base64 两种格式、无升级标识的准备/开始、重复终帧、断线停费、重连偏移、结束清理、100 次注册清理。供应商使用测试替身，不冒充真实物理收音。
- 既有回归 **131 passed / 3.93s**（上文列出的普通业务测试，不含 mock 文件）；追加旧传输/运行状态/转录抑制/预取回归 **46 passed / 0.95s**：`test_realtime_transport_v2.py`、`test_realtime_runtime_evidence.py`、`test_realtime_transcript_suppression.py`、`test_realtime_prefetch.py`。三个批次合计 291 个不同后端用例。
- 前端 **55 passed / 3.21s**：MockInterviewPage、mock-interview-client、MockPlaybackIndicator、App；增加准备阶段无音频连接也可开始、收音准备与等待期间不发送 listen、连接就绪只发送一次等回归。Web 类型检查、生产构建通过；只读获取既有生产价目，不写入线上。
- Chromium 合成预览覆盖首页、准备页、工作台、报告，1440px/390px 共八页无溢出/页面错误；声波变化、自然结束、停止及 reduced-motion 验证通过，人工检查准备页手机截图。准备页预览 `http://127.0.0.1:4291/test-previews/mock-interview.html?view=preparation`，明确不连接生产、不计费，不是实际麦克风验收。
- OpenSpec strict 和 diff whitespace 校验通过。仍存在既有 Starlette/httpx、Node localstorage-file 提醒，无测试失败。浏览器检查首次因默认 Node 路径未找到 Playwright 而未运行，改用应用提供的依赖路径后完整通过；没有为此安装新依赖。
- 未升级或重启助手，未访问生产用户数据，未 SSH、未切换服务器、未部署国服/国际服、未提交推送 Git。真实设备验收 6.5、部署 6.8 继续未完成。

## 剩余发布门槛（以兼容方案为准）

1. 使用现有安装版助手连接隔离本地后端，完成真实机器码、麦克风、耳机/外放、暂停、重播、刷新和播放中结束验收。自动协议测试不等于实际收音通过。
2. 已跑八场完整合成会话及故障/取消/恢复用例；仍不代表生产容量压测或真人听感验证，不能宣称生产内存指标已验证。
3. 本轮不需要也不允许发布新助手；若真实设备验收发现兼容限制，先修后端/网页并重新验收，不能静默改成强制升级。
4. 全部门槛通过后读取国服实际基线，只合入本变更；确认无在线面试、备份/回滚就绪，再执行已获授权的国服部署。

国服线上未改动，未 SSH、重启、迁移线上数据库，未推送 Git。其他工作区改动保留，不能直接部署整个脏工作区。

## 2026-09-26 国服正式发布（最新状态）

- 用户再次明确授权部署后自行测试；6.5 真实麦克风验收保持未完成。只发布国服，不打包/公证/上传新助手，不推送 Git。
- 发布基于实际运行的国服后端 `answer-errors-20260925-1` 和网页 `quick-stage-20260923-1`，在独立目录逐项合并 mock 增量，不覆盖本地/线上差异。保留国服合作伙伴功能、旧资源回收逻辑及最新快答/截图修复；后台用户搜索容器未动。
- 候选基线第一次回归发现遗漏三处截图 mock 隔离守卫，补齐后重测 **291 passed / 18.15s**。未替换普通截图算法或账本实现。
- 服务器保存的 App 测试夹具早于已发布的手机模式/助手版本检测，初跑有 7 条失败；换用与同一 App 源码版本匹配的本地回归夹具后，候选前端 **55 passed / 3.19s**，类型检查及生产构建通过。不为适配测试放松普通面试的既有助手校验。
- 发布检查补上 Nginx 的模拟面试列表/详情路由，避免直接进入或刷新 404；基于实际线上配置，只增加该路由。实际候选配置测试 **9 passed**，Nginx 检查成功，候选容器验证新路由、普通面试、笔试、合作伙伴、头像资源均为 200。
- 国服实际运行环境、真实百炼凭证的合成 TTS→ASR 检查通过：首音频 **0.559s**，6.60s 音频，总计 **11.48s**，10 次转录更新；结束采集和供应商连接为零。9 个评测场景中 6 次真实文本调用、1 个无回答本地报告、2 个确定性用例；人工复核角色问题、注入边界、逐字证据和不虚构经历。
- 镜像编译首次被基线自带 macOS `._web_search_gateway.py` 元数据阻断，改为编译时跳过 `._` 文件后成功。没有因此删除线上业务文件。
- 切换前多次即时检查：进行中面试、最近准备中的面试、页面租约、近期音频、未完成回答均为 0；生成并验证 PostgreSQL 备份，备份生产配置，再执行有锁等待/语句超时保护的加法迁移 0051。
- 仅重新创建 backend/web；容器前后对比确认 admin、PostgreSQL、Redis、资料处理、统计任务均未重启。仅增加 `OFFERSTEADY_MOCK_INTERVIEW_ENABLED=true`，运行环境其余键值逐项校验相同。
- 线上健康、首页、模拟面试路由、支付状态、网页状态和管理员站点检查通过；未登录访问模拟面试 API 被 401 拒绝，公网 WebSocket 到达应用并拒绝无效凭证；能力接口返回 enabled=true / companionUpgradeRequired=false。
- 最新 Web 标识为 `cn-mock-interview-20260926.1`。关键源码及正式助手下载清单 8 个文件哈希与候选匹配。
- 回滚保留原网页与兼容 mock 记录的基线后端镜像；只关闭功能/回退服务，不删除已创建会话或积分账本。详细记录见 [国服发布记录](../../../docs/releases/cn-mock-interview-20260926.1.md)。
- 没有创建生产测试账号、实际扣除用户积分或声称真人麦克风/外放回声已验收。上线后用户重点测试机器码绑定、朗读后收音、回答完成、报告和结束清理。

## 2026-09-26 准备阶段兼容热修

- 线上实际症状为：助手在线、绑定代际与简历正常，1.3.2 主进程心跳固定上报 microphone=unknown。旧准备检查严格要求 granted，且吞掉失败原因。此 unknown 不代表 OS 拒绝授权。
- 仅对无专用 mock 标识的 v2 助手允许延迟确认权限；显式 denied/restricted、协议不匹配、离线、错设备/代际、非 mock/已结束会话仍拒绝。权限状态不写回、不伪装 granted；OS 继续控制实际采集，回答需认证收音通道，等待不启动回答计时。
- 准备消息包含结构化原因；绑定成功提示不再冒充错误，立即请求状态刷新并在状态到达后消失。普通面试、机器码协议、模型、账本与配置不变。
- 修正原测试夹具硬编码 granted 的盲点，改用真实权限解释器，并在 binary/base64 HTTP→WS 完整回归中重现正式助手 unknown 心跳。新增未知/缺失、拒绝、非法状态、专用协议未知、离线、绑定代际、错设备、生命周期拒绝及同场无重复创建/等待不计费测试。
- 在当前国服实际基线的独立候选运行：**308 后端测试通过 / 18.43s；58 前端与路由测试通过 / 3.50s**。Web 类型检查/生产构建、OpenSpec strict、diff whitespace 通过。前端新增测试首次因页面有两个 status 元素失败，给助手状态明确的无障碍名称后重跑通过；不忽略失败。候选 Nginx 首次未连接 Compose 网络导致上游域名无法解析，在正确网络重跑通过，未改 Nginx 配置。
- 切换前重复核查：live 面试、live 页面、音频、未完成回答为零；唯一 mock 记录为 preparing，用户请求修复并部署，原准备数据保留。新增门禁检查 mock 阶段，非 preparing/completed 不切换。
- 只替换后端一个 mock runtime 文件和网页 mock 准备组件；在原镜像上构建增量镜像，旧静态资源保留。备份数据库并校验可读；无迁移、无配置变更。镜像、运行环境以及其他容器 ID/启动时间逐项校验通过。
- 上线后只读快照使用已部署就绪函数检查实际设备/绑定：ready=true、permissionDeferred=true、phase=preparing、resumeSelected=true、billedMinutes=0；这不是伪造登录或实际点击开始，不会写入用户会话。未新建生产测试场次。
- 6A.1/6A.2 完成，6.5 真人麦克风/耳机/外放仍待用户验收；未升级助手、未更新国际服、未推送 Git。
