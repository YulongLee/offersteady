## Context

用户已授权开发，状态apply-ready，仅本地1.3.6合入。基线为当前Local-r2源码/安装包：权限、mock音频、原外观和透明Tray保留。诊断见docs/diagnostics/cn-written-screenshot-20261101.md，心跳停发根因未证明，不把App Nap当既定根因。

## Goals / Non-Goals

目标：同场笔试连接恢复；busy不丢已受理截图；捕获/上传期限和旧结果隔离；既有失败入口反馈；三平台本地包。

非目标：生产/OSS/Git推送、新增路由/协议版本/计费/模型/Prompt/依赖升级；自动开面试/自动收音/截旧页面；新常驻UI或检查按钮；保证所有网络故障消失。

## Decisions

1. 以纯DesktopConnectionRecovery协调器包住完整注册操作（身份读取+fetch+响应消费），8秒期限、单在途、generation隔离，正常15秒周期；显式resume/focus/online合并触发且有最小间隔，旧操作abort后不堵新轮。仅记录计数/时间/稳定错误，不存标识或内容。原麦克风权限/能力登记走原接口，mock/普通采集逻辑保留。
2. 心跳恢复成功后只核验已有同场有效绑定；截图SSE404/409保持原保护，不能无门禁重连风暴。成功验证且当前笔试绑定/状态一致才重新开启截图流。原暂停/结束/切场清理所有旧截图队列与迟到回调；不自动创建/绑定会话。有效live written绑定期间临时prevent-app-suspension，允许显示器关闭，失效/结束/退出释放；resume只刷新状态，不自动截图。不宣称它已证实解决本次所有断档原因。
3. 新笔试processor以注入ports实现FIFO：1active+最多4pending，按request去重，busy明确保留或失败，不静默return true。仅当前同一bindingKey/session/device generation；处理前及capture后以设备凭证读取同场次指定请求状态，并兼容旧Backend的canonical next响应（不新增路由或依赖网页登录token）。不匹配/取消/过期跳过，完成后一次补查canonical pending，排除刚失败/跳过的同ID以免空转；按服务器时间拒绝60秒以上旧请求，禁止后台连续截取无用户请求的画面。
4. 捕获10秒、上传30秒等各步骤有界，AbortSignal+generation fence；无法取消的迟到native结果直接弃用。锁使用owner lease，旧捕获/定时器不能释放新锁。上传结果不明不盲重传，依赖服务器状态确认；report失败也有界。捕获/上传错误分别分类，取消后的409为终态，不作为当前新请求失败。所有截图仍内存临时，诊断不存图片/问答/身份。
5. 普通模式沿用现有截屏分支；共享锁只加兼容owner lease，不改已有普通/模拟采集规则。Web仅笔试已有失败提示和取消隔离，兼容正式1.3.5和当前Backend；本地预览可用合成场景，不触发线上测试或登录付费。
6. Backend仅现有device next读取增加可选sessionId/requestId：必须匹配当前有效binding、owner、device/code，指定请求可读终态；无参数保持原行为，只session参数只取同场pending。无写入或新路由，45秒TTL不放宽。旧Backend忽略query时，助手仍强检验返回session/device/code；无法确认时明确提示，不截错旧任务。版本仍1.3.6，本地文件Local-r3区分r2；沿用相同身份/默认国服/Electron42.5.0。顺序构建Mac两架构后Windows，冻结源/dist、实际签名/权限、安装器载荷和跨平台同源；实体硬件限制如实记录。

## Risks / Trade-offs

- [无法确定系统/网络断档触发] → 连接期限、resume恢复、短时应用保护和脱敏诊断可分别验证，不承诺已消除未知根因。
- [旧Backend只提供canonical next] → 添加现有设备读取的可选查询，同样鉴权且只读；旧响应强检验，不跨场截屏。
- [超时无法终止OS捕获] → 放弃迟到结果并隔离锁owner，不让旧结果上传/释放新锁；合成测试覆盖。
- [上传可能已到后端] → 不自动重复上传或生成，服务器请求状态和现有幂等边界保持。
- [共享代码误伤普通/模拟] → mode gate及普通/模拟/快捷键/多屏回归，保持r2音频和可见性源码校验。

## Migration Plan

仅本地开发/预览与安装包交付，无生产迁移。助手可连接现有国服，旧Backend忽略新可选参数时严格校验fallback；旧场次pending隔离的完整配套需后续统一发布Backend/Web。先纯合成回归/类型/构建、再固定源构建三包和验证；用户后续统一测试/发布。旧Local-r2安装包保留，线上仍1.3.5。

## Open Questions

无阻塞的产品选择。真实Mac/Windows断网、休眠恢复、透明槽位点击和音频仍需对应设备验收；本机自动化不当成完整线上面试。
