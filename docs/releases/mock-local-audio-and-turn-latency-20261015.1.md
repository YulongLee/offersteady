# 模拟面试收音与下一题优化：本地测试 20261015.1

本记录保存按用户要求开发、自测并编译本地版本时的事实；该阶段没有更新线上服务、上传正式安装包或推送 Git。用户随后另行授权国服 Windows/macOS 客户端正式上线，见 [1.3.5 发布记录](companion-1.3.5-cn-20261015.md)；下一题服务端优化仍未部署。

## 连接国服的客户端测试包

用户随后希望用原有线上服务测试助手，另编译了 **面试稳 国服测试 1.3.5**。先完全退出旧国服助手，再打开 [.app](<../../artifacts/mock-cn-connected-20261015/macos/mac-arm64/面试稳 国服测试.app>) 或 [打开国服测试.command](<../../artifacts/mock-cn-connected-20261015/打开国服测试.command>)；也可保留 [ZIP 包](<../../artifacts/mock-cn-connected-20261015/面试稳-国服测试-1.3.5-arm64.zip>)。

该包默认连接 `https://mianshiwen.cn/app` 与 `https://mianshiwen.cn/api/v1`，使用原有线上账号，复用既有国服设备身份。它没有本地或 Global 服务覆盖配置，22 个已测试的 dist 文件与本地隔离包逐个比对完全相同，仅打包名称、版本与服务选择不同。旧助手未退出时，既有单实例规则会把打开动作交给旧程序，因此需先退出旧助手。

连接国服的包已通过实际签名验证：16 个 Mach-O 组件，音频输入权限、稳定身份及用量声明均通过；制作测试包时公共国服下载清单 Mac 版本为 1.3.2，离线核对版本比较函数接受数值 1.3.5。未使用 prerelease 字符串，因为既有线上比较函数不接受该格式。本测试 ZIP 只是本机签名产物，未进行正式分发公证或上传下载中心；后续正式发布使用另外构建、公证的 DMG。

可在既有线上服务验证 Mac 客户端收音、错误提示与能力登记修复。**尚未部署的下一题等待优化和生成诊断不会在国服生效**，仍须通过下面的隔离本地服务验证。后续已按用户要求打开国服测试程序，没有替用户创建线上面试。

## 打开方式

