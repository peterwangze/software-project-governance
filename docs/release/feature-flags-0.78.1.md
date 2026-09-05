# Feature Flags — 0.78.1 (REL-073)

**无 flag 声明**（0.78.0 先例格式延续）：0.78.1 不引入任何 feature flag / 配置开关 / 行为门控——全部变更为检查器修复、解析器边界修复、清理、测试卫生、文档与 dsh 适配安全面；无默认行为切换、无渐进 rollout 面。

涉及"行为变化"的项均为**缺陷恢复**（恢复设计语义）：FIX-282（加粗 ID 匹配）、FIX-287（按 profile 列数/节边界/括号节名）、FIX-288⑨（项目当前版本为基准）、FIX-284（TRIAGE 行族列数标准）、FIX-290（预设 skill 目录正确挂载）——按 VERSIONING.md L38 PATCH 面如实陈述，无 flag 化需求。

DSH upgrade path: `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`（bundle 安装则 `dsh plugin --profile web update` + 重启）。The persona version line (v0.78.1) reaches sessions only after sync/restart; a pulled-but-not-synced checkout still injects the old template. Do not claim session-level effects for unsynced installations.

## No-overclaim Boundaries

This candidate does not create or prove `v0.78.1` and does not close RISK-036 or RISK-039. 0.78.1 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
