# FIX-362 独立代码审查报告（CODE R0）

- **任务**: FIX-362 — fixture byte_copy promote（governance-status）
- **Round**: R0（独立审查，无前轮 findings）
- **Reviewer**: Code Reviewer Agent（独立，只读）
- **规范依据**: `agents/code-reviewer.md` + `skills/code-review/SKILL.md`
- **审查对象（恰 3 文件，工作树未提交变更）**:
  1. `project/e2e-test-project/commands/governance-status.md`（fixture 字节级同步）
  2. `skills/software-project-governance/core/version-projections.json`（+6：注册投影条目）
  3. `skills/software-project-governance/core/manifest.json`（+1：projection_ids 27→28）
- **canonical 路径勘误确认**: 真实 canonical = 仓库根 `commands/governance-status.md`（任务书曾误写 skills/ 路径）。本审查全部按勘误后路径执行；其字节数 18,668 B 与 triage 记录吻合。

---

## 总结论

## **APPROVED_WITH_NOTES** — unresolved_blockers=0

- P0 = 0，P1 = 0，P2 = 0，P3 = 2（均为披露/建议级，不阻塞）
- 硬门槛：5 维度全覆盖 ✓、每条发现标注级别 ✓、设计一致性 ✓（与 FIX-354/7a865b7 先例同型）、AI 专项 5 项 ✓（逐一有结论）

### 修复语义核对

EVD-1084 同族缺口 + FIX-354 F-05 先例同型，语义成立：

- pre-fix：fixture 在 HEAD 中为 blob `4d50556`、`git cat-file -s` = **14,493 B**（与申报的陈旧手工镜像字节数吻合）；
- post-fix：fixture 工作树字节追平 canonical（复验①）；
- 注册：`version-projections.json` 新增 `fixture-command-governance-status` byte_copy 条目（确定性再生面纳入），`manifest.json` projection_ids 同步 +1；
- 该 fixture 路径**不在** `declared_legacy_snapshots`（10 条中无 governance-status）——它此前属于 `_legacy_census` 的 undeclared 分歧面，本次按 `check_legacy_snapshots` 的 "converged → promote to byte_copy" 语义方向收敛，方向正确。

---

## 审查重点逐项结论（任务书①~⑦）

### ① SHA256 相等独立复算 — PASS

python hashlib 独立复算（非复用 Developer 输出）：

| 路径 | 字节数 | SHA256 | CRLF/LF |
|---|---|---|---|
| `project/e2e-test-project/commands/governance-status.md` | 18,668 | `0f235613474a5d549bcd9ab83b3f279555c47808cc27ae5778859975f8a75a68` | 0 / 168 |
| `commands/governance-status.md`（canonical） | 18,668 | `0f235613474a5d549bcd9ab83b3f279555c47808cc27ae5778859975f8a75a68` | 0 / 168 |

`bytes EQUAL: True`。与申报 SHA 前缀 `0f235613` 一致。

### ② 注册条目 schema 与 7a865b7 先例逐字段对照 — PASS

先例（`git show 7a865b7 -- core/version-projections.json`）注册的 `fixture-command-governance-init`：

```json
{"id": "fixture-command-governance-init", "kind": "byte_copy",
 "source": "commands/governance-init.md",
 "target": "project/e2e-test-project/commands/governance-init.md"}
```

本次 `fixture-command-governance-status`：

```json
{"id": "fixture-command-governance-status", "kind": "byte_copy",
 "source": "commands/governance-status.md",
 "target": "project/e2e-test-project/commands/governance-status.md"}
```

逐字段同型：id/kind/source/target 四字段、kind=byte_copy、source=canonical 仓库相对 POSIX 路径、target=fixture 仓库相对路径。插入位置同风格（同族相邻：init 之后、router 之前——与先例插入点一致，非字母序但工具按 set 比较不依赖顺序）。manifest 同步行插入同一位置（init 之后、router 之前），与先例 commit 中的 manifest 插入位置一致。manifest 未 bump `version` ——正确：版本 bump 属发布流程（REL-xxx）；`core-manifest` structured_json 投影（pointer `/version` ← SKILL frontmatter）在 check 28 项零 drift 中核实 manifest.version 与权威版本 0.84.0 一致。

