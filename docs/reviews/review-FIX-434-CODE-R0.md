# Review: FIX-434 CODE R0 — 写侧旗标 `--install`/`--uninstall` 真实根拒绝注记补齐

- **任务**: FIX-434（FIX-433 R0/R1 P3 承接；plan-tracker L89）
- **审查者**: Code Reviewer（独立 R0；不修改产品代码）
- **日期**: 2026-10-06
- **审查对象**: 工作区未提交 diff（`git diff`：README.md + adapters/dsh/README.md，8 行修改 = 8+/8−）
- **结论**: `APPROVED_WITH_NOTES`
- **unresolved_blockers**: 0

## 1. 范围与方法

改动面（`git status` + `git diff` 独立核实）：恰 2 文件、8 处行内追加（每处 = 旧行改写为新行，全部为原句保留 + 守卫限定追加）：

| # | 位置 | 内容 |
|---|------|------|
| 1 | 根 README L108 | `--install` 行追加 `write_side_refusal: the real user root is refused with exit 2; only a redirected DSH_HOME (isolated env) is written` |
| 2 | 根 README L110 | `--uninstall` 行追加 `same write-side guard: the real user root is refused with exit 2 (redirected DSH_HOME only)` |
| 3 | 根 README L111 | 降级行改为 `--install under a redirected DSH_HOME (…refused with exit 2), or restart dsh and let ensurePreset() re-render` |
| 4 | 根 README L429 | 表格安装行追加 `写侧守卫同 --sync：对真实用户根必拒 exit 2，仅限显式重定向 DSH_HOME 的隔离环境` |
| 5 | 根 README L431 | 表格降级行追加 `同写侧守卫……或重启 dsh 由 ensurePreset() 重渲染` |
| 6 | 根 README L432 | 表格卸载行追加 `写侧守卫同 --sync：……仅限显式重定向 DSH_HOME 的隔离环境` |
| 7 | adapters/dsh/README.md L25 | `--install` 行追加 `写侧守卫：真实用户根必拒 exit 2（write_side_refusal），仅限显式重定向 DSH_HOME 的隔离环境` |
| 8 | 根 README L33 | Tier-1 表 dsh 行（Developer 中途发现即闭环追加）`write_side_refusal: …; only a redirected DSH_HOME (isolated env) is written` |

守卫事实源（代码级独立核实，不采信 Developer 自述）：
- `adapters/dsh/launch.py` L855-915 `write_side_refusal`：`$DSH_HOME` 未设 / 空白 / profile 不可解析 / 解析至（或包含）真实 DSH home 四形态一律返回拒绝理由。
- L1803-1809：`--install` 与 `--sync` 为同一 argparse 旗标（dest="install"）→ 三旗标两路径：install/sync L659 守卫、uninstall L783 守卫，均在任何写入前。
- L826 `SMOKE_EXIT_REFUSED = 2`；L917-922 `_refuse_write` 返回 2 → 「必拒 exit 2」属实。
- dry-run 预览先于守卫返回 0（install L640-652 / uninstall L763-777）→ 「--dry-run to preview」表述与代码一致。
- `lib/index.js` L416-420/L490：ensurePreset() 版本标记幂等——仅当 `current === version` 跳过，版本变化（含降级）即整体重渲染 → 降级行的 ensurePreset() 替代路径语义正确，且该宿主侧路径不经 launch.py 守卫，作为真实根合法替代路径呈现无误。

## 2. 逐维度结论

### 2.1 正确性 — PASS

8 处注记语义与守卫事实逐条一致：三旗标同拒（同一 `write_side_refusal`）、exit 2（SMOKE_EXIT_REFUSED）、仅显式重定向 DSH_HOME 可写；uninstall 行「same write-side guard」属实（同一函数）；降级行双路径（重定向下 `--install` / 重启 ensurePreset() 重渲染）均与代码行为吻合；dry-run 预览放行的既有表述不受影响。

### 2.2 完整性 — PASS

两文件 grep `--install|--uninstall|--sync` 全量枚举（根 32 命中 / adapters 6 命中）逐条核对：

- **已注记动作位**: 根 L108/L110/L111/L429/L431/L432/L33 + adapters L25（8 锚点全落位）。
- **紧邻注记覆盖位（Developer 判定成立）**:
  - 根 L82 `--install`（英文快速开始块）——L85 粗体注记距 3 行、同小节，显式点名三旗标 + exit 2 + `[REFUSED]` + 真实 home 形态枚举 + MUST 重定向 + dry-run 放行；L90 并示范重定向形态。覆盖充分。
  - 根 L409 `--install`（中文方式二块）——L419 引用块注记紧随代码块（同小节），同点名三旗标 + 拒绝面语义 + MUST 重定向。覆盖充分。
