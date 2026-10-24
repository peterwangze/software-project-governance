# CODE R0 — FIX-462 pin 台账机写命令（独立审查）

- 审查人：Code Reviewer（独立，M7.4；只读命令 + 本报告文件，零代码修改/零 .governance 写入/零 git 变更）
- 对象：未提交实现 vs HEAD=1d9216e（`git diff HEAD` + 未跟踪 `infra/pin_ledger.py` 653 行）
- 日期：2026-10-24 · round R0
- 结论（机录锚点行）：

FIX-462: APPROVED_WITH_NOTES (unresolved_blockers=0)

## §1 写入器正确性（清单 1）— 通过
- AST 锚定：`_parse_ledger` 定位 `STATIC_PIN_EXEMPTIONS` Assign→Dict 节点；既有文件键在 List `end_lineno`（`]` 行）前插入，新文件键在 Dict 收尾前插入；re-anchor 为行内 col 区间替换数字字面量——无关字节不经手（构造即外科级）。
- 写前校验完备（五道，全在任何写入前）：rel 限 `infra/tests` 且 .py；line≥1；token 以 `_SEMVER_RE`（与扫描器同族 lookaround）实载该行；活扫描必须正命中该行（`hit_key` 含行号+尾随空格对齐消息面）；`_REASON_*` 名实在模块内定义（或 JSON 字面量理由）。重复条目先于一切判 idempotent_noop。
- 原子性：mkstemp 于台账同目录（同文件系统）→ 写候选 → py_compile → 影子 import 候选源跑真实 `scan_static_version_pins`（该行不再命中 + 无 stale）→ `os.replace` 换入；post-check 失败删临时文件拒收（盘上从未出现半成品），retryable 路径 `_restore` 幂等回写原文。
- 回滚真实可达：SMOKE2 实测错 token → `refused` exit 2，台账 SHA256 前后一致；幂等 SMOKE1 实测 `idempotent_noop` 零字节写入。
- exit 量表 0/2/3 与 governance_store `_emit` 同构。

## §2 面 6 与 amnesty 语义（清单 2）— 通过
- 姿态：结构违规（不可解析/条目畸形/键越界）=FAIL；无 provenance 新增行=WARN（status 保持 PASS、issues 携带 detail）——与 face 5 全 WARN 默认姿态对齐；台账缺席（已安装包 dev 面不存在）=SKIPPED 非 FAIL。
- DELIVERY_AMNESTY_ENTRIES 逐项点数=55 条，与活台账精确相等由 `test_amnesty_snapshot_matches_live_ledger_exactly`（frozenset 相等断言）钉扎；真树面 `test_real_tree_face_is_clean_amnesty_complete` PASS。
- 迁移脱离 amnesty 为数据驱动机制（新行∉冻结集→须 provenance 注释），非注释承诺；§1 幂等冒烟在真台账上零写入复核。

## §3 安全不变量（清单 3）— 通过
- version.py diff 恰 +10 纯注释（台账写入路径/手改报警/amnesty 语义说明），hook pin FAIL 路径（L77-104）零触碰。
- register 拒绝 `infra/tests` 之外的一切目标 → 无法豁免任何已发布产品面 pin；活命中前置校验防「先豁免后命中」的空转行。

## §4 合同链合规（清单 4）— 通过
- registry.py：`LOADER_WHITELIST`+`pin_ledger`（带先例注释）+ `_COMMANDS` 表 `("pins","pin_ledger.cmd_pins")` 按字母序插入。
- 双冻结键 107→108（test_registry.py / test_contract_matrix.py 注释链各含 FIX-462 条目）；R6 冷导入 209→210（import_set_sha256 同步轮换）。
- snapshots.json 机 regen 指纹：handler_count 104→105、keys+pins、write-guard faces 清单 +1 行面 6 描述。
- baseline：anchor_loc 28214→28275、generated.git_head=1d9216e（本票 HEAD）；test_archguard_ratchet 冻结字面量同步并带 DEC-320/324 先例引用。
- 引擎 +61/-0：六 hunk 实测 6+6+32+3+12+2=61（含 2 空行），与 R1 增量一致——**但 ratchet 注释的子分解（7+14+3+30=54）漏列 @25775 守卫接线 hunk(+3) 且各项有 ±2 粗糙**，净数正确且被测试钉扎，见 N1。

## §5 测试质量（清单 5）— 通过
- 五案 mini-root（真实 version.py 副本 + 合成 1.23.0 active 根）：register 成功（provenance 行恰在 tuple 上方+post_checks 全真）/拒绝原子性（read_bytes 前后相等）/幂等（快照字节相等）/re-anchor 漂移修复（造漂移→stale 出现→修复→扫描零发现→复跑 noop）/手改 WARN（删 provenance 行→恰 1 issue type=pin_ledger_unattributed）。
- 真树契约两案：面净 + amnesty 精确相等。断言全部基于真实扫描行为与字节比对，无自证。unittest 风格零 pytest 依赖（FIX-460 教训落实）。

## §6 独立复跑（清单 6）— 全绿
| 门 | 结果 |
|---|---|
| test_static_version_pins 全模块 | `Ran 32 tests ... OK`（25 旧 + 7 新） |
| test_registry / test_contract_matrix / test_archguard_ratchet | 三套件 OK |
| verify_workflow | `Verification Result: PASSED` exit 0，[FAIL] 计数=0 |
| governance-write-guard | PASS 0 issue——面 6 行在列（`pin 豁免台账（FIX-462…）— 0 issue(s)`） |
| `pins --help` | usage 双子命令 exit 0 |
| 真树冒烟 SMOKE1（既有行 register） | `idempotent_noop` exit 0，台账哈希不变 |
| 真树冒烟 SMOKE2（错 token） | `refused` exit 2（detail 精确），台账哈希不变 |

## §7 Notes（非阻塞，N1-N5）
- **N1** test_archguard_ratchet.py 注释的 +61 行归属子分解算术粗糙（漏列 +3 守卫接线 hunk；7/14/30 与实测 6/12/32 有 ±2 出入）。净数正确且被断言钉扎；建议随下次触及该文件的票顺带校正注释。
- **N2** verify_workflow.py 新增含 2 空行（计入 61）——无影响，备忘。
- **N3** `_PROVENANCE_RE`/semver 正则在 pin_ledger.py 与 version.py 各持一份（约定耦合）；影子扫描 post-check 使漂移自捕获，风险受控；0.100 可考虑单一来源。
- **N4** re-anchor 拒多行 tuple（带明确报错与 --token 消歧提示）——当前台账无多行条目，合理保守。
- **N5** A组 7 项 Windows-bash 族本地 FAIL 仍在（暂停 FIX-444/445 所有，CI Linux 权威）——存量披露，非本票面。

## §8 范围纪律
diff 面=声明 10 文件 + WIP 两文件（742/1+855/2 会话前指纹，numstat 复核未动）；未跟踪仅 `.codex-sandbox/` 与 `pin_ledger.py` 本体。审查全程只读+写本报告。
