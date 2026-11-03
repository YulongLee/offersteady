## ADDED Requirements

### Requirement: Deliver a current-baseline local candidate only
本轮 MUST 以实际5efba4ab…的233输入为基线，通过明确允许列表构造隔离候选，MUST 核对未改SHA、完整203 API及配置/Prompt/依赖/助手清单。MUST 保留未发布笔试配套在候选之外；MUST NOT 部署/SSH/推送Git或访问真实用户/供应商。

#### Scenario: Assemble candidate and compare
- **WHEN** 允许文件叠加到冻结实际输入并验证
- **THEN** 所有非目标字节与203完整Schema保持，Global/普通/笔试/模拟/计费相关回归及新增并发场景实际执行并记录限制

#### Scenario: Slow I/O regression and release handoff
- **WHEN** 本地慢关闭、慢Redis、取消/重连/清理和批读验证完成
- **THEN** 交付实测对照、待解决项与晚间发布约束，不承诺线上P95降幅，不将本地通过当作部署授权
