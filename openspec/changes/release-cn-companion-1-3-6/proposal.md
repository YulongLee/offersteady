## Why

用户于2026-11-02明确要求将当前助手版本部署上线，覆盖此前1.3.6 Local-r3仅供本地测试的发布限制。本次发布已经完成开发、自测及三平台本地包核验的助手，不扩大到尚未上线的Web/Backend笔试配套。

## What Changes

- 国服正式下载更新为助手1.3.6：macOS arm64、macOS x64和Windows x64，沿用当前稳定身份、协议、国服地址和系统最低要求。
- Mac从已冻结、已测试输入制作正式Developer ID签名、公证、staple和Gatekeeper验收通过的DMG；不得将未公证Local-r3包改名作为正式产物。Windows核验真实x64载荷和安装器，保留未签名事实。
- 三个不可变OSS版本对象全部上传、完整读回核验后，才原子替换实际运行Backend内按请求读取的下载清单；不重启业务容器。
- 为未来显式重建保留以实际运行镜像为底、仅增加发布清单的一层镜像及固定镜像Compose覆盖材料；不修改历史Compose文件或无关镜像标签。
- 保存完整发布基线、清单、漂移保护及可验证回滚记录。现有版本门槛继续在新绑定/开始面试时执行；不主动终止已绑定的旧版本面试。OSS三个latest文件不作为当前官网来源，本轮保持不动。

## Capabilities

### New Capabilities

- `cn-companion-1-3-6-publication`: 三平台正式包、不可变对象、原子清单、无重启持久化材料和发布回滚。

### Modified Capabilities

无。本变更只推进[权限及窗口本地变更](../improve-companion-permission-and-window-1-3-6/proposal.md)与[笔试稳定性本地变更](../stabilize-written-screenshot-local-1-3-6/proposal.md)中的Desktop部分到国服正式分发，不改变其功能实现。

## Impact

影响国服助手三个安装包、OSS不可变版本对象、Backend内单个发布清单文件、专用发布工具、生产发布记录及未来重建材料。OSS三个latest文件保持原字节。无数据库迁移、模型/Prompt/计费/依赖升级、容器重启或Web/Backend业务代码发布；不更新Global，不提交或推送Git。私人Ventura兼容包不更新。验证只使用合成输入或公开健康/下载接口，不开启真实面试、模型调用或生产压测，凭据与用户内容留在服务器。

## Authorization and status

状态：apply-ready。2026-11-02的用户指令授权正式发布当前助手；本变更明确记录其覆盖此前本地交付限制的范围。完整同场请求读取与网页失败反馈仍在本地，不能将它们描述为已随助手上线。实体Windows/Intel Mac、真实网络/休眠及音频验收的既有限制继续如实记录。
