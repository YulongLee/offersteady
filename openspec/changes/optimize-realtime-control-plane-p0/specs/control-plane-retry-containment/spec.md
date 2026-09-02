## ADDED Requirements

### Requirement: Duplicate control requests do not amplify expensive work
相同设备在一个服务端建议刷新窗口内发起重复连接、绑定或截图资格查询时，系统 MUST 复用安全结果或执行 single-flight，且 MUST NOT 重复扫描或写入全局状态。

#### Scenario: Multiple identical connection queries overlap
- **WHEN** 同一设备的相同 active-connection 查询在一秒内重复到达
- **THEN** 系统返回契约一致的结果并至多执行一次昂贵状态解析

#### Scenario: Device state changes during cache lifetime
- **WHEN** 新绑定建立或设备 generation 发生变化
- **THEN** 相关缓存立即失效或在小于一秒的窗口内重新读取权威状态

### Requirement: Invalid binding retries remain client compatible
失效绑定和未绑定截图请求 MUST 保持既有状态码与安全错误语义，并 SHALL 提供有界退避建议；系统 MUST NOT 依赖 429 或强制客户端升级保障服务稳定。

#### Scenario: Legacy companion repeatedly requests screenshot binding
- **WHEN** 旧客户端持续请求一个未绑定设备的截图资格
- **THEN** 每次响应仍可被旧客户端理解，服务端只执行 O(1) 轻量查找且不会产生大快照写入

### Requirement: Short control work cannot block realtime streams
短时同步控制操作 MUST 与异步事件循环和阻塞 Stream 等待隔离，且执行资源 MUST 有界。

#### Scenario: Invalid clients generate a retry storm
- **WHEN** 多个失效设备持续查询且正常用户正在面试
- **THEN** 正常用户的音频接收、SSE事件和健康检查不会排队到失效查询之后
