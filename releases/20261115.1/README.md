# 代码封版 20261115.1

此版本继承 `release-20261106.1`，保存截至 2026-11-15 国服和国际服的实际运行源码、静态资源及伴随程序 2.0.0 的区域开发来源。标签 `release-20261115.1`，分支 `codex/release-20261115-1`。此次封版不部署、不更改线上配置或用户数据。

## 后续迭代的基线

先按 `components.json` 和各自清单恢复目标区域的实际组件，再叠加经批准的改动；不能用根目录整包替换任一线上服务。国服 Backend 已从运行容器逐文件核对 238 项；国服 Web 366 项、worker 196 项与既有快照一致。国际服 Backend 308 项、Web 267 项、worker 267 项已核对现有公开运行输入；后台发布锁是运行元数据，不是源码。只读检查范围和限制见各区域记录，未导出私有环境、用户数据或原始日志。

根目录 `apps/desktop` 是国服伴随程序开发来源；国际服伴随源码在 `global/desktop-source.tar.gz`，两者区域逻辑不同。国服和国际服伴随安装包分别从各自已发布的 1.3.6 制品按记录增量构建，不能将源码快照误称为完整已签名安装包，也不可用国服源码直接覆盖国际服。国服手机面试滚动代码是尚未上线的本地开发改动，根目录还有此前未上线的笔试配套；不等于线上网页行为。

Mac 2.0.0 安装包已签名公证；Windows 未签名、真实 Windows 收音及最终 Mac 真实音频链路未完成验收。用户反馈 Zoom 共享和录制仍会显示浮窗；腾讯会议、钉钉和飞书的结论限于用户自己的测试环境。国服切换期间出现 52 次 502，后续单次一分钟观察未见新增，详见[发布记录](../../docs/releases/cn-companion-2.0.0-20261115.md)。标准桌面 `npm test` 的国际服文案生成步骤仍有失败，单独运行 Vitest 的 410 项通过；在无本机 artifacts 的封版工作区，国服发布相关八组回归为 101 项及 147 子项通过，含一项框架弃用提示。

## 离线核验和恢复

```bash
python3 -B releases/20261115.1/tools/verify_snapshot.py
python3 -B releases/20261115.1/tools/restore_snapshot.py --component cn-backend --output ../offersteady-cn-restored-20261115
python3 -B releases/20261115.1/tools/restore_snapshot.py --component global-backend --output ../offersteady-global-restored-20261115
```

恢复工具只写入不存在的新目录，可选择国服/国际服的 Backend、Web 或资料 worker，不连接线上。国际服桌面源码另按 `global/snapshot-manifest.json` 核验；后续需在隔离目录恢复并检查对应构建工具及既有正式安装包。

Git 中不包含密钥、私有环境、用户资料、原始音频和日志、安装包或镜像层。本版归档的三个国服 staging 脚本已移除生产 SSH 地址并要求调用者显式提供 `OFFERSTEADY_CN_SSH_TARGET`，因此与当时实际执行脚本的字节不同，不能当成审计过的原脚本重放。未来部署必须重新核验实际线上镜像、业务门禁与发布控制器。历史证据中的 `artifacts/` 仅存在于原工作区，不随 Git 交付。
