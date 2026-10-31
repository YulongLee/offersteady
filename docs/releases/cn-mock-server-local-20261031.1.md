# 国服模拟面试服务端补修：本地 2026-10-31.1

2026-11-01更新：用户另行授权后，本地修复已与网页增量合并发布国服，[生产记录及验收](cn-mock-20261101.1.md)。以下保留开发交接当时的状态。

状态：**代码完成、本地验证完成，未部署、未提交或推送Git**。用户要求先完成不需要更新伴随程序的部分，供先行上线；助手另行优化。本轮变更为 [finish-cn-mock-server-reliability](../../openspec/changes/finish-cn-mock-server-reliability/proposal.md)，并保留已完成的[网页权限与播放修复](cn-mock-permission-local-20261030.1.md)。

## 已完成

1. **下一题和新回答不等待旧语音关闭。** CN有效提交先持久化状态、停止交互计时、撤销旧capture，再发布生成状态并启动下一题；进入新回答也不等待此前已隔离的旧清理。后台仍用固定4线程执行器，沿用活动和关闭中capture合计64个的资源门禁。旧epoch转录、重复提交与旧关闭回调不能污染新题或关闭新连接。
2. **断线清理幂等。** 收音端点最后关闭时兼容已断开的WebSocket，继续通过registration身份检查保护替代连接。
3. **生成及清理可安全定位。** 记录简历读取、上下文检查、模型排队、请求、解析、输出校验、总耗时与ASR关闭；区分HTTP失败、请求/排队超时、格式不完整、重复题及报告证据失败。仅使用固定字段/枚举和随机追踪号，不记录用户/会话/设备标识、简历、问题、回答、音频、URL、凭据、供应商正文或原始异常。日志自身故障不会改变业务结果，异常恢复失败不会误记为成功。

暂停、结束、重播、退出及shutdown继续遵守原有有界清理；observer取消/排队或drain超时不取消实际native close、不丢失跟踪，真正完成后才释放。Global原等待策略和新诊断禁用规则已单独验证。

模型、Prompt、请求内容、输出校验、重试次数、provider_fault、每日免费次数、100积分收费、60分钟起算和截止均保持。没有新依赖、配置或数据库迁移。普通面试/笔试、资料/简历优化、SEO、既有性能增量和助手/国际服源码保持。

## 验证结果

| 检查 | 实际结果 |
| --- | --- |
| 服务端组合21个文件 | **333通过、2项历史TTS兼容测试失败**，下文说明，未标整套后端全绿 |
| 清理和CN/Global隔离 | 20项通过，覆盖关闭阻塞、旧回调、替代连接、observer取消、实际future排队、超时drain和日志失败 |
| 生成、诊断、截止 | 78项通过，覆盖敏感标记、并发trace、HTTP/JSON/schema/超时、取消、报告fallback和恢复I/O失败 |
| 完整CN Web | **68文件、696项通过**，网页代码与上轮验证的修复逐SHA一致 |
| Web类型检查与生产模式源码构建 | 通过；仅作本地构建验证，不能当线上完整替换静态包 |
| 接口与编译 | 本地相同配置/依赖环境下完整OpenAPI逐字一致，203条HTTP路径保留；5份服务端文件编译通过 |
| 独立审查 | 通过，已修正“恢复处理失败却记成功”的诊断问题 |
| 范围、Spec与链接 | 任务起始哈希对比无范围外改动；两个OpenSpec strict和本地文档链接校验通过 |

服务端测试使用新建的一次性本地PostgreSQL（127.0.0.1:58645），合成账号/资料、假模型和语音服务；不调用生产、真实模型、音频或付费服务。完成后移除该容器，既有55445/56385服务不动。真实Windows/Mac物理收音仍需使用正式助手验收；Mac晚授权误判、Windows权限检测/上报和多余权限预检等助手根因未改。

两个历史失败为 `test_cn_mock_tts_release_guards.py::test_new_protocol_patch_preserves_known_cn_legacy_baseline` 与 `test_mock_interview_audio_tts.py::test_global_legacy_protocol_and_voice_are_not_migrated`。前者的旧发布转换器要求当前独立CN TTS源码包含Global分支，后者要求CN源码中的Global测试使用国际端点；本轮TTS/旧发布脚本及这两个测试均未改动，在改动前副本上复跑同样失败。没有删除、放宽断言或混入Global源码以求全绿。先前确认的ASR阻塞和断线清理失败，本次对应回归已通过。

## 执行方式与证据

证据目录为 `artifacts/cn-mock-server-local-20261031/`，含测试文件列表、组合及旧版对照JUnit、类型/构建输出、API契约对照、范围检查和组合源清单。Python使用 `/Users/liyulong/anaconda3/bin/python`。主要执行命令：

```bash
OFFERSTEADY_TEST_DATABASE_URL=<isolated-local-test-db> PYTHONPATH=apps/backend /Users/liyulong/anaconda3/bin/python -m pytest <backend-selected-files.json中21个文件> -q
npm run test -w @offersteady/web
npm run typecheck -w @offersteady/web
VITE_APP_ENV=production VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=cn-mock-server-local-20261031.1 npm run build -w @offersteady/web -- --outDir ../../artifacts/cn-mock-server-local-20261031/web-source-build
openspec validate finish-cn-mock-server-reliability --strict
openspec validate fix-mock-web-permission-readiness --strict
git diff --check
```

最初尝试把本地完整OpenAPI散列直接与上次生产镜像散列比较，未匹配；本地配置/依赖并非生产运行环境，不能据此声称生产契约已验证。已改为本轮同环境前后逐字对照并通过。上线时仍应在实际固定镜像和私有配置上执行原有API/Schema探针。

## 上线交接

组合源清单冻结5份Backend运行文件（含新增diagnostics模块）、3份Web运行源码及相关测试/规范指纹；它是源码交接，不是可直接覆盖生产的镜像或静态包。

后续按用户上线安排，须重新核对[实际组件来源](../current-cn-baseline.md)、运行配置和用户工作门禁，在目标实际镜像/静态资源图上仅叠加这些mock增量。保留普通面试、模拟面试、简历优化、多屏、SEO及此前状态读取优化；不使用旧目录源码或完整本地Web构建覆盖生产。发布应保留回退镜像，不回滚数据库或账务。模型自身的排队/生成耗时仍存在，本轮不承诺整体出题或API P95的固定降幅。
