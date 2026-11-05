# Mac蓝牙耳机收音慢与识别差：2026-11-04只读诊断

用户反馈普通面试中，蓝牙耳机/AirPods麦克风“又慢效果又差”，并自愿在已有面试中讲话供核对。本轮仅只读观察，没有修改音频、代理、网络设置、程序或线上，没有创建面试、代理主动调用模型或录制音频。保留的证据只含数值和有限状态；用户讲话属于既有面试正常活动。

## 已确认

本机默认输入和输出均为蓝牙耳机，Core Audio报告24kHz，输入1通道；这本身不证明识别会失败。实际运行国服助手1.3.6、1个主进程，旧副本与Global主进程未运行。实际App和Renderer Helper均有audio-input entitlement，持续约46.8次/秒采集回调，不能套用10月15日旧1.3.2缺签名权限的根因。

只读解包实际安装的app.asar，确认renderer仍同时请求echoCancellation/noiseSuppression/autoGainControl ideal true，并有commercial-adaptive VAD。该组合对具体蓝牙输入可能需要设备适配，但尚无对照实验证明本次误识别由其中哪一项造成，不能据此直接关闭所有处理。

本机当前WiFi在信道11、2.4GHz/20MHz，PHY 802.11ax、链路速率68Mb/s、信号/噪声-61/-82dBm。系统HTTP/HTTPS/SOCKS代理均开启，系统例外规则未明确匹配面试稳域名；没有测出代理应用内部DIRECT规则或实际路由，不能据此断言流量绕行境外。

已在服务器内用本机设备做归属匹配（不输出任何标识），当前绑定的会话为live/interview/computer。设备状态存在mic level0及0.087、语音帧增长的样本，说明有时能采到并发送声音；不能描述为麦克风完全不可用。

## 已出现的延迟分段

新Backend进程累计、混合microphone/system的样本中，助手入队至实际发送3331条，P95 1480ms、最大4902ms；这两个时间来自同一客户端，确实有发送前长尾。后端队列3245条P95 5ms、最大937ms，ASR锁等待P95 0ms但最大149ms；不是所有后端帧都恒定5ms。ASR最近append到partial592条P95 358ms，Redis到SSE591条P95 9ms。

networkMs和SSE到浏览器时间跨客户端/服务器时钟，未校准偏差；它们的秒级长尾只能作线索，不能给出纯网络精确归因。desktopVadToWorklet复用了整段语音的确认时间，也不能把P95约7.6秒当成每句话VAD等待。

约35秒本地采样中MIC采集计数持续增长，但新语音帧只增加1个；附近其它时段有零星/成批发帧。用户消息和实际讲话时刻没有独立时间标记，不能保证整个10秒讲话恰好落入窗口，因而不能单凭它断言VAD吞掉了整句话。服务器较晚采到的mic level0.087及帧增长也已保留。

## 目前判断和验证顺序

已确认助手发送前有秒级等待，且Mac当前同时使用蓝牙输入/输出与2.4GHz WiFi。蓝牙双工模式的音质影响、同频干扰、代理/链路长尾和助手音频处理，是应逐项隔离的因素；还没有确定唯一根因，不能把主观识别差全归责耳机，也不能仅因API P95已降就证明语音端到端正常。

1. 保留当前麦克风，先使用已有5GHz WiFi或网线做同句对照，检查ACK/发送队列是否改善。
2. 保留AirPods作输出，若有其它可用有线/USB输入，只更换麦克风再比较；本次枚举未见内建输入，不能要求此机选择不存在的“Mac内置麦克风”。
3. 产品侧在准确采样下分开核对输入电平/静音、VAD判定、ACK拥塞与浏览器交付，再制定蓝牙设备处理策略；保留权限/回声与噪声防护，不盲目改阈值或重新部署。

Apple说明，耳机同时启用麦克风与播放时会切换蓝牙模式并降低音质：[官方说明](https://support.apple.com/zh-cn/102217)。Apple也说明蓝牙与WiFi共用2.4GHz、改用5GHz可能减少干扰：[无线干扰说明](https://support.apple.com/zh-cn/102319)。这些是通用机制，不能替代本机因果对照。

证据：[汇总](cn-mac-bluetooth-audio-20261104/9caea1a5-diagnosis-summary.json)、[服务端累计分段](cn-mac-bluetooth-audio-20261104/dd41430a-runtime-current.json)、[本机采集/签名](cn-mac-bluetooth-audio-20261104/12204f62-local-audio-readonly.json)、[本机无线/代理](cn-mac-bluetooth-audio-20261104/adb42590-local-network-readonly.json)、[归属匹配后的数值状态](cn-mac-bluetooth-audio-20261104/b2ba6b43-matched-device-health.json)、[讲话采样时间线](cn-mac-bluetooth-audio-20261104/2c7e18bc-speech-check-timeline.json)。没有保存音频、问答、原始设备/用户/会话标识、SSID、MAC/IP或代理端点/凭据。
