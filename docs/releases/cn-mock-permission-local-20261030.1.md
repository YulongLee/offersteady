# 国服模拟面试权限恢复：本地开发 2026-10-30.1

2026-11-01更新：用户另行授权后，本地修复已与服务端补修合并发布国服，[生产记录及验收](cn-mock-20261101.1.md)。以下保留开发交接当时的状态。

2026-10-31跟进：此前列出的ASR关闭阻塞、断线二次异常和诊断不足，已在[服务端本地补修](cn-mock-server-local-20261031.1.md)完成并组合验证，仍未部署；下文保留10月30日的检查历史。

状态：开发和本地验证完成，**未上线、未提交/推送Git、未发布助手**。用户授权仅优化模拟面试，明确不改伴随程序。对应 [OpenSpec](../../openspec/changes/fix-mock-web-permission-readiness/proposal.md)；问题证据见[排查记录](../diagnostics/cn-mock-permission-20261029.md)。

后续按用户要求精简呈现：准备区长说明改为开始按钮下方默认收起的“使用说明”，移除画像区重复声明，缩短等待/播放提示，本地测试场景与记录默认收起。仅改文案与呈现，未改权限/控制/收费逻辑，继续不部署。此追加调整执行既有模拟面试/播放器44项测试、类型检查、严格Spec及差异格式检查通过，并在本地浏览器确认默认收起。上表完整网页684项与源码构建为此前功能完成时的记录，未在这次文案调整后重复全量构建。

## 后续复查与补修（仍未上线）

用户再次要求检查后，使用实际页面、播放器和合成WebSocket/AudioContext复现并修复了四处边界问题：

1. 切换场次或结束后，迟到的资料选择/绑定请求可回填旧页面。现在按页面/连接代际、场次、阶段和版本隔离结果及错误，覆盖A→B→A，合法当前结果仍正常应用。
2. 点击结束时，1.5秒收音等待计时器可能在服务器回包前发出listen。现在结束、暂停等控制意图立即取消本地计时与等待，不自动续听。
3. 换路由时，旧场次状态可能短暂为新场次建立额外控制连接。现在只有已加载场次与路由一致时才连接。
4. 全部PCM和audio_end已到达后，系统挂起AudioContext不会再有后续PCM触发错误，朗读按钮可能持续禁用。现在活动音频中断时停止旧队列并仅暂停当前题目一次，给出简短的手动继续入口；空闲、关闭和旧上下文事件不会误操作替代场次，关闭的上下文可重建。

复查最终结果：**CN Web 68文件696项通过，后端相关130项通过，类型检查与生产模式源码构建通过**。其中页面/播放器/真实播放器集成56项通过，新增12项回归；后端包括本轮权限52项、既有API、隔离PostgreSQL收费/额度/60分钟截止与功能隔离。播放器集成使用实际播放器排队合成PCM、挂起及旧完成回调，验证不会自动进入收音，再由用户操作恢复同题。真实物理设备尚未验收。

复查没有修改后端、助手或国际服；没有部署、Git提交或推送。新的临时测试数据库只监听127.0.0.1:58644，完成后移除，既有本地服务保留。证据在 `artifacts/cn-mock-permission-local-20261030/recheck/`、`player-review/`、`recheck-backend/`，另有生命周期原始失败/修复证据在 `artifacts/cn-mock-permission-recheck-20261030/`。

同时明确纠正原先对历史失败的笼统描述：**旧12项失败并非全部只是测试与源码不匹配，里面仍包含真实旧问题**。独立合成复现确认，提交回答在启动下一题前等待旧ASR关闭，等待上限为30秒，确实可能拖慢下一题；收音断线清理的socket.close如果抛WebSocketDisconnect，还会二次冒出异常，设备注册已释放，主要影响清理日志。这两项不是本轮引入，本次权限/网页恢复复查保留其运行行为，没有将后端全套测试标为通过；后续应独立修复和验证。详见 `recheck-backend/existing-runtime-findings.json`。

## 实现范围

- 国服专用模拟助手未同步、缺失或异常的麦克风状态返回 `mock_microphone_checking`，页面显示检查中，不再直接当作拒绝。未知仍阻止开始和收音连接，不改写为granted。
- denied/restricted保留阻断，说明这是助手当前上报结果，并提示检查系统权限；已允许者可以重新检查或重开助手。账号、设备、在线、代际、会话模式与生命周期检查保留。
- 复用现有5秒网页控制心跳，没有新增后台轮询。未知持续30秒后显示具体恢复指引；同场“重新检查麦克风”发送一次heartbeat，2秒节流。不重绑、不重建、不自动开始；成功恢复只清除过时的麦克风错误。
- 浏览器声音恢复与助手麦克风分开。AudioContext解锁最多等3秒，并确认实际running；按准备、朗读、暂停阶段给对应按钮指引。自动/手动恢复去重；换题、换简历、跳过、结束、断线或卸载使旧回调失效。迟到的旧连接打开事件不能留下心跳。
- 仅修改 [mock runtime](../../apps/backend/app/services/mock_interview_runtime.py)、[模拟面试页面](../../apps/web/src/MockInterviewPage.tsx)、[专用网页客户端](../../apps/web/src/mock-interview-client.ts)及专用测试/本地预览。没有修改普通面试、笔试、快答、资料、简历优化、导航、SEO、模型/Prompt、收费、截止时间、国际服或桌面源码/安装包。

