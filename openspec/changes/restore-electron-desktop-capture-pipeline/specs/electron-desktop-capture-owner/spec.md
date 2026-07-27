## ADDED Requirements

### Requirement: Electron is the single capture owner
当前无 Developer ID 的 macOS 助手 SHALL 仅由 Electron 主应用拥有麦克风、电脑输出和屏幕采集资源，正式运行时 SHALL NOT 启动 Swift Helper 或遗留主进程音频发布器。

#### Scenario: Live interview starts
- **WHEN** 已授权的桌面助手连接到一个 live 面试
- **THEN** 系统仅创建一个 Electron realtime publisher，并由其打开麦克风与电脑输出媒体源

#### Scenario: Native helper exists in application files
- **WHEN** 安装目录仍包含原生 Helper 源码或二进制
- **THEN** 正式桌面运行时不得启动该 Helper 或接受其音频帧

### Requirement: System output uses the main application permission identity
电脑输出采集 MUST 通过 Electron display media loopback 运行，并复用主助手的屏幕与系统音频录制权限身份。

#### Scenario: System output permission is granted
- **WHEN** 用户已向面试稳伴随程序授予屏幕与系统音频录制权限，并在电脑播放可听声音
- **THEN** Electron system audio adapter 获得音频轨道并产生非零 PCM 帧

#### Scenario: System output permission is missing
- **WHEN** display media 请求被 macOS 拒绝或没有返回音频轨道
- **THEN** 助手明确显示权限或音轨不可用状态，并且不得显示电脑输出发布已就绪

### Requirement: Capture owners are mutually exclusive
本地音量监视器与 live realtime publisher MUST 互斥拥有媒体轨道。

#### Scenario: Session changes from idle to live
- **WHEN** 助手检测到当前绑定面试进入 live 状态
- **THEN** 助手先停止本地监视器并释放其轨道，再启动正式 realtime publisher

#### Scenario: React state refreshes during one live session
- **WHEN** 同一 binding lease 的状态、电平或心跳发生更新
- **THEN** 助手不得重复创建 realtime publisher 或第二组媒体轨道

### Requirement: Captured media remains ephemeral
助手 MUST NOT 默认将麦克风、电脑输出或屏幕媒体写入本地持久文件，诊断日志 MUST NOT 包含原始音频或转写正文。

#### Scenario: Capture diagnostics are generated
- **WHEN** 助手记录采集健康状态或错误
- **THEN** 诊断仅包含权限、轨道、帧计数、电平、时延和错误码等元数据
