## Why

国服资料上传允许最大 20 MB，但 Web Nginx 仍使用约 1 MB 的默认请求体限制。浏览器直传 OSS 失败后，大于 1 MB 的 PDF 会在后端代理上传入口被 413 拒绝，且页面误显示为“解析失败”；该问题已影响真实用户，需要立即修复。

## What Changes

- 仅为简历、JD 和知识资料的后端代理上传路由配置与产品一致的上传请求体上限。
- 保持其他 API 的默认请求体限制、后端 20 MB 文件校验和材料处理逻辑不变。
- 增加 Nginx 配置回归测试，防止后续镜像重新引入 1 MB 限制。
- 将代理上传的 413 与文档解析失败区分，避免把尚未进入解析队列的文件标记成解析器故障。

## Capabilities

### New Capabilities

- `material-upload-proxy-boundary`: 定义资料代理上传的网关大小边界、路由隔离和可诊断错误行为。

### Modified Capabilities

无。

## Impact

- 国服 Web Nginx 配置和部署镜像。
- Web 资料上传错误分类与回归测试。
- 不修改 OSS 对象结构、PDF 解析器、索引、积分、面试、ASR、回答或国际服运行逻辑。
