# Global release 20261022.1

本标签 `release-global-20261022.1` 封存当前国际服版本，基于 `release-global-20261019.1`。新鲜实际基线与离线包已验证；提交、标签及推送结果由Git远端引用确认，不以包就绪代替Git回执。封版不部署、不重启或更改线上业务。

国际服模型版本已于北京时间2026-10-22 01:40:29部署并于01:41:22独立verify通过。本封版仅承接该实际版本：Backend四个模型选择器、独立旧worker的共享选择器为 `deepseek-v4.1-flash-1017`；各自资料摘要仅补 `enable_thinking=false`。完整配置、端点和凭据留在服务器；公开增量见[model-overrides.json](model-overrides.json)。

Backend完整302项运行输入与worker267项分别归档并逐SHA验证。worker有48项与Backend仓库当前源码不同，不能把Backend根目录当作worker实际源码。两份独立tar分别以 `/app` 为逻辑根，保留已上线的少量AppleDouble文件，仅用于完整字节恢复。原文件内容及模型/摘要以外的差异不作清理或改写。

[manifest.json](manifest.json)绑定当前三个实际镜像、完整文件清单、223条接口的完整Schema和必要脱敏证据。`sealReady=true`仅表示包和运行证据就绪，不能代替Git操作完成证明。[live-verification.json](live-verification.json)来自本次新鲜只读核对，未用上线时历史回执替代。

## 恢复与验证

运行 `python3 releases/global-20261022.1/verify-release.py` 可离线核对所有封版文件、两份源tar和Web235静态包。它不连接生产、不调用模型、不执行Git。源tar是各组件独立字节恢复材料，不包含数据、环境文件、密钥或用户日志。

`image-recipes/backend/` 与 `image-recipes/material-worker/` 分别以原实际镜像为固定父镜像，仅COPY本次摘要文件。先保留或恢复对应父镜像，再在各自目录离线构建；不得将Backend镜像用于worker，也不能用普通全仓构建替代已验证增量。Docker构建元数据可能改变镜像ID，验收仍必须核对完整源/Settings和运行归属；当前实际镜像ID已明确记录在manifest。

Web本轮没有修改。[web-static.tar.gz](web-static.tar.gz)与[web-static-manifest.json](web-static-manifest.json)保存原235项公开文件和历史hash资源，[nginx.conf](nginx.conf)为实际原配置，包含既有21MiB资料上传封装规则。使用Python tar读取恢复，避免macOS把真实上线的AppleDouble文件吞为元数据。完整前端源码与字节可移植重建继续承接上一标签的 `releases/global-20261019.1/rebuild/`，本版本不重新构建Web。

## 行为、验证与限制

Global原会员/Creem、语言、简历UTC每日一次、模拟面试/联网原开关、多屏、ASR/TTS/Embedding/Rerank/MinerU及全部Prompt保持。鉴权、状态、心跳、预取、网页1.5秒缓存和ACK5秒合并已在原封版中存在，本次只保全，不宣称重新引入性能优化。

142项模型/语言/截图/Global商业离线回归、137项发布控制器/门禁回归及5项本地镜像probe情景通过；两个实际候选镜像分别通过禁网检查。沿用前一天国际服10项真实合成适配器最终通过证据，并保留视觉v1错误合同的初次失败记录。9项公开检查通过，上线后119.83秒观察未发现ERROR/Traceback/HTTP5xx或重启；没有生产回退演练、真实用户资料回放或压测，这些结果不能证明长期P95或所有用户文件均可处理。

历史本地开发记录中的“未授权部署”或上线记录中的“未Git操作”各自保留原日期语义。后续新任务从本次已核验标签新建分支，国服保持独立封版。
