# 国服伴随助手1.3.6：2026-11-02

状态：**2026-11-02 01:26:04（北京时间）完成国服下载清单切换，三平台公开下载和只读验收通过。业务容器未重启。** 未执行Git提交/推送。

用户授权将当前助手正式上线。来源为[Local-r3](companion-1.3.6-local-r3-20261101.md)，生产范围见[发布规范](../../openspec/changes/release-cn-companion-1-3-6/proposal.md)。仅国服macOS arm64、macOS x64、Windows x64安装包和下载清单，不部署本地Web/Backend笔试配套、不更新国际服或Git。

## 客户端内容

- 真实麦克风权限与晚授权同步，模拟面试收音中断后的资源释放、旧回调隔离和手动重试。
- 笔试心跳有界等待、网络/系统恢复后的合并刷新，有效笔试期间短时防应用挂起。
- 笔试截屏有界队列与去重、捕获/上传超时、取消及跨场旧结果隔离，防止旧操作释放新锁。
- 保持原外观，隐藏主窗口及Dock/任务栏，菜单栏/托盘保留透明可点击位置恢复；无新增独立“重新检查”按钮。

助手可以连接现有国服；现有Backend会忽略新可选查询参数，助手严格校验旧响应。完整同场次/指定请求读取和网页失败提示仍在本地，未随本次发布。旧场次异常请求不能明确核实时保守放弃，不能声称配套已上线。

## 验证

桌面54文件394项、类型检查通过，包校验工具20项通过。实际执行的发布控制器70项、不可变上传器17项及独立5个未知态/丢回执场景通过；发布后验收修订版控制器84项通过。三平台88份源输入与最终Local-r3一致，26份非native dist逐字一致；两架构native编译载荷分别与已测试版本一致。

Mac正式包须通过实际Developer ID/音频权限、App与DMG公证、staple、Gatekeeper及DMG实际载荷检查；Windows核验NSIS外/内层、104份安装文件及真实x64，沿用unsigned状态。payload工具的local-only公证字段不是正式公证评估，正式证明另存包记录和终检日志摘要。实体Windows/Intel音频、真实网络/休眠及完整线上面试未由结构验证代替。

## 发布保护及重建

实际Backend基线为`sha256:c62df7ddbb92627de83c7c2733574c862678b120a11d051b346b9d13abfcf58a`，运行容器`edd16865e5d5c0b1e57f33a696faf28cdffc340846db65e70150bb77a418a4dd`，232份运行输入及8组件生命周期/配置摘要、15份冻结Compose输入核对。原清单SHA-256为`76ba8b6009071d4c4c0b824b6bbbf1c05c7d848f95c1ab08649c9e9e05c4a76a`。

先将三包上传CN不可变版本路径并完整读回。上传禁止覆盖已有对象；已有不同字节停止。三个OSS latest文件不被当前官网或版本门槛读取，保持原字节。下载清单按请求读取，采用同目录锁、旧hash比较、fsync和原子rename，不重启或替换业务容器，不终止用户工作。

现有版本门槛保留：新绑定或新开始面试的旧助手需要升级，已绑定进行中的面试不被主动关闭。用户安装前应完全退出旧助手。

专用控制器`scripts/release_cn_companion_136_manifest.py`从实际固定镜像只增加一层清单，验证Config全等及完整运行输入；新镜像与`backend-image.compose.json`保存在`/opt/offersteady/releases/20261102-cn-companion-136-1`。旧`compose-backend:latest`与历史Compose不改。普通restart保留热清单；未来recreate必须显式携带新固定镜像覆盖或将当前清单纳入后续候选，不能直接从旧固定镜像恢复。

精确回滚使用同控制器的`--rollback`，共同参数为`--manifest docs/releases/companion-1.3.6-cn-20261102/desktop_release_manifest.json --baseline-dir artifacts/companion-cn-1.3.6-20261102/baseline`。仅已知发布归属/源码/配置/清单均匹配时允许恢复旧清单；未知状态停止。保留不可变包，不改OSS latest、不回退业务镜像或结束用户。未来执行须重新获得对应操作授权并核对实际状态。