新后端判断明确限定repository的CN edition；Global同一runtime的合成对照仍沿用旧行为。旧v2无专用mock协议的deferred兼容保留，不扩大到新助手。没有数据库迁移、配置或新依赖。

## 执行的验证

| 检查 | 结果与范围 |
| --- | --- |
| 权限专用后端回归 | **52通过**，含真实进程内control/microphone WebSocket与4个隔离PostgreSQL会员/积分场景 |
| 聚焦网页回归 | **44通过**，其中22项为本轮新增回归；包含超时、拒绝、恢复、节流、过期错误、播放竞态和清理 |
| 完整CN Web | **67文件、684测试通过**；覆盖现有普通/笔试/模拟/简历入口及状态读取等 |
| Web类型检查与生产模式源码构建 | 通过，目标Chrome86；产物仅放本地ignored artifacts，不作为线上完整替换包 |
| 浏览器合成演练 | 实际MockInterviewPage验证未知、拒绝、同场重新检查、授权恢复、离线与30秒指引；保留原简历；操作记录只有heartbeat、无自动start/create |
| 独立审查 | 通过；审查后修复阶段提示、无响应重试提示遮挡及等待解锁时换简历锁定问题，并增加回归 |
| 范围保护 | 任务开始文件哈希对比，无范围外文件新增修改；桌面与国际服未改；既有未提交SEO/性能增量保留 |

专用后端验证使用新建的一次性本地PostgreSQL容器，监听127.0.0.1:58643；全部是合成账号、资料与假供应商，不调用真实模型、麦克风、音频播放或付费服务。测试容器完成后移除；原有55445/56385服务不动。

主要命令（项目根目录）：

```bash
OFFERSTEADY_TEST_DATABASE_URL=<isolated-local-test-db> PYTHONPATH=apps/backend /Users/liyulong/anaconda3/bin/python -m pytest apps/backend/tests/test_mock_interview_readiness.py apps/backend/tests/test_cn_mock_permission_recovery.py apps/backend/tests/test_cn_mock_permission_recovery_postgres.py -q
npm run test -w @offersteady/web
npm run typecheck -w @offersteady/web
VITE_APP_ENV=production VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=cn-mock-permission-local-20261030.1 npm run build -w @offersteady/web -- --outDir ../../artifacts/cn-mock-permission-local-20261030/source-build
openspec validate fix-mock-web-permission-readiness --strict
git diff --check
```

## 扩展回归中的既有失败

没有将整套Backend标为全绿。扩展18个现有及本轮mock测试文件得到 **271通过、12失败**；这12项在复制的改动前runtime上复跑全部同样失败，失败用例与首个失败原因一致。改动前runtime SHA-256 `d90738ef92ec7c78b597cdd01da754e165e8e8f9d3ca9fc821f5fed0ba461469` 与上次实际生产核对值一致。未重置或替换当前工作区文件来做对照。

这些历史失败涉及Global TTS端点预期、缺失的生成/清理诊断事件，以及旧轮关闭和断线清理的真实旧缺陷，具体复查结论见上节。另两个Global测试文件依赖当前CN源码未包含的 `global_commerce_service`，旧生成诊断测试依赖未包含的 `mock_interview_diagnostics`，无法收集；未删除或弱化测试。初始化baseline副本时曾因路径缺少迁移文件而得到7个setup错误，已修正副本目录并重跑；最终对照为12个原有失败，不把初次setup错误作证据。

脱敏日志、JUnit、基线对照、范围哈希与本地构建保存在 `artifacts/cn-mock-permission-local-20261030/`，不包含生产配置或用户数据。

## 本地预览与验收边界

测试页：[本地合成预览](http://127.0.0.1:5198/test-previews/mock-permission-recovery.html)。它挂载实际页面，所有API、WebSocket和AudioContext均在内存模拟，未连接线上；不支持真实出题和收音。测试入口不属于生产构建输入。若本地服务已停，可运行：

```bash
VITE_APP_ENV=development VITE_API_BASE_URL=/ npm run dev -w @offersteady/web -- --host 127.0.0.1 --port 5198 --strictPort
```

不改助手意味着仍不能修复助手内部的Mac超时误报denied、Windows上报延迟、真实系统拒绝、设备占用或采集失败。本轮修复网页/后端判断与恢复，不宣称所有硬件问题已解决。真实Windows/Mac设备、实际麦克风和浏览器自动播放策略尚未做物理验收。

未来上线须另获用户指令，并依据[当前实际组件基线](../current-cn-baseline.md)重新核对运行镜像和用户工作门禁；只对mock模块做最小增量，不用全量源码构建覆盖包含历史独立增量的线上静态图。计费仍为有效会员每天1场、其余100积分/场、首次成功开始后60分钟截止，不因本轮检查和恢复重新起算。
