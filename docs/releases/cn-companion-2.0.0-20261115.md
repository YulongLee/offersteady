# 国服伴随程序 2.0.0 发布：2026-11-15

状态：**00:37:44（北京时间）国服 Backend 更新完成**。实际候选 `sha256:4c1b3c60ba2366bce93831cc0684aab703935388f8b38a6d1a95444f9d96b25e`，容器 `924af8013ec7f95be9533c538788eb2852ce64c4c604193c96da7ecb3d2dfedd`；运行健康。用户授权国服更新并接受旧版新连接/新开始时升级要求。未发布国际服、未提交或推送 Git。

## 发布范围

保留三平台 2.0.0 安装包与旧 1.3.6 精确下载。新清单保留六条记录，旧三条 `hiddenFromListing: true`，仅 Backend `web.py` 的公开列表过滤该布尔标记；旧精确下载路径仍可用。Backend 其余 236 份输入保留，Web 实际 366 文件及其他七组件不变。原 58d39 镜像为固定回退，回退之前必须重新核实归属及全部业务门禁，不得中断用户工作。

三个新对象以不可覆盖方式上传并完整读回；切换控制器在切换前将新旧六对象再次按长度、MIME 及 SHA-256 串行验证。完成后公开匿名状态返回三个 2.0.0 条目，新旧六个精确下载路径的单字节 Range 请求均通过；另有16条公开页面/健康检查通过。后台实际版本门槛读取清单，旧助手新绑定、启动和重复 start 可能要求先升级；不主动结束现有会话。

## 基线与验收

本次基于固定国服 Backend `sha256:58d39c035650ba6619bd5783b6e344a49e1a10eadad962ee9a7aa9638a5e7e43`、容器 `fe11497d82c625b47dc7e5ffcd0ed6463d17dda9259e18db18a81d45f9021a94`；候选只修改 `apps/backend/app/modules/web.py` 与 `apps/backend/app/desktop_release_manifest.json`。新 web.py SHA 为 `e4865462d344f579db425414fecf06a74378ac6e70df22c74337c3813d26d3a0`，新清单 SHA 为 `6cb2a0e01afa7c8539a1cccdb1f0d0c8dd1907304ffe71711438ae6b70061340`。

隔离实际候选探针核验 238 输入、162 Python 编译、203 API 路径及完整 Schema、344 配置、44 依赖，网络请求/数据库操作/文件写入为0；合成旧新六个下载路由与三条可见列表通过。切换前 prepare、preflight 和切换时按控制器验证归属、单 writer、七项业务门禁、国服实体和 TCP8000 零连接。历史7条失败任务和22条孤立预占依原口径保留。独立执行控制器 verify 返回 `verified:true`、238输入、344设置、203路径和七非目标保持。

原部署 SSH 会话没有返回退出回执，但只读检查确认部署控制器进程已退出、`deployed.json`/`progress.json` 及公开验收记录存在，且实际容器归属和独立 verify 均通过；没有重复切换。服务器只读证据位于 `/opt/offersteady/releases/20261114-cn-companion-200-1/`。执行 deploy 的本地 SSH 退出状态未知，不以成功退出码冒充已获得。

## 观察与限制

独立只读反代聚合发现切换期 **00:37:10–00:37:24 共有52次 HTTP 502**；同一52条错误日志不重复计数。00:40:19 时最近1分钟 Web 136行，5xx 与 ERROR 均为0。此前 Backend 有界5分钟聚合535行，无5xx、ERROR 或 stream_failed，但准确采样时间未记录。短时样本不能证明后续无故障；另一次独立请求聚合读取失败，未按零错误处理。

用户此前测试 Zoom 共享和录制中浮窗仍可见；腾讯会议、钉钉和飞书在其测试环境下正常，不承诺所有会议软件隐藏。Windows 包未签名、尚未真实 Windows 真机验收；最终 Mac 包的实际音频及线上端到端链路仍需用户验证。桌面 410项 Vitest 通过；标准 `npm test` 的国际服文案生成前置步骤未通过，未宣称完整标准测试通过。

发布证据：[独立切换及短时观察](../../releases/20261115.1/evidence/independent-post-cutover-observation.json)、本地只读基线和候选材料（保存在原工作区 artifacts，不入 Git）、[发布准备及本地测试](cn-companion-2.0.0-release-preparation-20261114.md)、[发布规范](../../openspec/changes/release-cn-companion-2-0-0/proposal.md)。