### ③ manifest projection_ids set-equal 语义 — PASS（独立脚本核验）

`projection.py:144` 的合同比较是 `set(required_ids) != set(projection_ids)`——确为 set-equal（顺序无关）。独立脚本核验结果：

- registry count = 28 = manifest count = 28；`set-equal: True`；id 唯一
- 新 id 在 registry 与 manifest 双侧均存在
- kinds 双侧一致（byte_copy / structured_json / transformed_text）
- target 无冲突（`projection.py:197` 同 target 冲突检查也存在）

### ④ 消费者断言面复核 — PASS（本地直接复算，非推断）

将三处测试断言在真实文件上逐项复算：

| 断言点 | 内容 | 复算结果 |
|---|---|---|
| `test_verify_workflow.py:9531` `test_governance_status_docs_require_permission_mode` | canonical 4 needle | 零缺失 ✓ |
| `test_verify_workflow.py:9543` `test_governance_status_docs_require_delivery_trust_snapshot_contract` | canonical + fixture 双源 × 37 needle | 双源均零缺失 ✓ |
| `test_verify_workflow.py:14814` `test_governance_commands_do_not_emit_repo_local_hook_install_only` | `plugin_home` in = True；`cp skills/...hooks` in = False；`python skills/...verify_workflow.py` in = False | 三断言保持绿 ✓ |

语义等价论证成立且升级为实证：L9543 对 canonical 与 fixture 施加**同一 needle 列表**，两文本现已字节等同 → 必然同绿同红；canonical 侧不受本次变更影响（HEAD 未改），故 fixture 侧保持绿是结构性保证并被直接复算证实。任务书所指 L3031/L3068 经核实为 `RuntimeReadinessMatrixTests` 的 runtime-readiness-matrix 文档断言（docs/requirements 面），与 governance-status fixture 无关——"不改"结论正确。真实消费面即上表三处。

### ⑤ 范围纪律 — PASS

`git status --porcelain` 中 `test_verify_workflow.py` 不在 modified 列表 → Developer "test_verify_workflow 零改动" 声明与 git 事实一致。工作树其余 4 个改动（`infra/checks/review_domain.py`、`infra/checks/version.py`、`infra/tests/test_review_closure_legacy.py` M，`infra/tests/test_static_version_pins.py` ??）属并行任务，本审查未纳入、未采信。

### ⑥ git autocrlf 对确定性判定的影响 — PASS（附 P3-1 披露）

- `core.autocrlf=true`；`.gitattributes` 仅锁 `*.py`/`*.json` 为 `eol=lf`，`*.md` 未锁定。
- 工作树：两文件 `git ls-files --eol` 均 `i/lf w/lf`（当前无 CRLF）；SHA `0f235613…` 是 LF 字节哈希。
- index 侧：`git hash-object`（clean filter 后）两文件 blob **同为 `fc31b5d`** → 提交后仓库内字节确定性成立，投影相等性不依赖工作树换行状态入库。
- clone/checkout 推演：两文件同为 `.md`、属性相同，autocrlf 的 smudge 转换对称 → 干净 clone 后两边同转 CRLF，byte_copy 相等性保持；但绝对 SHA256 将变为 CRLF 版本值（`0f235613…` 非平台不变量）。byte_copy 精确字节（无归一化）语义由 `projection.py:32` 与 `test_release_ledger.py:708`（`test_byte_copy_crlf_difference_requires_exact_rewrite`）双重看护。
- 残余风险见 P3-1（单边 re-checkout 中间态）。

### ⑦ AI 专项 5 项 — 全部通过

| # | 检查项 | 结论 | 证据 |
|---|---|---|---|
| 1 | mock 残留 | 无 | diff 为命令文档+JSON 注册；"降级为既有手工读取流程"是真实降级路径描述，非 mock 桩 |
| 2 | 硬编码返回值 | 无 | 注册条目四字段值全部对应真实路径；文档无虚构固定输出 |
| 3 | 幻觉 API 调用 | 无 | fixture 引用的子命令逐一在 `verify_workflow.py` dispatch 表证实：`status`(L24675, 且 L10952 支持 `--json`)、`first-run-demo`(L24694)、`governance-context`(L24676)、`check-governance`(L24683)、`check-governance-pack-status`(L24742) |
| 4 | 未实现 TODO | 无 | 全量 diff 无 TODO/FIXME/占位符 |
| 5 | 过度实现 | 无 | 注册最小同型四字段、manifest 仅 +1 同步行，无多余机制 |