- **天然合规范位**: 根 L453（安全验证边界块）——L452 先行设置临时 `$env:DSH_HOME` 再执行 `--install`，本身就是隔离形态示范，无需注记（该位未出现在 Developer 的豁免清单中，见 F-3）。
- **dry-run 只读预览**: 根 L81/L405、adapters L26 — 按验收定义不算动作位。
- **散文/边界语义引用**: 根 L114/L434（Key boundary 卸载归属描述）、L399（方式一中卸载工具归属散文——其正句主指令是 `dsh plugin remove` + 手动删目录，`--uninstall` 为工具指名）、adapters L11/L32/L38（路径架构描述/「常用路径不需要」/括注）——均非可执行动作步骤，判定成立。
- **异工具旗标**: 根 L18/L193/L284/L287/L296 为 `web-console --install`，与 launch.py 无关。

无裸 live 动作位残留。

### 2.3 一致性 — PASS

- 英文面：L108/L33 与 FIX-433 L109 尾句「the real user root is refused with exit 2」同族同构；隔离限定用规定形态 `redirected DSH_HOME (isolated env)`。
- 中文面：L429/L432「写侧守卫同 `--sync`：对真实用户根必拒 `exit 2`，仅限显式重定向 `DSH_HOME` 的隔离环境」与 FIX-433 L430 及 adapters L44 逐族一致（「同 `--sync`」正确回指 FIX-433 注记）；adapters L25 与同文件 L44 措辞族一致。
- 无自相矛盾：降级行双路径（守卫限定 `--install` vs 宿主侧 ensurePreset()）为并列替代机制且注记明确区分，不构成「一处可用一处必拒」冲突。

### 2.4 无回归 / 纯粹性 — PASS

- diff 恰 2 文件、8 行修改，全部为原句保留 + 追加限定；唯一非纯追加点为 L111 将原括注 `(overwrites in place)` 从 `--install` 从句移至 ensurePreset() 从句——该移位是新限定的必然结果（原无限定 `--install (overwrites in place)` 正是被注记的裸动作缺陷本体），原语义信息无丢失。
- `git status` 确认 `.governance/**` 与全部豁免档案面（docs/architecture·release·requirements·marketplace、CHANGELOG）零触碰。

### 2.5 R5 措辞 — PASS（零违禁）

- 零新增违禁词：全部新文本为守卫拒绝语义描述（「真实用户根必拒」/「the real user root is refused」），无无限定语的「真实安装/真实环境/真机」操作宣称。
- 隔离措辞符合规定形态：中文 4 处「（仅限）显式重定向 `DSH_HOME` 的隔离环境」；英文 2 处 `redirected DSH_HOME (isolated env)`。L110 压缩变体 `(redirected DSH_HOME only)` 见 F-1。

### 2.6 独立复跑 — PASS（全部 exit 0）

| 验证 | 结果 | exit code |
|------|------|-----------|
| `verify_workflow.py check-agent-adapters` | `[OK] agent adapter contracts synchronized`（6 适配器 runtime-verified） | 0 |
| `verify_workflow.py check-cross-references` | 77 文件 / 733 引用，5 项全 PASS | 0 |
| `verify_workflow.py check-entry-bootstrap-sync` | `PASSED — entry bootstrap sections synchronized` | 0 |
| pytest 三 dsh 文件 | `301 passed, 102 subtests passed in 61.14s` | 0 |

pytest 文件组合独立定位：Developer 未点名文件，逐文件计数（contract 120 / boundary 136 / compat 126+99 subtests / adapter 55+3 subtests / doctor 92）推得声称口径 = **contract + compat + adapter**，按该组合复跑与声称「301 passed + 102 subtests」逐字一致。

## 3. 发现清单

| # | 级别 | 位置 | 发现 | 建议 |
|---|------|------|------|------|
| F-1 | P3 | 根 README L110 | 隔离限定用压缩变体 `(redirected DSH_HOME only)`，未带 `(isolated env)` 标记（其余英文锚点均为规定形态 `redirected DSH_HOME (isolated env)`）。语义等价、同族，不构成错误 | 未来文档任务顺手对齐即可，不单独派发 |
| F-2 | P3 | 根 README L399 | 方式一散文提及 `--uninstall` 作为手工副本卸载工具指名——边界语义散文、非步骤动作位，且 CLI 自身守卫机器强制、对称表卸载行已注记，判定不改动成立 | 如未来追求极致一致可加半句限定；无行动必要 |
| F-3 | P3 | Developer 验证报告 | 「pytest dsh 三文件」未点名文件名——不同三文件组合计数不同（如 contract+boundary+adapter = 311 passed + 3 subtests），单凭计数无法定位组合；本审查已推定并复现其口径 | 后续 evidence 建议写明具体文件名（流程卫生，非产品缺陷） |

- **P0**: 0
- **P1**: 0
- **P2**: 0
- **P3**: 3（F-1/F-2/F-3，均观察项，不要求修改）

## 4. 终裁

**RESULT: APPROVED_WITH_NOTES**
**UNRESOLVED_BLOCKERS: 0**

八锚点全部落位且语义与 `write_side_refusal` 代码事实一致；FIX-433 同族措辞达成；无裸动作位残留（含 L85/L419 紧邻覆盖判定成立、L453 天然合规）；diff 纯粹、档案面零触碰；R5 零违禁；四项验证独立复跑全绿且 pytest 计数与声称逐字一致。三条 P3 观察项不阻塞合并。
