# Code Review — FIX-478（consumer 布局 bootstrap 段边界泛化）

- 审查方: Code Reviewer（独立只读；未修改任何文件、未 commit、未 spawn）
- 审查对象: 未提交 diff（2 文件，+123/−10）：`skills/software-project-governance/infra/hooks/pre-commit`（+22/−10）、`skills/software-project-governance/infra/tests/test_verify_workflow.py`（+101）
- 轮次: R0
- 日期: 2026-10-31

| 维度 | 结论 | 证据 |
|---|---|---|
| 正确性 | **PASS** | 投影=标题后至首个非模板 H2；dogfood 边界 H2 仍为结束界：repo CLAUDE.md 旧/新投影 **SAME 722B**；standard 形态夹具旧/新 **SAME 59B**；consumer-native 夹具投影旧 9B→新 **69B**（`## 项目信息`/`## 治理入口` 进入比较面）。端到端：同一夹带夹具（owner alice→MALLORY）**HEAD hook rc=0 ALLOW** / **新 hook rc=1 BLOCK「BOOTSTRAP DISCIPLINE」**；仅 bootstrap 内变更夹具两侧均 ALLOW → RED 真实有效、GREEN 不误拦。 |
| 健壮性 | **PASS**（含 P2 注记） | 7 夹具 × 4 组合（`LC_ALL=C` / `zh_CN.UTF-8` / `gawk --posix` / `gawk`）投影 sha256 **全同**；consumer_std 输入 214B→投影 59B 证明中文五段白名单在 C locale 仍生效。CRLF 投影（去 CR）与 LF SAME；无标题=整文件入比较面；空文件被上游 `grep -q "## Governance Bootstrap"` 先拒；重复标题会重新开豁免但 staged 新增必改变投影→拦；无效 UTF-8 字节 gawk 不报错。**mawk/busybox 本机 NOT FOUND，未实测**（gawk --posix 代理，残余披露）。 |
| 单源 | **PASS** | `in_bootstrap` 仅 143-146 一处实现；两处调用同一 `claude_non_bootstrap_lines`；函数定义早于调用；`bash -n` exit 0。 |
| 纪律面 | **PASS** | FIX-477 段（175-179）与 FIX-081 early-return（155-157）未在 diff 中，对应 7 用例全过；负例改的是 `## 项目信息` 内 owner 行（标题之后区域，非标题本身）。 |
| 测试质量 | **PASS**（P3×3） | 夹具确为 consumer-native（无 dogfood 边界 H2、有项目 H2）；双 tempfile 隔离 + `SPG_HOME` 指向临时安装根 + pop `SOFTWARE_PROJECT_GOVERNANCE_HOME`；断言 rc + marker。 |
| 回归 | **PASS** | ①`PreCommitClaudeBootstrapUpgradeHookTests -v` **9/9 OK（19.8s）**；②`test_hooks` **70/70 OK（137.1s）**；③`test_pre_commit_review_evidence` **11/11 OK（3.2s）**；附加相邻钩子回归 `CommitMessageSourceHardeningTests`+`ExternalInstalledRuntimePathResolverTests` **19/19 OK（79.1s）**。 |
| 范围 | **PASS** | 仅 2 文件、无无关改动；hook 25044B **CR=0（LF）**；`git diff --check` exit 0。 |

## 发现项

- **P2-1（既有缺陷，非本 diff 引入）** — `|| true` 掩盖 awk 失败 → 双侧空投影相等 → **误放行**。实测：PATH 前置 `awk` 桩（exit 2）后跑同一 consumer-native 夹带夹具，hook **rc=0 且打印「bootstrap self-upgrade detected」**（owner alice→MALLORY 放行）；旧 HEAD hook 同样带 `|| true`（非回归）。建议 fail-closed（`command -v awk` 前置校验或捕获 rc；去掉 `|| true` 让 `set -e` 生效），约 2 行。`--no-verify` 已是文档化逃生口，严重度封顶 P2。
- **P3-1** — 注释称 `## 当前项目治理状态快速入口` 为 "dogfood-only"，实际它也在 standard/strict 消费方注入模板内（`commands/governance-init.md:331`）；功能与旧实现同界（无回归），但白名单应改为「从 canonical 模板派生/显式登记」。
- **P3-2** — 测试 helper 三份近重复（仅 CLAUDE.md 载荷不同），建议参数化防夹具前提漂移。
- **P3-3** — 新增用例未覆盖 CRLF / standard-layout / 重复标题边界（审查侧手工探针已覆盖，未入 CI）。

**审查结论：APPROVED_WITH_NOTES**
**unresolved_blockers=0**
