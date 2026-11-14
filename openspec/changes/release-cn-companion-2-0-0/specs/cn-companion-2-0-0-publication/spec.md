## ADDED Requirements

### Requirement: Safely publish the authorized domestic packages

系统 MUST 仅在已核验三平台候选、不可变对象和即时国服基线后发布国服 2.0.0，不终止用户工作。Backend 切换需要即时空闲门禁和完整回滚材料。

#### Scenario: All artifacts and gates pass
- **WHEN** 三个指定包与其签名状态、尺寸、哈希及 OSS 完整读回一致，当前源和业务门禁均通过
- **THEN** 受控切换包含新清单和最小列表过滤的 Backend，并验证所有公开入口和保留的历史下载

#### Scenario: Unknown or changed state
- **WHEN** 来源、对象、清单、服务工作状态或发布回执不明确
- **THEN** 停止写入并报告，不接受漂移或盲目重试

### Requirement: Preserve runtime and accurately report limitations

发布 MUST 保持未授权组件和其他业务文件不变，保存以实际镜像为来源的重建材料，报告真实验收范围。

#### Scenario: Historical package appears in the published manifest
- **WHEN** 旧版条目标识 hiddenFromListing 为 true
- **THEN** 公开下载列表不显示该条目，精确旧版下载仍可用，最新版本门槛不回退

#### Scenario: Existing manifest has no hidden marker
- **WHEN** 已有清单没有该标志
- **THEN** 公开列表保持原有行为

#### Scenario: Existing user session is active
- **WHEN** 即时工作门禁发现进行中的受保护工作或读取失败
- **THEN** 不切换清单、不终止用户工作

#### Scenario: Report product coverage
- **WHEN** 发布记录描述新版本
- **THEN** 保留 Zoom 浮窗可见、Windows 未签名及尚未完成的硬件音频验收事实