## 最终安装包及公开验收

| 平台 | 大小（字节） | SHA-256 |
| --- | ---: | --- |
| macOS arm64 | 126284123 | `dcc029f5d3c2c0073922ee91ad37a389eaf63b0dedf82050f736a05b95bfc0ad` |
| macOS x64 | 129963799 | `2b577117e6f8a02100b42e8e9e58fe2467242ce269286d1c1baa67940cd69ae8` |
| Windows x64 | 102172270 | `18fd93b8d8c2ff412c0baea7a728eb392ba70962bae96a1f5bb27224ab811f54` |

三个公开state条目均为1.3.6；真实下载API均Range 206、完整下载200，MIME、长度及SHA-256与正式产物一致。健康、登录、模拟面试入口/capabilities为200，匿名模拟面试列表保持401。八个组件ID、镜像、启动时间、重启数及配置保持；完整232份Backend输入仅发布清单变化，15份历史Compose和旧latest镜像标签保持。三个OSS latest逐hash不变。

新清单SHA-256：`d7b106a6497bce873d67c2c81b045fab520aaa7382296978a8f6a04056e10927`。仅增加该清单的未来重建镜像：`sha256:15824dc57cdaaa817d171f11e3750cc84919750259a595c4741b042bbb2129ab`；实际运行Backend仍为上述c62df镜像。没有调用Compose up、结束用户或放宽工作门禁。发布前只读观察普通live、近期准备页、模拟active计数均0。

首次独立验收曾报配置摘要差异。只读12次检查捕获2次PostgreSQL两个完整Mount对象返回顺序反转；仅交换顺序即可精确恢复原whole Config/HostConfig/Mounts摘要，未发现实际配置变化。修订验收器先比原摘要，只在恰好两项时尝试整对象反序；所有字段均保留，真实字段、增删和重复挂载变化仍拒绝。14项回归新增后共84项通过，独立8次复查亦保持。**没有重写基线/服务器存证，没有再执行apply或回滚。**

实际发布执行控制器SHA为`805d8df7fe6ca28a3c4cf9155d6bf7539d32bcc3236e18fcdbef89ad91564872`；修正后的只读验收器SHA为`e6fc8574c95c3cb78d7d3639aa0c8072e32bb31d2204517b165f1b793f36e498`。两版用途分别记录，原执行源码留在本地证据。发布后的短时窗口检查Backend589行、Web282行，ERROR/CRITICAL、Traceback和HTTP5xx均0；此结果不代表长期故障率或真实音频硬件验收。

下载：[Windows](https://mianshiwen.cn/api/v1/web/downloads/desktop/OfferSteady-Companion-Setup-1.3.6-Windows-x64.exe)、[Mac Apple Silicon](https://mianshiwen.cn/api/v1/web/downloads/desktop/OfferSteady-Companion-1.3.6-macOS-arm64.dmg)、[Mac Intel](https://mianshiwen.cn/api/v1/web/downloads/desktop/OfferSteady-Companion-1.3.6-macOS-x64.dmg)。安装前完全退出旧助手。

[官网清单](companion-1.3.6-cn-20261102/desktop_release_manifest.json)、[三平台同源](companion-1.3.6-cn-20261102/cross-platform-source-verification.json)、[ARM正式包](companion-1.3.6-cn-20261102/mac-arm64-package.json)、[Intel正式包](companion-1.3.6-cn-20261102/mac-x64-package.json)、[Windows包](companion-1.3.6-cn-20261102/windows-x64-package.json)、[OSS完整读回](companion-1.3.6-cn-20261102/object-readback-verification.json)、[公开下载](companion-1.3.6-cn-20261102/public-verification.json)、[运行验收](companion-1.3.6-cn-20261102/verified-published.json)、[独立复核](companion-1.3.6-cn-20261102/independent-release-review.json)、[错误聚合](companion-1.3.6-cn-20261102/post-release-error-summary.json)。

完整本地证据：`artifacts/companion-cn-1.3.6-20261102/`。生产配置和凭据未写入仓库、发布记录或安装包；没有原始用户日志或资料进入证据。