1. 双击 [打开本地测试.command](<../../artifacts/mock-local-20261015/打开本地测试.command>)。本机 Docker Desktop 需处于运行状态；启动器只操作本轮专用容器及本机服务。
2. 进入 [本地模拟面试](http://127.0.0.1:5175/app/mock-interviews)，使用合成手机号 `19900000001` 和模拟验证码 `123456` 登录。不会发送真实短信。
3. 新建模拟面试，选择“本地合成练习简历”，使用 **面试稳 本地测试** 窗口显示的连接码。
4. 首次使用由用户允许麦克风权限；开始回答后确认音量与转写，提交回答查看下一题。权限或设备失败时助手会保留原因，并提供“重试麦克风”。

助手已编译为 `1.3.2-local.20261015.1`，Apple Silicon / arm64，最低 macOS 14.2。可直接打开 [.app](<../../artifacts/mock-local-20261015/macos/mac-arm64/面试稳 本地测试.app>)，或保留 [ZIP 编译包](<../../artifacts/mock-local-20261015/面试稳-本地测试-20261015.1-arm64.zip>)。

助手固定连接 `http://127.0.0.1:8015/api/v1` 与 `http://127.0.0.1:5175/app`，本地配置不允许远程地址，也不受生产 URL 环境变量覆盖。身份目录为 `~/Library/Application Support/@offersteady/desktop/local-test`，不会迁移生产助手的机器码或凭据。本轮为本机测试签名编译产物，没有执行正式分发公证。

## 改动

- 补齐主应用与 Helper 的音频输入签名权限；验证实际签名的布尔权限，缺少权限的产物不能通过检查。
- 麦克风权限失败保留可操作提示并停止反复自动尝试；模拟面试音量来自同一条实际 PCM 回调，不创建第二路采集。
- 周期能力登记保留支持的模拟面试协议，读取当前权限状态；修复旧闭包覆盖最新权限与重复释放采集资源。
- 提交回答先停止计费并隔离旧轮音频，下一题不等待旧 ASR 关闭。关闭使用独立的 4 个工作线程，活动与关闭中的资源总量限制为 64；取消观察任务也不会丢掉排队的实际关闭工作。
- 修复断连后关闭 WebSocket 的次生异常。旧轮转录、迟到回调及关闭动作不能污染下一轮。
- 生成日志区分简历读取、队列、供应商请求、响应解析、结果校验和总耗时，仅保留固定错误码、耗时、HTTP 状态及随机诊断 ID。没有改变模型、Prompt、题目/评分校验、收费或自动重试规则。

## 已执行验证

| 验证 | 结果 |
| --- | --- |
| 最终 Backend 模拟面试、Global 隔离、Task ASR 与轻量 heartbeat 回归 | 253 passed，无跳过 |
| Desktop 全部测试 | 41 个文件，228 passed |
| Desktop main / renderer 类型检查 | 通过 |
| Web 模拟面试客户端、报告导出、入口契约 | 23 passed |
| 本地 Web 编译 | 通过，产物位于专用目录 |
| 原生 Mac arm64 采集程序与 Desktop 编译 | 通过 |
| 实际 .app 签名、权限、身份与用量声明 | 通过，16 个 Mach-O 组件；main/Helper/native 音频输入权限已检查 |
| 本地启动器、后端健康、合成短信登录、认证聚合状态、模拟面试列表及网页路由 | 通过 |
| 实际编译程序打开与设备登记 | 显示本地版本，独立身份创建，登记/心跳/连接查询均返回 200 |
| 本地程序的系统麦克风授权通路 | 正常弹出授权并记录结果；该进程近期没有再次出现缺少音频输入签名权限的拒绝 |
| 两次真实模型合成输入，无重试 | 首题 8.249 秒；下一题 3.932 秒，两题不同且通过校验 |

后端测试使用 `synthetic_mock_tests` 与独立 `synthetic_global_mock_tests`；用户预览使用另一个 `local_mock_preview` 数据库和专用 Redis。账号、权益、简历及测试回答全部合成。真实模型验证没有创建业务会话、业务收费记录，也没有使用真实用户内容；模型连接凭据仅由本地后端读取，没有打入客户端。

真实模型两次成功只能证明该合成输入当时可生成，不能证明此前未知生成失败已经根除。真实麦克风输入、扬声器回声、耳机、暂停恢复与连续换题由用户本地试用验收；本轮没有替用户授予系统权限或宣称已经完成物理麦克风验收。

## 复核命令

```bash
OFFERSTEADY_TEST_DATABASE_URL=postgresql://synthetic_local:synthetic-local-only@127.0.0.1:55445/synthetic_mock_tests \
OFFERSTEADY_TEST_GLOBAL_PRACTICE_DATABASE_URL=postgresql://synthetic_local:synthetic-local-only@127.0.0.1:55445/synthetic_global_mock_tests \
  .venv/bin/python -m pytest -q apps/backend/tests/test_mock_interview*.py apps/backend/tests/test_global_mock*.py apps/backend/tests/test_dashscope_task_asr_gateway.py apps/backend/tests/test_web_heartbeat_lightweight.py
npm run test -w @offersteady/desktop
npm run typecheck -w @offersteady/desktop
npm run test -w @offersteady/web -- src/mock-interview-client.test.ts src/mock-interview-word-export.test.ts mock-interview-release-contract.test.ts
node apps/desktop/scripts/verify-release-mac.mjs --app 'artifacts/mock-local-20261015/macos/mac-arm64/面试稳 本地测试.app' --bundle-id com.offersteady.companion.local-test --allow-unnotarized
.venv/bin/python scripts/open_local_mock_preview.py --no-open
openspec validate fix-mock-local-audio-and-turn-latency --strict
git diff --check
```

本地测试服务保留供用户试用，下一题服务端优化仍未发布线上。相关 [OpenSpec](../../openspec/changes/fix-mock-local-audio-and-turn-latency/proposal.md)、[原始诊断](../diagnostics/cn-mock-latency-mac-20261015.md) 和 [后续客户端正式发布](companion-1.3.5-cn-20261015.md)。
