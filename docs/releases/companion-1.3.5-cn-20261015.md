# 国服伴随助手 1.3.5：2026-10-15

用户明确授权 Windows 与 macOS 助手正式上线。发布范围为国服 macOS arm64、macOS x64、Windows x64 三种安装包及下载清单；本地下一题服务端优化仍不部署，Global 与其他业务组件保持既有版本。

关联 [正式发布变更](../../openspec/changes/release-cn-companion-1-3-5/proposal.md)、[修复变更](../../openspec/changes/fix-mock-local-audio-and-turn-latency/proposal.md) 和 [此前本地验证](mock-local-audio-and-turn-latency-20261015.1.md)。

## 本次客户端修复

- 补齐 Mac 主程序与 Renderer Helper 的实际音频输入签名权限，正式发布检查验证实际签名，而非只读取 plist 模板。
- 模拟面试麦克风失败保留原因，提供手动重试，避免反复自动申请权限；音量取自本轮同一条 PCM 采集。
- 设备能力登记保留模拟面试协议与最新权限，避免周期登记覆盖已上报的可用能力。
- 停止、切题和采集初始化失败时正确释放资源，不复用上一轮音频。

三平台沿用国服稳定身份、协议 2.0 和生产 HTTPS 默认地址，无 local-test-runtime.json、Global 覆盖、测试用户或服务端凭据。正式 Mac 最低 macOS 14.2+，Windows 最低 Windows 10 22H2+；私人 Ventura 兼容包未更新。

## 验证记录

- Desktop：41 个文件、228 项测试全部通过；类型检查与构建通过。
- Windows：NSIS 外层及内层 app-64.7z 完整性、实际 x64 PE、22 个冻结 dist 文件、无服务覆盖配置与凭据检查通过。保留真实未签名状态，没有宣称 Authenticode 已验证。
- 发布保护：54 项合成漂移、原子切换、丢失 SSH 回执、恢复已暂存候选与回滚回归，加上既有 4 项 publication 回归，共 58 项通过。本机合成 Docker 与线上实际构建均确认单 COPY 增加一层、Config 不变；实际候选清单权限为 0644。
- Mac：两架构分别执行主程序及原生采集程序架构、版本、22 个冻结 dist 文件、实际音频输入权限、Developer ID 签名、公证与 staple、App/DMG Gatekeeper 检查。
- 实体 Windows/Intel Mac 的真实麦克风、扬声器与耳机验收未代替用户执行；结构与签名验证不能替代物理设备试用。

## 发布状态

三个安装包正式构建与终检、OSS 完整读回与校验均通过。2026-10-15 03:57（北京时间）已原子更新国服清单，随后公开下载验收全部通过。

| 平台 | 文件 | 字节 | SHA-256 |
| --- | --- | ---: | --- |
| macOS Apple Silicon | `OfferSteady-Companion-1.3.5-macOS-arm64.dmg` | 126182643 | `9b6d95aa1fb0109cff7c2085c0418839228966e845bd19ea54db464882e8dce7` |
| macOS Intel | `OfferSteady-Companion-1.3.5-macOS-x64.dmg` | 129925399 | `9cd6db94c7883cd9e8faba373ed9217ade7ff312c33afd4c3986a54f6a17804b` |
| Windows x64 | `OfferSteady-Companion-Setup-1.3.5-Windows-x64.exe` | 102155896 | `2ce3ba67c97566c31734a3c8f75313526d47a118503ebba5dcd34520e6e6f3e0` |

Intel 首次构建停在 Electron 运行时下载；通过官方 SHA-256 验证的同版本 42.5.0 x64 缓存和现有 `OFFERSTEADY_ELECTRON_DIST` 参数完成重试，没有修改打包源码、运行时版本或跳过签名公证。

首次清单镜像构建因目标服务器缺少 Buildx 而回退 legacy builder，不支持 `COPY --chmod`；当时还未切换官网清单或未来镜像标签。保留失败 Dockerfile 后使用普通 COPY（源文件已显式 0644），核验候选实际权限、单层差异、Config 与业务源码，再通过 `--resume-staged --apply` 完成恢复发布。未安装新构建组件或重启业务服务。

