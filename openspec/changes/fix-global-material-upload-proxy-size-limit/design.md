## Context

国际服直传对象存储失败后会回退到 Backend `/uploads/proxy`，但 `global-web.conf` 没有声明上传请求体上限。应用层允许 20 MB，因此网关默认约 1 MB 与产品能力不一致。

## Decisions

- 使用锚定正则 location，仅覆盖 resume、job-descriptions 和 knowledge collection 的代理上传路径。
- Nginx 使用 21 MB 容纳 multipart 开销，Backend 继续执行 20 MB 文件校验。
- 保留对象存储优先和 Backend 代理兜底的现有拓扑。
- 413 使用英文可操作提示；未创建服务端文档前的失败显示为 Upload failed，而不是 Parsing failed。

## Risks / Trade-offs

- 正则范围过宽：通过正反配置测试确保普通 `/api/` 不被放宽。
- 国际服发布风险：先完成测试与构建；部署时仅平滑重载 Nginx，不重启核心服务。

## Migration Plan

1. 完成配置、英文错误和测试。
2. 验证 Nginx 语法及国际服生产构建。
3. 在国际服以大于 1 MB 的合成 multipart 请求验证网关边界。
4. 异常时恢复原 Nginx 配置并平滑重载。
