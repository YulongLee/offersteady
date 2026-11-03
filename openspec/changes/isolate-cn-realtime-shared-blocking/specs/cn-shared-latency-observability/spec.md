## ADDED Requirements

### Requirement: Bound and isolate content-free CN scheduling observations
CN SHALL 以固定内存上限记录主循环延迟和低比例工作分段，区分入场/排队、worker执行和loop恢复；操作/lane MUST 为固定白名单，日志 MUST 只含固定标签及有限数值。观测失败 MUST NOT 改变业务结果，Global MUST 不启用本探针；MUST NOT 记录用户/会话/设备/请求标识、SQL/URL、正文或异常文本。

#### Scenario: Main loop and worker stall independently
- **WHEN** 合成主循环停顿或worker慢I/O分别发生
- **THEN** 数值摘要能区分loop等待与worker执行，样本有界，不把各相位或模型标记混作同一请求精确归因

#### Scenario: Broken observer or disabled edition
- **WHEN** 时钟/日志异常、取消/关闭或Global运行
- **THEN** 原成功/错误保持，无敏感日志、无限样本或遗留后台探针
