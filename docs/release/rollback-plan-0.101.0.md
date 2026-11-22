# v0.101.0 恢复步骤

当升级后无法恢复原单元、整体验收发生误放或误拦，或下载的包与远端记录的 SHA-256 不一致时，保存触发操作、单元、制品、原始回执及版本。先暂停对受影响数据的写入。

1. 备份消费项目的治理数据、工件、宿主设置及安装来源，并在独立目录检查备份可读。升级后新增的证据另存，保留其原路径和 SHA-256。
2. 在隔离目录检出前版标签 `v0.100.0`。核对其剥离提交为 `37ac96d322e4c874f0ba83ff6fe80b392fe2cb51`。从该树执行 `npm pack --ignore-scripts`，将生成的包离线安装到空消费目录。也可核实并使用[前版正式附件](https://github.com/peterwangze/software-project-governance/releases/tag/v0.100.0)。
3. 在升级前的数据副本中运行包内 `governance-bootstrap --format json`，确认根正确，再用 `loop status --unit <原单元> --json` 核对原目标、验收和证据。对照升级前的原始记录确认一次正常操作。将升级后产生的单元留在已备份的新版本数据中，供相应版本的读取器复核。
4. 副本恢复验证通过且恢复范围已获授权后，再切换实际安装。打标签前修正候选，应在新树复跑受影响的独立验收与 CI。已公开的版本保留其标签和下载摘要，后续修复使用新的版本号并附恢复说明。

RISK-036 跟踪外部验证。未声明 official approval、marketplace approval、universal/full runtime support，未声明 external first-session pilot success。
