# 国服20MiB上传边界 · 本地验证

2026-10-21用户授权：修复20M上传并与当天1017模型候选一起测试后部署国服。本记录仅描述本地实现和自测，生产发布状态另由组合发布记录确认。

关联变更：[上传边界](../../openspec/changes/fix-material-upload-proxy-size-limit/proposal.md)、[模型候选](../../openspec/changes/unify-models-v41-flash-1017/proposal.md)。

实际问题是当前运行网关缺少上传专用大小规则；仓库默认配置已有21m，因此不能通过复制整份仓库配置来覆盖实际组件。补丁工具读取钉住SHA的当前配置，只在原通用API块前插入一块上传location；其余字节完全保留。上游和转发头从实际通用API块继承，上传块移除WebSocket升级头。

文件上限仍是20 × 1024 × 1024字节。21MiB是网关multipart请求体封装空间，不表示允许21MiB文件。没有修改后端、OSS、MinerU、数据库、积分、前端JavaScript、简历模板或其它页面。

本轮未修改前端failed状态的泛化“解析失败”文案；不能声称本轮已经修复上传错误分类。

## 本地检查

运行工作区：`/private/tmp/offersteady-cn-model-1017-20261021`，来自国服`release-cn-20261019.2`基线。

```sh
PYTHONPATH=apps/backend /Users/liyulong/liyulong/1_projects/offersteady/.venv/bin/python -m pytest -q apps/backend/tests/test_cn_upload_proxy_overlay.py apps/backend/tests/test_material_upload_gateway_config.py apps/backend/tests/test_oss_upload_policy.py
/Users/liyulong/liyulong/1_projects/offersteady/.venv/bin/python scripts/verify_upload_20m_isolated_nginx.py
openspec validate fix-material-upload-proxy-size-limit --strict
```

聚焦回归27项通过，覆盖缺失规则复现、逐字节恢复、通用API不放宽、三条路径正例、相邻路径反例、SHA漂移、已有规则/覆盖路由拒绝、输出文件不覆盖和Backend20MiB加1字节拒绝。

本机隔离Nginx实际测试全部通过。固定镜像`sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10`，每个临时容器均`--network none`、只读、有限内存和tmpfs，测试后删除。没有访问本机既有Web容器或生产URL。

| 配置/路径 | 文件大小 | HTTP结果 |
| --- | --- | --- |
| 旧缺失规则，简历代理 | 1.5MiB | 413，问题复现 |
| 候选，简历代理 | 20MiB | 202，合成上游确认 |
| 候选，JD代理 | 20MiB | 202，合成上游确认 |
| 候选，知识资料代理 | 20MiB | 202，合成上游确认 |
| 候选，简历代理 | 21MiB加multipart封装 | 413 |
| 候选，普通`web/state` | 1.5MiB | 413 |
| 候选，`uploads/proxy/extra` | 1.5MiB | 413 |

20MiB文件的实际multipart请求体为20,971,714字节。上游仅返回固定合成202，不进行鉴权、OSS写入、解析、索引或计费。Backend离线边界测试独立验证20,971,520字节允许、20,971,521字节拒绝。

## 生产集成接口

[准备工具](../../scripts/patch_cn_upload_proxy_20m.py)提供`patch_config(original: bytes, *, expected_sha256: str) -> PatchResult`；结果的`content`是候选字节，另含基线/候选SHA和新增字节数。调用者必须传入先前独立钉住的原文件SHA，不能以每次新读到的任意内容自我批准漂移。CLI仅创建新候选输出，不直接修改输入或执行重载。

[隔离验证工具](../../scripts/verify_upload_20m_isolated_nginx.py)可额外接收`--baseline-config`、`--expected-sha256`、`--listen-port`和本地固定`--image`，用于验证具体实际运行配置。配置内容不输出，失败只返回固定错误类。生产配置不得带回本地或写进公开证据。

生产阶段仍须钉住真实镜像、配置和归属，完成全部用户工作保护门禁、候选`nginx -t`、持久化镜像和回滚准备。只能验证公开健康/配置及小规模无凭据拒绝路径；不得重放真实简历、创建真实资料或为测试发起模型调用。