发布清单 SHA-256：`76ba8b6009071d4c4c0b824b6bbbf1c05c7d848f95c1ab08649c9e9e05c4a76a`。未来重建镜像：`sha256:c24d1237ca4790eba53f07b46ff1ba35a9778dea36b9e5b070dcee4c7e85766c`，标签 `compose-backend:latest`；候选标签 `offersteady-cn-backend:companion-135-manifest-20261015`，回滚标签 `offersteady-cn-backend:companion-135-manifest-rollback-20261015`。持久备份目录 `/opt/offersteady/releases/20261015-cn-companion-135-1`。

公开验收：`/api/v1/web/state` 三平台均为 1.3.5；三个真实下载 API 的 Range 返回 206、整包返回 200，MIME、大小、SHA-256 与正式本地产物一致。`/healthz`、登录和模拟面试网页返回 200；模拟面试 capabilities 为 enabled/protocol 2.0，匿名列表返回预期的认证保护 401。八个业务组件的 ID、镜像、启动时间与重启次数全部与发布前相同，四项业务源码哈希完全相同。

用户下载：[Windows x64](https://mianshiwen.cn/api/v1/web/downloads/desktop/OfferSteady-Companion-Setup-1.3.5-Windows-x64.exe)、[Mac Apple Silicon](https://mianshiwen.cn/api/v1/web/downloads/desktop/OfferSteady-Companion-1.3.5-macOS-arm64.dmg)、[Mac Intel](https://mianshiwen.cn/api/v1/web/downloads/desktop/OfferSteady-Companion-1.3.5-macOS-x64.dmg)。安装前完全退出旧程序。Windows 仍未签名，系统可能显示提示；Mac 正式包已签名、公证。

Git 封版标签：`release-cn-companion-1.3.5-20261015`。同轮本地服务端开发与测试代码一并保存供后续验证，线上仍是上述实际 heartbeat 基线加清单；不能从本标签完整构建 Backend 并认为它等于本次线上客户端发布。

## 发布方式与回滚

以实际运行 Backend 镜像 `sha256:ec510532ca598878e147c4277e6da9776924fbf056ed942ab4cc2bf110f398bb` 和容器 `6c16f7bf71385ed4d9d8d1dc409b7c7d8704861bbf7b66596e191bb64cbaf025` 为基线，避免从旧 `current` 源码重建。原清单 SHA-256 为 `10a217b8dd766bd46b6ebfacc6d020bdcd356f5b2fa997ac6cd6f72f281db1d4`，三平台均为 1.3.2。

先上传三件不可变版本对象并完整读回验证，再原子替换正在运行容器的发布清单。清单按请求读取，网页与版本检查立即使用新值，无须业务容器重启。额外保留只增加清单的镜像和旧镜像标签，确保后续无构建重建可保持新下载版本。

普通面试的版本门槛在新绑定或开始面试时检查；已绑定正在进行的旧版会话不会因清单更新被主动断开。模拟面试采集验证协议、权限和绑定，不因清单版本更新主动关闭。使用者应完全退出旧助手、安装 1.3.5，再进行新的绑定。

回滚需要恢复备份清单并恢复 `compose-backend` 镜像标签，不删除已上传对象。运行容器 inspect 的 Image 仍是原镜像，热更新清单位于可写层；以后以该 Image 为基线发布代码时，必须显式携带当前清单，不能把旧镜像中的 1.3.2 清单覆盖回来。

发布保护脚本默认只读，只有显式 `--apply` 才发布。需要手动回滚时，在保留本地新清单和基线目录的仓库中运行以下程序；它先验证当前仍是本次发布状态，再恢复精确的旧清单与镜像标签。

```python
import sys
sys.path.insert(0, "scripts")
import release_cn_companion_manifest as release

plan = release.load_plan(
    "apps/backend/app/desktop_release_manifest.json",
    "artifacts/companion-cn-1.3.5-20261015/baseline",
    release.DEFAULT_RELEASE_DIR,
)
remote = release.Remote()
candidate = remote.image(release.NEW_TAG)
release.verify_candidate(remote, plan, candidate)
release.verify_live(remote, plan, expected_manifest_sha=plan["newManifestSha"], expected_future_image=candidate["Id"])
release.copy_and_switch(remote, plan, rollback=True)
remote.run(["docker", "tag", release.BASE_IMAGE, release.FUTURE_TAG])
release.verify_live(remote, plan)
```

OSS 的三个 `latest.json` 原文件也已单独备份；现有官网读取容器内清单，回滚官网版本不依赖这些对象。若同步回滚 OSS latest，仅恢复备份 JSON，保留所有 1.3.5 安装包。
