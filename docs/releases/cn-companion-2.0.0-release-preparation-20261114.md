# 国服伴随程序 2.0.0 发布准备

状态：本文为发布前准备记录；2026-11-15 已完成国服更新，实际基线、验收与切换期 502 见[发布记录](cn-companion-2.0.0-20261115.md)。用户于 2026-11-14 授权国服更新，并接受旧助手须升级；今后发布仍须重新核验业务空闲与组件归属。Zoom 在用户实测共享和录制时浮窗仍可见，Windows 包未签名，最终 Mac 和 Windows 真机音频链路尚未完整验收。

## 兼容修订

真实国服下载 API 按运行清单中的文件名查询，清单只留新版本会导致已发布 1.3.6 精确下载链接返回 404；当前实际 Web 将所有可下载的 Mac 条目列出，六条全部公开则首页出现两组同名架构。为同时保留旧链接和原本的三个架构选项，候选清单保存新旧六条，旧三条增加 `hiddenFromListing: true`；Backend `_release_manifest` 仅过滤该值为布尔 true 的条目，不改变精确下载的查找与许可。

候选 `artifacts/cn-companion-2.0.0-live-preflight/web-listing-filter-candidate.py` SHA-256 `e4865462d344f579db425414fecf06a74378ac6e70df22c74337c3813d26d3a0`，国服 1.3.6/2.0.0 清单 `artifacts/cn-companion-2.0.0-live-preflight/desktop_release_manifest.2.0.0.hidden-history.json` SHA-256 `6cb2a0e01afa7c8539a1cccdb1f0d0c8dd1907304ffe71711438ae6b70061340`。前述两份文件是独立冻结候选，不能只更新清单而运行旧版 Backend。

## 已完成本地检查

`PYTHONPATH=apps/backend /Users/liyulong/liyulong/1_projects/offersteady/.venv/bin/python -B -m pytest -q scripts/test_cn_companion_200_hidden_listing.py`：5 项通过。合成用例验证无标志时原样、仅布尔 true 隐藏、旧条目其他字段保持、三个 2.0 展示、六个合成 API 精确下载重定向与未知 404、三个架构选择最新 2.0 及源码变更可精确反向恢复。测试的签名下载地址为 `.invalid` 替身，不访问网络或使用真实用户数据。

独立复核使用隔离的完整 Backend 源执行真实 FastAPI ASGI（`/tmp/cn200_audit_asgi.py`）：合成 state 返回三个可见 2.0 项，新旧六条精确路由返回模拟 307，重新生成的 OpenAPI 和路由表与原版一致；禁止测试网络，未启动应用 lifespan。该检查不代表候选镜像或 OSS 下载的验证。

实时 Backend、Web 容器与各自镜像的库存对照分别为 238、366 个文件并与已记录基线一致；该检查不等于发布门禁。已知历史控制器锁定其他镜像、缺乏本次全部保护门禁，不可直接重放。

版本门槛可能影响旧客户端新绑定、新开始及已有会话重复 start。切换时须严格验证新旧单 writer 和全部业务空闲门禁，未知或读取失败须停止；若需回退，须重新确认归属与保护门禁。