---

## Findings

### P0 阻塞（0 项）

无。

### P1 关键（0 项）

无。

### P2 建议（0 项）

无。

### P3 讨论（2 项，均不阻塞）

- **P3-1｜byte_copy 绝对 SHA 的平台换行敏感性（审查⑥产出）**：`.gitattributes` 未锁 `*.md`，`core.autocrlf=true` 下干净 clone 会把两个 `.md` 同转 CRLF——byte_copy **相等性**保持，但本报告记录的 SHA256 `0f235613…` 仅在 LF 工作树成立；理论存在"单边文件被 git re-checkout 而另一边未触碰"的中间态漂移窗口（操作顺序问题，非本次变更引入，且有 census/check 双机制兜底）。建议：后续将 `*.md text eol=lf` 纳入 `.gitattributes`（延续 FIX-242/FIX-250 先例），使绝对字节哈希也平台稳定；或维持现状并在文档记录该边界。
- **P3-2｜mirror census 仍有未声明分歧面（披露）**：复验 check 输出 `census: inventory=284, identical=55, divergent=37, absent=179, declared=10, undeclared_out_of_scope=27`。本次修复把 governance-status 1 个面从"未声明分歧"收敛为 projected 一致性面；其余 divergent/undeclared 为**既有**披露状态（`projection.py` `_legacy_census` 文档明示 counted-not-fixed），是后续同族 byte_copy promote 的候选池，不属本任务回归。

---

## 独立复验记录（3 项，Reviewer 亲测）

| # | 复验项 | 命令/方法 | 结果 | 与申报对照 |
|---|---|---|---|---|
| 1 | SHA256/字节相等 | python hashlib 双文件读字节 | 18,668B 双侧同 SHA `0f235613…a68`，EQUAL=True；index blob 同为 `fc31b5d` | ✓ 一致 |
| 2 | release-projection check（只读） | `python …/verify_workflow.py release-projection`（exit 0） | PASS，projections_checked=28，declared_legacy_snapshots=10，converged=[]/missing=[]/issues=[] | ✓ 一致 |
| 3 | manifest↔registry set-equal | python json 独立脚本 | 双侧 28 条 set 相等、id 唯一、kinds 一致、无 target 冲突、新 id 双注册 | ✓ 一致 |
| 附 | 消费者断言本地复算（④） | python needle 复算 | L9531/L9543/L14814 全部保持绿 | ✓ 一致 |

### 申报依赖项（如实标注：本轮未独立复跑）

- `test_verify_workflow 3F/903P`（3F=loop-runtime-claims/FIX-300 既有基线）、`test_projection_legacy_snapshots 16 passed`、`verify` 全子命令 PASSED、cross-refs/manifest PASS（786 canonical）——均标 **Developer 申报，本轮未复跑**（Reviewer 只读约束+复验额度 1~3 项已用于上表；`check PASS` 逻辑上蕴含 `--write` 幂等 written=0，见 `projection.py:448-453` changed=[] 分支，故未实际执行写操作）。

---

## 5 维度覆盖（硬门槛）

| 维度 | 结论 |
|---|---|
| 正确性 | PASS——字节相等复算、set-equal 合同、converged→promote 语义方向均实证成立；注册条目经工具 check 接受（exit 0） |
| 安全性 | PASS——路径均为仓库相对 POSIX 路径，无穿越/符号链接风险（`projection.py:71` `_safe_repo_path` 校验亦在）；无敏感数据 |
| 可维护性 | PASS——与 7a865b7 先例逐字段同型，declared_legacy 理由文本可审计；无重复机制 |
| 性能 | PASS——纯声明注册，无运行时热路径变更 |
| 测试覆盖 | PASS——投影合同有 check 引擎 + legacy snapshot 看护 + 消费者 needle 断言三层面；fixture 面被 L9543 直接断言 |

## 结论

**APPROVED_WITH_NOTES / unresolved_blockers=0**（P0=0, P1=0, P2=0, P3=2）。变更可直接合并；P3-1/P3-2 作为记录项与后续候选，不需在本任务内处理。
