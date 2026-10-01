# 国际服发布校验与剩余事项（本地开发）

日期：2026-09-29。未部署应用，未更改线上套餐或数据库，未删除生产文件/镜像。线上应用仍以 `20260929-global-reliability-2` 为基线。

## 本轮实现

- 发布源包检查：`scripts/global_release_validation.py`，校验 edition、发布模式、服务集合、不可变基线镜像 ID 格式、完整源码哈希和测试证据哈希。老 `deploy-global-production.sh` 在任何 chmod/build/restart 前要求清单，拒绝将四组件增量发布交给老全量入口。
- 镜像保留规划：`scripts/global_image_retention.py`，只读，无 `apply`/删除功能。每个组件最近两张不同镜像、所有运行/停止容器的镜像及回滚引用均保护。混合标签、未知时间、未标记和未知组件保守保留。
- 3 处前端断言：静态/React 首页按照当前线上 benefits → plans 顺序断言，保留独立反馈组件的行为测试；现行已启用的付费套餐入口应为 `/login`，不是旧支付未开放时的空链接。本轮未修改首页、套餐或反馈数据。

## 验证结果

| 检查 | 结果 |
| --- | --- |
| `.venv/bin/python -m pytest scripts/test_global_release_safety.py -q` | 33 通过 |
| `bash scripts/test-global-deployment-assets.sh` | 通过 |
| `bash -n scripts/deploy-global-production.sh` | 通过 |
| `npm test -w @offersteady/web-global` | 115 通过、20 个测试文件，无跳过 |
| Global Web production build（本地验证版本） | 通过，仍有主包 >500KB 提示；未将该工作区产物作为线上发布包 |
| 当前已部署 Global 独立源码的 `test_durable_material_processing.py` + `test_global_second_batch.py` | 19 通过，包括原先缺少数据库而跳过的真实 PostgreSQL 持久化回归 |
| `openspec validate harden-global-release-validation --strict` | 通过 |

数据库测试使用本地临时 pgvector/pg16 容器、随机回环端口和内存文件系统，只有合成数据。执行后停止并自动移除临时容器，没有接入或清理任何生产数据。构建自动更新的下载元数据/翻译文件已恢复到构建前版本，避免夹带无关变化。

## 只读线上镜像检查

2026-09-29 14:04 北京时间，以四组件 `baseline-20260929-2` 回滚引用执行只读规划，共识别 36 张镜像，保守保护后没有推荐删除项。没有删除内容，不能宣称已经释放磁盘。数据卷、日志、源目录、构建缓存不在此规划范围，磁盘清理仍需单独核查具体占用和引用关系。

## 使用边界

发布清单使用 schema 1，字段为 `edition=global`、`release`、`deployment_mode`（`incremental` 或 `legacy-compose`）、`baseline_images`（完整 SHA256 ID）、`source_roots`、`source_files`（路径到 SHA256）、`checks`。检查项至少为 backend/web/admin/web-build/admin-build，每项包含 passed 状态、相对 evidence 路径、sha256。

源码范围由脚本 `SOURCE_ROOTS` 固定，包括所有 apps、packages、ai、infra、scripts 和根构建文件；可选 `.dockerignore`、`.npmrc`、shrinkwrap 同样入清单。只排除已知依赖/构建缓存和私密配置；源文件或证据不允许符号链接、路径越界。

```sh
python3 scripts/global_release_validation.py --root /absolute/isolated/global-bundle --manifest /absolute/reviewed-manifest.json --mode incremental
python3 scripts/global_image_retention.py --rollback-image offersteady-global-backend:baseline-20260929-2 --rollback-image offersteady-global-material-worker:baseline-20260929-2 --rollback-image offersteady-global-web:baseline-20260929-2 --rollback-image offersteady-global-admin:baseline-20260929-2
```

清单不是自动批准，也不证明供应商可用或源码必然不含国服逻辑；审查者必须核对隔离基线和允许的改动。脚本只检查基线 ID 格式，不从线上确认实际运行镜像；部署流程仍必须核对真实基线、空闲会话/音频/任务、运行时配置、回滚及上线后服务检查。不要为了通过而从混合根目录生成一份“全部通过”的清单。

## 尚未完成 / 待确认

- 新功能：联网回答、模拟面试/语音/报告/Word 尚未开发到国际服；见 [新功能提案](../../openspec/changes/add-global-web-search-and-mock-interview/proposal.md)。国际服不具有国服积分钱包，需要确认新功能套餐/配额，不能直接复用国内扣费。
- 真实设备、连续面试和多人并发容量验收尚未执行；以上单元/集成测试不代表这些场景已经通过。
- 首页历史商业清晰度 Spec 提及保留反馈，而当前已部署首页未挂载反馈组件；本轮测试记录现有基线，不重新设计首页或静默修改那份历史 Spec。未来若恢复展示，需要单独确认。
- 本轮只生成保留规划，未执行磁盘清理，也未配置周期自动清理。
- 未改变已购套餐，不调整既有实时音频、快答、语言、Creem 支付或国服代码路径。
