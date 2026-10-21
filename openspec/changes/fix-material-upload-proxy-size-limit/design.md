## Context

浏览器资料上传优先使用 OSS 表单直传；直传因 CORS 或网络原因失败时，会回退到同域 Backend 代理上传。应用层允许最大 20 MB，但承载国服 Web 的 Nginx 未声明 `client_max_body_size`，使用约 1 MB 默认值。2026-09-06 的真实请求中，1,662,780 字节的 multipart 请求被 Nginx 以 413 拒绝，Backend 和 MinerU 均未收到文件。

## Goals / Non-Goals

**Goals:**

- 让不超过应用层 20 MB 限制的简历、JD 和知识资料能够通过代理上传。
- 仅扩大资料代理上传路由的请求体边界，不改变其他 API。
- 保持现有 OSS 优先、Backend 兜底、解析与索引流程不变。
- 让上传网关错误不再冒充解析失败。

**Non-Goals:**

- 不更换 OSS、MinerU、数据库或材料处理模型。
- 不提高产品声明的 20 MB 文件上限。
- 不修改面试、ASR、回答、计费或国际服链路。

## Decisions

### 为明确的代理上传 URL 增加专用 Nginx location

使用正则 location 精确匹配简历、JD 和知识资料的 `/uploads/proxy` 路径，并设置 `client_max_body_size 21m`。21 MB 为 multipart 元数据提供少量协议开销，文件本身仍由 Backend 的 20 MB 校验约束。

不在整个 `/api/` 上放宽限制，避免其他接口接受不必要的大请求。也不只修改运行中容器，因为镜像重建后会丢失临时配置。

### 保持 OSS 直传优先和 Backend 代理兜底

本轮不改变上传拓扑。代理兜底是用户网络或 OSS CORS 不可用时的重要可用性保障；先修复其网关边界可快速恢复真实用户上传。

### 用配置契约测试覆盖路由范围

回归测试必须证明三个上传代理路由使用 21 MB 上限，同时普通 `/api/` location 未被整体放宽。运行 `nginx -t` 验证最终配置语法。

### 区分上传失败与解析失败

尚未获得服务端 document ID 的乐观条目属于上传失败，不得显示为 MinerU 解析失败。413 应提供文件大小/网关边界相关提示。

## Risks / Trade-offs

- [multipart 请求会略大于文件本身] → Nginx 使用 21 MB，Backend 继续严格校验文件内容不超过 20 MB。
- [Nginx 正则 location 可能覆盖错误路径] → 使用锚定路径并增加正反例测试。
- [重载配置时影响连接] → 先 `nginx -t`，再 graceful reload；不重启 Backend、数据库或 Redis。
- [OSS 直传问题仍可能存在] → 保留代理兜底；OSS CORS 单独排查，不扩大本次紧急修复。

## Migration Plan

1. 修改镜像源配置并运行配置契约测试及 `nginx -t`。
2. 将同一配置写入国服运行容器，验证后执行 graceful reload，立即恢复大 PDF 上传。
3. 构建并发布持久化 Web 镜像时仅替换 Web 层，不重启 Backend。
4. 回滚时恢复原配置并 graceful reload；不会涉及数据回滚。

## Open Questions

无。

## 2026-10-21 runtime-derived overlay

发布输入必须是当前`compose-web-1`实际运行的`default.conf`原始字节和单独钉住的SHA-256。`scripts/patch_cn_upload_proxy_20m.py`只允许在唯一`location /api/`前插入上传专用location；复制该实际API块的既有上游和转发配置，移除对上传无用的WebSocket Upgrade/Connection头，添加`client_max_body_size 21m`。删除新增块必须逐字节恢复原文件，已有CSP、网页路由、SSE、静态文件和通用API配置不得改变。

发现SHA漂移、已有上传块、多个server/API块、`^~`或先行regex覆盖上传路径等冲突时拒绝生成；不自动猜测新的路由拓扑。工具仅生成全新的候选文件，不能就地覆盖输入、直接重载Nginx或更改线上容器。

隔离验证使用本机固定Nginx镜像、`--network none`、只读容器和tmpfs。上游是在同一容器内返回固定202的合成Nginx服务，不经过生产认证、OSS、解析器或数据库。先复现旧配置对1.5MiB请求返回413，再验证20MiB文件加multipart封装在三条专用路径均返回202；超过21MiB封装及普通/邻接API仍返回413。后端离线测试单独证明20MiB文件允许、20MiB加1字节拒绝，不能把21MiB网关封装误当产品文件上限。

生产阶段由组合发布控制器执行新鲜基线/完整用户工作门禁、固定镜像和私有配置备份、候选语法验证、持久化镜像切换与验收；不能复制历史9月6日已完成记录来宣称本次发布完成。真实用户简历不用于回放，不创建用户资料或调用解析来做验收。不得整体重建前端或改写JavaScript错误文案。
