# 国服模拟面试准备兼容热修 — 2026-09-26

部署完成：2026-09-26 04:05:22 +0800。网页版本 `cn-mock-readiness-20260926.2`。

## 问题与修复

正式 1.3.2 助手心跳固定上报麦克风 unknown，新模拟面试却把它作为必须 granted 的准备条件，导致绑定成功仍不能开始。仅对现有 v2 协议且无专用 mock 标识的助手兼容未知/缺失状态，不放松身份、绑定代际、在线与显式拒绝权限检查，不把未知改写成授权。实际采集仍受 OS 权限控制，回答仍等待认证音频通道。

页面显示具体准备原因，绑定成功通知与错误分离，并立即刷新准备状态。同场恢复不重新创建、不重复扣创建积分，收音通道等待不累计回答分钟。普通面试、快答、笔试、手机模式、模型、计费规则和助手安装包未改。

## 验证

- 独立国服实际源码基线：308 后端测试，58 前端/路由测试通过；类型检查、生产构建、Nginx、OpenSpec strict 通过。
- 旧助手真实 unknown 心跳贯穿 HTTP→publisher→两种 v2 WebSocket 帧→转录→断线→恢复→结束清理的合成测试，不再硬编码权限 granted。
- 拒绝授权、协议不支持、离线、错设备/代际、结束会话、权限状态提示、同场恢复和原功能回归通过。
- 公网健康、首页、mock 路由、支付/网页状态、后台站点验证通过；未登录 mock API 仍 401。
- 上线后只读核查用户原准备记录：ready=true、简历选中、分钟费 0；这不等于真人麦克风验收，真实设备体验仍待用户测试。

## 发布产物与范围

目录：`/opt/offersteady/releases/20260926-cn-mock-readiness-2`。

| 组件 | 镜像 | SHA-256 |
|---|---|---|
| 后端 | `offersteady-cn-backend:mock-readiness-20260926-2` | `c4a7a88f143f4f3589f45f990aa4de08af74e59f1a1f29c8a54573d7a9b6ccfc` |
| 网页 | `offersteady-cn-web:mock-readiness-20260926-2` | `5d918c7106d5256f5ed466fc17e40afd753574562e75078a7551a8e9d72270f9` |

基于 [上一版正式 mock 发布](cn-mock-interview-20260926.1.md) 增量构建，后端业务只替换 `mock_interview_runtime.py`，网页业务只改 `MockInterviewPage.tsx`。`backend-current`、`web-current` 指向新目录；`current` 编排目录不变。

切换前无 live 会话、音频、未完成回答，唯一 mock 场次尚在 preparing。备份 `postgres-before-readiness.dump` 并用 pg_restore 校验目录；无数据库迁移，无配置更改。只重建 backend/web，其他容器 ID、启动时间、环境均核验未变。保留原准备记录与已付创建费用，没有代用户结束/创建场次。

## 回滚

先检查普通和 mock 活跃面试。上一版后端 `offersteady-cn-backend:mock-interview-20260926-1`、网页 `offersteady-cn-web:mock-interview-20260926-1` 保留；回退到这两个镜像并恢复组件指针即可。不要还原数据库、删除 mock 表或积分账本。上一版仍存在 unknown 准备阻断，回退只用于阻止新故障，不是问题修复。

发布执行及核验保存在服务器本次目录的 `deploy/readiness-switch.py`、`containers-before.json`、`containers-after.json`、`verified.json`。未更新国际服、未发布助手、未推送 Git。
