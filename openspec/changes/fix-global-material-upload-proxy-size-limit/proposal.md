## Why

国际服与国服使用相同的资料上传拓扑，但国际服 Web Nginx 仍保留约 1 MB 的默认请求体限制。浏览器直传对象存储失败后，较大的 PDF 会在代理上传入口被 413 拒绝，因此国服已经确认的问题也会影响国际服。

## What Changes

- 为国际服简历、JD 和知识资料代理上传路由增加与后端 20 MB 文件限制匹配的、路由级 21 MB 网关上限。
- 将国际服代理上传 413 显示为英文的文件大小错误。
- 将上传阶段失败与解析阶段失败区分，并补充配置与前端回归测试。

## Capabilities

### New Capabilities

- `global-material-upload-proxy-boundary`: 国际服资料代理上传边界及错误分类。

### Modified Capabilities

无。

## Impact

- 国际服 Web Nginx、国际服资料上传适配器及资料页错误展示。
- 不修改登录、面试、Companion、ASR、RAG、AI、计费或国服运行环境。
