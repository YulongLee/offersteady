# 国服模拟面试控制通道收尾修复 cn-mock-control-20261107.1

状态：2026-11-07 02:07:19（北京时间）已发布，仅CN Backend。用户授权自测通过后上线；独立verify、完整来源/配置/合同核对及短时自然流量观察通过，现可交用户测试。

## 修复与边界

实际基线1724/df78的控制端点最终socket.close只接RuntimeError。合成回归在旧版复现4个失败，新版在同一窄边界容忍WebSocketDisconnect，不吞取消或其他清理失败。保留detach、旧新控制器归属、音频资源、状态/截止及计费规则。仅业务文件mock_interview.py改变；237份原输入逐字保持。未改变Web、助手1.3.6/d7、Global、worker、模型/Prompt、计费、SQL、连接池或依赖。未将最初断线原因、9秒控制或知识库长尾列为已修复。

## 实际运行基线

- 新Backend镜像 `sha256:58d39c035650ba6619bd5783b6e344a49e1a10eadad962ee9a7aa9638a5e7e43`，容器 `fe11497d82c625b47dc7e5ffcd0ed6463d17dda9259e18db18a81d45f9021a94`，StartedAt `2026-11-06T18:06:57.527124762Z`；健康、RestartCount0。
- 238运行输入、162份Python编译、203完整Schema、344有效配置、44依赖保持；池false，辅助上传格式、d7助手、366Web及七非目标保持。
- 固定兼容回退 `sha256:1724a4e95c8fe610d2e6b98a5186a3867adde99c4126e96f55920c2beefc80cf`。新目录 `/opt/offersteady/releases/20261107-cn-mock-control-1`，控制器SHA `e91b46a6e490127ea896c00a1ed0132a94cfb2a31b3892b7d1c7fe575960b59d`；不重放旧控制器。
- prepare/preflight/最终切换重复七项工作门禁、CN实体只读门禁、严格TCP8000为0、归属和单writer证明。历史失败任务及孤立预占保留原口径，不终止任何真实用户工作；恢复同样需要全部门禁。

## 自测

候选从新鲜核对的实际1724镜像单文件叠加。真实本地独占PostgreSQL和合成模型/音频完成271项模拟面试回归，其中含12项控制端点针对性测试，另覆盖旧控制器退出后新控制器/音频/余额保持。307项发布保护测试加110个子场景通过。一个国际服专用TTS案例在未修改国服基线上也失败，明确排除，不计通过。首轮误用主项目editable导入的结果已作废；最终显式PYTHONPATH指向完整候选，并验证实际导入路径和SHA。一次性本地测试数据库已移除。

实际固定镜像以network-none/read-only/cap-drop执行完整合同及12项新控制关闭场景，取消仍传播；原性能/资源隔离探针保持，13个合成线程全部退出。未在生产调用真实模型、创建测试面试或付款，未导出原始日志、用户资料或私有配置。

## 真实发布观察

切换启动后0.983–3.777秒间有16次真实502（实时控制9、连接状态7），均早于部署验收完成，之后及观察末尾60秒未新增。不能描述为完全无短暂影响。

启动至最后错误采样282.18秒内，Backend无ERROR/CRITICAL、Traceback、stream_failed或清理失败。早期主循环最大漂移包含启动和完整发布检查，不当作稳定负载表现。

完整验收结束之后另观察140.848秒自然流量：普通HTTP 157条，P95 58.54ms、最大93.54ms；≥500ms 0条，≥1000ms 0条。真实5xx另由反代核对，不能用request.completed缺少状态字段推断全部200。容量中的活跃面试/音频以证据为准；没有真实用户主动断网的线上复现或同类高峰对照，不能承诺整体P95固定降幅，也不能仅凭无报错断言所有断线已解决。

## 验收证据

[独立生产核对](cn-mock-control-20261107.1/production-verification.json)、[完整运行输入](cn-mock-control-20261107.1/backend-runtime-manifest.json)、[实际镜像探针](cn-mock-control-20261107.1/candidate-probe-result.json)、[自测](cn-mock-control-20261107.1/test-summary.json)、[控制器审阅](cn-mock-control-20261107.1/controller-source-review.json)、[错误汇总](cn-mock-control-20261107.1/post-release-error-summary.json)、[真实502窗口](cn-mock-control-20261107.1/proxy-error-window.json)、[验收后自然请求](cn-mock-control-20261107.1/post-verification-natural-routes.json)、[最终范围核对](cn-mock-control-20261107.1/final-production-audit.json)。

实施任务：[fix-cn-mock-control-disconnect](../../openspec/changes/fix-cn-mock-control-disconnect/tasks.md)。完整控制器/回归结果保留于本地artifacts/cn-mock-control-20261107-release；私有冻结材料仅在服务器。未提交推送Git。
