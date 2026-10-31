# Code Review — FIX-478 R1（delta 复审：fail-closed 补轮）

- 审查方: Code Reviewer（独立只读；未修改任何文件、未 commit、未 spawn）
- 轮次: R1（delta 范围；base = REVIEW-FIX-478-R0 / docs/reviews/review-FIX-478-CODE-R0.md）
- 审查对象: 工作树未提交 diff（2 文件，+171/−10）：`skills/software-project-governance/infra/hooks/pre-commit`（+41/−10）、`skills/software-project-governance/infra/tests/test_verify_workflow.py`（+140）
- 日期: 2026-10-31

| 维度 | 结论 | 证据（独立实测） |
|---|---|---|
| fail-closed（单侧/双侧/正常） | **PASS** | consumer-native 夹具：clean+正常 **rc=0 ALLOW**；夹带+正常 **rc=1 BLOCK**；**双侧失败 rc=1 BLOCK**；**HEAD 单侧失败 rc=1 BLOCK**；**STAGED 单侧失败 rc=1 BLOCK**；clean+双侧失败 **rc=1 BLOCK**（R0 该场景为 rc=0 放行） |
| `if !` × `set -e` | **PASS** | 探针：`set -e; if ! x=$(false); then x=SENTINEL; fi` → x=SENTINEL 且 shell 存活；实 hook 失败分支执行后继续至 Step 6 输出 BOOTSTRAP DISCIPLINE，未提前中止 |
| 哨兵内容伪造 | **P3（构造成功，理论面）** | staged CLAUDE.md 首行恰为 `__CLAUDE_PROJECTION_FAILED__:HEAD` + HEAD 侧投影失败 → rc=0 放行；触发需环境控制（≈已文档化 `--no-verify`）；内容侧无法令 gawk 失败（NUL/无效 UTF-8/CRLF 实测 rc=0） |
| 注入有效性（BASH_ENV shim） | **PASS**（注释 P3） | `type awk`=function；仅投影程序 return 2，其余 `command awk` 透传；shim 失效只会令测试变红、不会假绿；RED 判别力：回退 `|| true` → clean+shim rc=0 ALLOW，R1 现状 rc=1 BLOCK |
| R0 P2-1 闭合 | **CLOSED** | `|| true` 已移除；单侧/双侧失败均 BLOCK；R0 放行场景消失 |
| R0 P3-1（注释口径） | **部分闭合（P3）** | 已删「dogfood-only」并补维护口径；但仍把尾部 `## 当前项目治理状态快速入口` 写作「模板未拥有的 H2」——它实际在 standard/strict 消费方模板内（commands/governance-init.md:331）。功能无回归，措辞需再校正 |
| 注入/测试注释准确性 | **P3** | 新用例 docstring 仍写「PATH-prepended awk stub」（实现已改 BASH_ENV）；helper docstring「PATH stub cannot win」与本环境实测相反（PATH 桩实测生效 → rc=1 BLOCK） |
| 全量回归 | **PASS** | ①`PreCommitClaudeBootstrapUpgradeHookTests -v` **10/10 OK（21.5s）**；②`test_hooks` **70/70 OK（136.6s）**；③`test_pre_commit_review_evidence` **11/11 OK（3.2s）** |
| 范围/卫生 | **PASS** | 2 文件 +171/−10；hook 25632B CR=0（LF）；`bash -n` exit 0；`git diff --check` exit 0；无无关改动 |
| 新引入风险 | 仅 P3 | 哨兵伪造（理论、需环境控制）；无功能性回归。R0 P3-2（helper 近重复）、P3-3（CRLF/standard/重复标题未入 CI）仍未闭合（非阻断） |

## 发现项（R1）

- **P3-1（新）** 哨兵可被内容伪造——仅当「HEAD 侧投影失败」成立（环境控制 ≈ `--no-verify`）；建议布尔 `projection_failed` 标志替代魔法串，并修正注释「单侧失败必 block」的过强表述。
- **P3-2（新）** 测试注释两处不准确（陈旧 PATH 表述；「PATH 桩必失效」断言与实测相反），不影响用例判别力。
- **P3-3** R0 P3-1 部分闭合：尾部 H2 模板归属表述仍不准确。
- **P3-4** R0 P3-2/P3-3 遗留未闭合（helper 重复、边界用例未入 CI）。

**审查结论：APPROVED_WITH_NOTES**
**unresolved_blockers=0**
