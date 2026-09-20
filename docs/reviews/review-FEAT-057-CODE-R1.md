# Review FEAT-057 · CODE · R1 —— 定向复审（对照 R0 §8 指引，prev = review-FEAT-057-CODE-R0.md）

> 审查人: Code Reviewer Agent（同 R0 Reviewer，独立只读）· 轮次: **R1** · 日期: 2026-09-20
> 前轮引用: review-FEAT-057-CODE-R0.md（NEEDS_CHANGE / P0=0 · P1=1 · P2=1 · P3=6 / unresolved_blockers=1）
> 本轮审查对象（R0 基础上的增量）: `infra/closure_chain.py`（+1 hunk @:1325 方案 c 互斥分支，全文件 7 hunks 其余 6 处与 R0 逐字一致）+ `infra/hooks/post-commit`（+12 行 WARN-gated 计数行）+ `infra/tests/test_closure_chain.py`（+3 恢复腿测试）+ `infra/tests/test_hooks.py`（+静态钉 +双态行为测试 +stub UTF-8 姿态）+ `infra/tests/test_triage_write_guard.py`（+P3-1/P3-4 两钉）

---

## 1. 总结论

## **APPROVED_WITH_NOTES**（P0=0 · P1=0 · P2=0 · P3=1 · **unresolved_blockers=0**）

硬门槛全过：5 维度逐项有结论（§3）· AI 专项 5 项全过（§5）· R0 findings 逐条闭环比对（§2）。按 code-review skill 关闭规则（P0=0 且 P1=0 → 可合并），P3×1 为文档级建议，不阻塞合并。独立复验 6/6 通过（§4），真实 `.governance` 全程零写入（state 文件 mtime 保持 2026-09-20 12:09:45，`git status -- .governance` 干净）。

---

## 2. R0 findings 逐条闭环比对（复审本质 = 验证修复）

| R0 项 | 状态 | 事实依据 |
|-------|------|---------|
| **P1-1** CLI 步 UNKNOWN 未落地腿死路 + 建议补救命令崩溃 | **已修复**（方案 c） | 互斥双腿结构（closure_chain.py:1330-1350）：`unknown && kind==cli && 无 world_check` → 步探针（已先行运行）为世界核验，未命中 = 效果不在世界 → fall-through 重执行（写器 effect-based replay/状态级 CAS 兜底 = 修复前超时行为等价）；**有声明 world_check 的 cli 步与 external 步走原 elif 分支，语义零变化**（elif 体与 R0 逐字一致）。三恢复腿测试钉住：not-landed bare resume → ready + started 恰 2；landed bare resume → reconciled + started 恰 1；旧崩溃 remediation（`--world-check` on 未声明步）→ 无 schema_violation + ready。**活体复现（Reviewer 本机，R0 §4-6 同型夹具）**：run1 超时 → awaiting-world-check exit 2；run2 裸 resume → **exit 0 / ready / completed / 效果落地**；run3 `--world-check` → **exit 0 / ready / schema_violation 消失**。R0 死路与崩溃双腿均闭合 |
| **P2-1** hook 丢弃 WARN 输出 + 消费窗口不可见 | **已处置（可见性腿；窗口消费显式留 0.87）** | post-commit:270-279 WARN-gated 计数行：sed 提取 `Result: PASS — 0 FAIL issue(s), N WARN(s)` → N>0 才输出 `⚠️ GOVERNANCE: write-guard: N WARN(s) —— run governance-write-guard for details`；零 WARN 无行（行为测试断言缺席）。hook 注释显式登记「the guard run here also consumes the reconciliation window, so this line is the only trace」——R0 §7 边缘 8 的 0.87 约束（BLOCK 不得沿用 WARN-once-then-absorb）已在 hook 注释与 R0 报告双登记。双态行为测试（pass 静默 / warn 呈现计数）+ 静态钉（`-gt 0` WARN-gated）实跑通过；stub 增加 `sys.stdout.reconfigure(utf-8)` 对齐真实 CLI 姿态（修复期披露①——Windows 管道 stdout 默认 GBK 会致 em-dash Result 行不匹配，如实披露） |
| **P3-1** ops 中部插行语义无钉 | **已修复** | `test_ops_ledger_midline_insert_pins_displacement_semantics`：裸行插于 receipt 前 → 恰 1 WARN 锚定键 "1"/行 1；被位移原 receipt（键 2）凭证仍命中零误报——与 R0 §7 边缘 5 分析逐点对应 |
| **P3-4** unwritable 路径无测试 | **已修复** | `test_state_unwritable_disclosed_not_crash`：monkeypatch `Path.write_text` 抛 OSError → `row_family_state_unwritable` WARN 披露 + face 恒 PASS 不崩溃 + 基线文件字节原样保留 |
| P3-2（face5 非 UTF-8 分歧姿态无测试）/ P3-3（凭证子串假阴，BT-8 边界内）/ P3-5（ratchet 弱钉）/ P3-6（申报行数口径） | 未处置（可遗留） | 均为 R0 建议/讨论级，按 R0 §8 指引遗留登记，不阻塞；随 0.87 面或后续候选处置 |
| 新引入检查 | **1 处 P3 文档漂移** | 见 §6 R1-P3-1 |

## 3. 五维度审查结论（增量面）

