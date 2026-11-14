# 国际服 2026-11-15 封版快照

`backend-runtime.tar.gz` 基于 2026-11-06 已封存 308 项公开运行输入，加 2026-11-10 已发布 Global 助手清单；`web-static.tar.gz` 基于既有251项静态快照，加2026-11-10的32项静态增量（16替换、16新增），最终267项。`desktop-source.tar.gz` 保存国际服2.0.0工作树桌面源码和构建所用根 lockfile；桌面安装包由 Global 1.3.6 发布制品以专用脚本增量构建，源码快照不是对已发布包逐字节重建的承诺。

`runtime-source-readonly-verification.json` 记录 2026-11-15 01:34 北京时间对当前运行 Backend 与 Web 的既有308项和267项公开文件逐 SHA 核验，以及对应容器和实际镜像。该记录检查已知文件；随后另做了范围内目录库存检查。没有检查私有环境或配置。资料 worker 沿用 `releases/20261102.1/global/material-worker-runtime.tar.gz` 历史已封存来源；本次只读核验现运行镜像和 267 项文件哈希一致。`runtime-complete-inventory-verification.json` 还核对了后端、worker 的应用/迁移/提示词目录和 Web 根目录；后端发现 1 个发布锁文件，是运行元数据，非源码。目录扫描未涵盖非普通文件及私有环境。

`snapshot-manifest.json` 记录三份归档及逐文件 SHA。原 Global 发布记录和未来重建镜像参见 `docs/releases/global-companion-floating-2.0.0-20261110.md`；不得把根目录国服源码直接当作国际服当前线上源码。归档不包含安装包、镜像层、私有配置、密钥或用户数据；后续真实发布必须再次核对当前线上来源和业务门禁。
