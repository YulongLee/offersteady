# 国际服问题预取发布支持：2026-10-16

本目录保存 [Global Backend 发布控制器](../../release_global_question_prefetch.py) 的活动门禁与合成回归。不会连接服务器或执行生产发布。

在仓库根目录、安装 Backend 开发依赖后执行：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=apps/backend .venv/bin/python -m pytest -p no:cacheprovider scripts/release_support/global_question_prefetch_20261016 -q
```

门禁来源：

- `legacy-gates/check-idle.py`：从本轮实际 Global 服务器既有发布目录读取，SHA-256 `3fb49a2991e86677e142fd17e8a24ef5af7de92802ee4050055a764be6574f1d`。
- `legacy-gates/check-mock-idle.py`：从本轮实际 Global 服务器既有发布目录读取，SHA-256 `daf3f0f8a6b63e5ebb9eab04fb4f948407b301234e1c1e3e24fbea658bbc81f4`。
- `global_mock_companion_idle_gate.py`：原有 Global 租约和资料门禁的原始副本。
- `active_work_gate.py`：复用已验证的桌面发布者、音轨、截图、资料任务门禁，增加 Global/production 身份校验。
- `extra_idle_gate.py`：复用模拟面试阶段、有效生成租约、网页租约与生成任务门禁，增加 Global/production 身份校验、聚合结果形状验证、缺少保护字段时拒绝以及 Redis 连接关闭。

所有门禁只读数据库与 Redis，并且只打印固定字段的聚合计数。控制器独立拒绝非零保护计数、未知/不完整元数据和异常退出，不输出原始内容或凭据。旧准备中记录不能替代有效租约、页面、音轨与生成工作判断；不清理生产数据制造空闲。

控制器固定本次实际 Backend 容器与不可变镜像，将全部 Compose/Env 文件按原顺序复制到服务器私有上下文，并核对原件、副本和完整渲染配置。历史版本 overlay 保留，只允许新 overlay 变更 Backend image。正向切换与回退都必须通过即时活动门禁，回退还要确认容器属于本轮。

实际发布还必须单独提供三文件候选、完整 app/Prompt 清单、测试报告以及与实际候选匹配的 `probe/candidate-probe.py` 和 `probe/probe-expectations.json`。这些输入由本轮实际镜像重新生成，不能从此前国服或国际服历史清单推断。本目录测试使用合成元数据和假的容器/命令，不代表真实负载 P95、生产回退演练或实体设备收音验收。

本轮冻结的[只读探针](probe/candidate-probe.py)、[配置摘要工具](probe/config-digest.py)及[候选期望清单](probe/probe-expectations.json)一并保存。它们绑定本轮实际 Global 基线与候选，并要求显式提供对应有效配置摘要；后续版本必须重新核对完整清单。候选执行同时使用 Docker 无网络、只读文件系统、移除能力及禁止提权隔离；Python IO 拦截不能单独代表通用沙箱。

本目录合成回归：184 项通过，包含直接拒绝服务未运行、健康缺失/异常/启动中和重启漂移的验收。
