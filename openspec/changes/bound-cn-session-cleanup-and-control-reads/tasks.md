## 1. Baseline and regression

- [x] 1.1 冻结封存a1e6实际237输入、工作树及非目标，确认apply-ready、本地范围和既有合同。
- [x] 1.2 增加可复现用户列表N+1、慢物理close占位和ACK完整资料读取的失败测试（9项失败，见red-tests.xml）。

## 2. Scoped reads

- [x] 2.1 实现owner绑定/账号索引、原子初始化/写维护、TTL/完整性和原始JSON读取。
- [x] 2.2 单场结束直接读取canonical绑定，回归旧仓库/owner/stale/generation/retire/seed/重启。
- [x] 2.3 用独占真实Redis验证1/1242/10000历史下网络、解码和服务端扫描预算及交错。

## 3. Cleanup and acknowledgement

- [x] 3.1 实现独立有界物理关闭、旧对象归属、满载回退/失败/关机排空和可选gateway能力。
- [x] 3.2 CN普通语音接入逻辑关闭与准备通道，保留同场锁/取消/补偿及Global/mock原路径。
- [x] 3.3 CN回执权威轻读和DEBUG开销保护，验证完整字段、缓存期限、缺失/跨owner与旧仓库。

## 4. Verification and handoff

- [x] 4.1 构造独立候选，验证203完整Schema/344离线配置、44项封存依赖目录与声明、辅助格式/d7清单及全部非目标；未执行实际镜像或生产私有配置探针。
- [x] 4.2 运行真实本地PG/Redis、普通/笔试/模拟/计费/鉴权及6/10场混合并发与慢关闭/取消规模回归，记录实际操作数/CPU/耗时（最终1013通过、1跳过）。
- [x] 4.3 完成代码与场景复核、strict/链接/diff检查和[本地交付记录](../../../docs/releases/cn-cleanup-control-local-20261104.1.md)；两轮六个自建容器及合成数据库已清理，等待晚上用户部署指令，不上线/提交推送Git。最终来源与场景证据见artifacts/cn-cleanup-control-local-20261104/final-audit.json。

## 5. Authorized CN production release 2026-11-06

- [x] 5.1 新鲜核对实际a1e6/7663来源、237输入/完整合同、辅助格式、d7、366Web和七非目标；冻结生产基线/回退和七文件SHA，任何漂移停止。
- [x] 5.2 新专用控制器保持既有生命周期/归属/七门禁+CN实体/TCP0/单writer；发布回归146项/220子用例及network-none合成镜像探针通过，固定1724候选238输入/231非目标保持，13个合成线程全部释放。
- [x] 5.3 冻结私有Compose/环境只留服务器，prepare/preflight通过；原七门禁、CN实体保护字段和TCP8000均零，单writer/归属通过，没有清活动、断开连接或放宽门禁。
- [x] 5.4 空闲重复门禁后仅切换CN Backend，控制器返回deployed；未回退、未重复重启，原七门禁+CN实体/TCP0/单writer保护保留。独立验收和观察见下一项。
- [x] 5.5 独立verify及实际238/231、203Schema/344配置/44依赖/d7/辅助格式/366Web/七非目标通过；472.25秒观察Backend异常/5xx/清理失败为0，15次502仅启动0.524–3.545秒，验收后无新增。另120.497秒空闲自然窗口162普通HTTP P95 47ms，不能代表活跃面试收益。README/当前CN基线及[生产记录](../../../docs/releases/cn-cleanup-control-20261106.1.md)已更新，未提交推送Git；可通知用户测试。
