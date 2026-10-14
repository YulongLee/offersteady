## Context

状态：apply-ready。用户本轮明确授权正式发布 Windows/macOS 助手，覆盖此前仅本地交付的限制；授权范围是国服客户端发布。来源为已验证的 [修复变更](../fix-mock-local-audio-and-turn-latency/proposal.md) 与 [本地验证](../../../docs/releases/mock-local-audio-and-turn-latency-20261015.1.md)。

当前公有国服清单三个平台均为 1.3.2，Mac 正式最低 14.2+；没有公有 Ventura 额外条目。实际 Backend 为轻量 heartbeat 恢复镜像，实际 Web 为已恢复模拟面试入口的保留镜像；旧 current 源码不能替代这些运行基线。

## Decisions

1. 版本统一为 1.3.5，使用正常产品名称、国服稳定身份与生产 HTTPS 默认地址。正式包不得包含 local-test-runtime.json、Global 地址、测试账户或服务端凭据。
2. 三个架构使用正确运行时；Mac arm64/x64 串行构建，Windows 复制冻结 dist 后才允许重写共享构建目录。
3. Mac 正式产物必须签名、公证、staple 和真实音频权限验签全部通过；不能上传 prepare-only 测试包。Windows 延续现有 unsigned NSIS 分发政策，不虚构 Authenticode 或实体 Windows 验收。
4. 核对实际公有清单和其额外字段，先保存备份。所有三件产物验证、上传、远端对象校验后才切换清单。清单影响旧版版本门槛，不能只发布其中一个平台。
5. 实际清单按请求读取时采用热原子替换，无须重启 Backend。同步保留新的元数据镜像或等效持久化材料，确保后续重建不会退回旧清单；不复制旧服务端源码、不切换当前业务容器。若实际检查证明必须重启，则仅在没有在线面试时进行。
6. 首页及下载入口若使用动态 Backend 清单，不重建 Web。逐个验证公有版本、下载 MIME/长度与 SHA-256；保留旧清单、原镜像标签和 OSS 对象以便回滚。

## Verification

- 客户端测试与类型检查、正式构建；产物对照编译源码、版本、架构、签名/公证、目标地址及无本地覆盖文件。
- 上传完成前不改公有版本；上线后三平台统一显示 1.3.5，分段与完整下载验证正确文件。
- 比较前后容器 ID/镜像/启动时间与业务源码，确认未发布后端优化或中断面试。
- OpenSpec 严格校验、发布记录及文档链接校验，实体 Windows/Intel 麦克风验收未执行时如实记录。