| 维度 | 结论 | 要点 |
|------|------|------|
| 正确性 | ✅ | 互斥分支穷尽三种组合（cli 无声明重执行 / cli 有声明+external 原 gate / 非 unknown 直行）；重执行恰一次由 counter 夹具与 started 计数双重钉住；live 复现双腿达 ready |
| 安全性 | ✅ | 方案 c 不放行任何外部副作用面——CLI 探针为只读世界查询；写器幂等（确定性 per-step op-id / CAS）承载重执行安全；「结果不明不盲目重跑」的 round-2 目的由探针未命中=「已知不在世界」保持 |
| 可维护性 | ✅ | 分支注释完整记载 R0 P1-1 死路动机与恢复语义；测试脚本常量化（LANDED/NOTLANDED）+ docstring 引用前轮报告 |
| 性能 | ✅ | 零新增热路径；hook sed 单行提取 |
| 测试覆盖 | ✅ | 三恢复腿 + hook 双态 + 静态钉 + P3 两钉全部实跑（115 passed + 34 subtests）；红史申报（裸 halt 红/schema_violation 红）与 R0 §4-6 实证形状逐字吻合，标 claimed（绿态已钉，红史不可事后重现） |

## 4. 独立复验（6/6 通过——Reviewer 本机实跑）

| # | 项目 | 命令/方法 | 结果 |
|---|------|----------|------|
| 1 | 三套件实跑 | `pytest test_triage_write_guard.py test_closure_chain.py test_hooks.py -q` | **115 passed + 34 subtests in 42.65s**（47+35+33 与申报精确吻合） |
| 2 | verify + archguard | `verify_workflow.py verify` / `archguard_ratchet.py` | **双 exit 0**——R1~R7 零漂移申报证实（锚 25291/R4 1306 不变） |
| 3 | 契约矩阵零漂移 | `pytest test_contract_matrix.py -q` | **27 passed**（引擎↔snapshots 双提取一致） |
| 4 | P1-1 双腿活体复现 | R0 §4-6 同型 stateful-writer 夹具三连 | run1 awaiting-world-check/exit 2；**run2 裸 resume → ready/exit 0/效果落地**；**run3 `--world-check` → ready/exit 0/无 schema_violation** |
| 5 | hook 行为双态 | test_hooks 行为测试（真实 bash 段执行 + stub 双态） | 零 WARN PASS 无计数行 / WARN 态呈现 `2 WARN(s)` 计数行，均 set -e 存活 + marker 落盘 |
| 6 | 真实 .governance 完整性 | state 文件 mtime/长度 + `git status -- .governance` | **12:09:45 / 101,521 B 不变；零未提交变更**——测试零真实写入与 Reviewer 零写入双证实 |

## 5. AI 代码专项（增量面，5 项全过）

mock 残留 ✅（仅夹具隔离 + `Path.write_text` OSError 模拟，声明式用途）· 硬编码返回 ✅ 零（断言对真实 payload/文件/退出码）· 幻觉 API ✅ 零（新分支仅用既有符号）· 未实现 TODO ✅ 零 · 过度实现 ✅ 无（修复范围=死路腿本身，窗口语义未提前实现 0.87 姿态）

## 6. Findings

### P0 / P1 / P2 ——无

### P3（讨论/建议）

- **R1-P3-1 TOOLS.md TOOL-057「锁外披露先例」句与修复后 hook 行为矛盾（文档漂移）** · `infra/TOOLS.md` TOOL-057 条目
  事实：该句仍写「hook 面板对 WARN 数零呈现差异（WARN 只进 guard 输出行，不翻 hook 面板 PASS 结论）」；修复后 hook 面板**会**呈现 WARN 计数行（post-commit:276-279，行为测试钉住）。一句修正即可（如改为「hook 面板以 ⚠️ 计数行呈现 WARN 数，不改 PASS 结论、不翻退出码」）。属本次修复引入的描述滞后，不阻塞；建议随本批收尾顺手改或登记候选。

## 7. 遗留登记清单（随版本推进，不阻塞）

1. R0 P3-2：face 5 非 UTF-8 WARN+skip 分歧姿态负例测试。
2. R0 P3-3：凭证判据 0.87 BLOCK 升级时改「标记 + op-id 在 ops 台账 join」判据（BT-8 边界声明维持）。
3. R0 P3-5：ratchet 锚钉收紧为精确/区间断言。
4. R0 P3-6：申报行数口径标注（keys vs instances）。
5. R1-P3-1：TOOLS.md TOOL-057 hook WARN 句修正。
6. 0.87 BLOCK 升级设计约束（双处登记）：不得沿用 WARN-once-then-absorb 窗口语义；hook 窗口消费权/台账化在升级方案内显式处置。

## 8. 结语

R0 唯一阻塞项 P1-1 以方案 (c) 精确落地：互斥分支保住 external 步与有声明 cli 步的原 gate 语义，标准链无声明步的未落地腿经裸 resume 链内恢复（写器 replay 兜底），旧补救命令不再崩溃；三恢复腿测试 + Reviewer 活体双腿复现双重证实。P2-1 可见性腿落地、窗口消费义务显式移交 0.87。**批 2.3 上线路由（WARN 姿态）+ FEAT-056 P2-1/P3①④⑥ 承接达到合并标准（APPROVED_WITH_NOTES/0）。**

---
*审查依据: skills/code-review/SKILL.md + agents/code-reviewer.md · 复审协议：逐条比对前轮 findings（已修复/未修复/新引入）+ 前轮报告引用 · 事实依据红线遵守：每条结论可回溯至文件行号/命令输出/测试结果 · Reviewer 零代码修改、零 .governance 写入*
