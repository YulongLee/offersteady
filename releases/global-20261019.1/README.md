# Global release 20261019.1

标签 **`release-global-20261019.1`**；分支 `codex/release-global-20261019-1`。这是2026年10月19日当前国际服Backend/Web的独立封版。用户授权上传Git；封版过程不发布、不重启服务。不得用于覆盖国服。

[manifest.json](manifest.json)绑定实际镜像和恢复文件SHA。[live-verification.json](live-verification.json)是封版前新鲜只读核验；302项实际Backend和235项实际Web逐SHA相同，运行健康、restart0。源码位于仓库原路径；[Backend输入清单](backend-runtime-manifest.json)、[Global Web源码清单](frontend-source-manifest.json)、[Web生产清单](web-static-manifest.json)、[完整API](openapi.json)与[原Nginx配置](nginx.conf)均保留。数据库与私有环境不在归档内。

新增笔试英文Multi-screen answers默认关闭；开启后Capture最多4张，再Answer统一处理，采集不调模型/不占权益，批答沿用一次原Global权益。普通/模拟面试、Global时间会员/Creem、简历UTC每日1次、语言/74 Prompt、鉴权/状态/问题预取与性能保持。桌面快捷键仍为原单图。

## 生产字节与重建

[web-static.tar.gz](web-static.tar.gz)是235项线上完整静态快照，解包后应逐项符合`web-static-manifest.json`。它保留历史hash资源以及原来已上线的AppleDouble公开文件；这些文件用于字节恢复，并非新增功能。不能将未审阅的普通全量前端构建当作等价线上版本。

可移植重建脚本[rebuild/build-web-overlay.mjs](rebuild/build-web-overlay.mjs)以封版根目录源码、固定英文adapter扩展及原217项静态为输入，保留原Global单例/路由/会员逻辑，仅生成34项overlay。先在隔离克隆安装锁定依赖，再从仓库根执行：

```sh
python3 releases/global-20261019.1/verify-release.py --extract-baseline releases/global-20261019.1/rebuild/baseline-web-static
node releases/global-20261019.1/rebuild/build-web-overlay.mjs
```

解包使用[verify-release.py](verify-release.py)逐文件检查安全路径和SHA，避免macOS tar将实际存在的AppleDouble公开文件吞为元数据。该工具不连接服务器。静态全包同样可用其`--extract-static <目录>`选项恢复。

[封版重建验证](evidence/portable-overlay-verification.json)已确认可移植脚本生成的全部235项SHA与线上精确一致。编译器region注释保留原固定标识，以便字节复现；业务源码未变。结果在`rebuild/output/`，应将`candidate-static/`每项SHA与235项生产清单比较。脚本不访问生产或模型，不依赖本机绝对路径或国服源码。未来发布仍需实际镜像基线、固定候选及重复用户/财务/TCP保护，不直接重用本封版进行盲切。

## 验证证据与限制

[原上线摘要](evidence/release-summary.json)、[独立verify](evidence/actual-verify.json)、[180秒聚合观察](evidence/short-observation.json)及[公开策略](evidence/public-capture-policy.json)保留历史真实结果。89项Backend分批、10项元数据、17项编译Web、9项浏览器、完整类型检查、221项发布保护和实际候选28项离线检查通过；43项公开检查通过。观察窗口0错误/Traceback/5xx/重启，不能代表长期P95。没有真实模型质量、物理Windows/macOS捕获或生产业务模拟测试。

[已完成需求](../../openspec/changes/sync-global-written-multi-screen/tasks.md)与[逐场景核对](../../openspec/changes/sync-global-written-multi-screen/verification.md)保留。历史开发/发布记录中的“未Git操作”仅描述当时上线阶段；本封版是之后用户另行授权的Git归档。此前两次prepare夹具停止未切换服务；本版本绑定第三轮实际成功镜像。

封版工作区再次通过40项笔试后端回归、Global Web类型检查、302/221/235项快照校验与四项Spec严格校验。用于方法保全比较的原Global截图服务已保存到 [fixtures/screenshot_answer_service_before.py](fixtures/screenshot_answer_service_before.py)，回归测试只调整了夹具路径。三份鉴权文件保留实际生产原字节中的末尾空行，未为格式检查改写线上源。
