## Design

在 AuthenticationService 的微信授权会话创建、模拟扫码、模拟授权和回调入口统一调用生产环境保护函数。当前项目中的 Provider 会生成合成身份，尚未实现微信官方 OpenID/UnionID 换码，因此 production 一律返回 404，避免公开接口被滥用。

development/test 环境保持原有兼容模式和测试覆盖；后续正式微信 Provider 完成后，再单独设计生产启用条件与验收。
