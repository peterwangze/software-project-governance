# FEAT-083 CODE REVIEW R0 — 结构化返回

- **Reviewer**: Code Reviewer（subagent `9cb4e4d2`，只读审查，零文件修改）
- **Task**: FEAT-083（round 0）｜ **审查对象**: docs/reviews/FEAT-083-R0.diff 全 929 行逐行 + 6 文件工作树现状交叉核验 + F-P3 定义原文（docs/reviews/review-FEAT-082-CODE-R0.md §五/§六）+ DEC-302/RISK-063/TRIAGE 票面核验
- **日期**: 2026-10-03

**完成状态**: 完成
**审查结论**: **APPROVED_WITH_NOTES**（unresolved_blockers=0）
**P0 计数**: 0 ｜ P1: 0 ｜ P2: 0 ｜ P3: 4（全非阻塞备注）

## 硬门槛自检（全过）

1. **diff 逐行**: ✅ 929 行全读（provenance_domain +222、verify_workflow 薄委托、bootstrap_aggregate 镜像回收、两测试文件、baseline 2 字段）
2. **薄委托正确性**: ✅ 签名逐字保留 `def _collect_session_closure_events(governance_dir=None, today=None):`（vw:7339）；委托导入为函数局部（vw:7354）——verify_workflow 模块级导入面零变化，R6 冷导入冻结面不受触碰；GOVERNANCE_DIR 解析时点语义一致（旧 `Path(governance_dir) if governance_dir else GOVERNANCE_DIR` vs 新 `governance_dir if governance_dir else GOVERNANCE_DIR` + 叶内 `Path()` 包裹——调用时解析、falsy 判定、Path 等价性全同）；Check 42 无参调用（vw:17553）与引擎侧 8 个测试调用点（位置/关键字形态）全兼容
3. **单源断言真实性**: ✅ `test_mirror_is_fully_retired`（test:1130-1156）钉 6 个退役符号不在 ba 源 + 2 个不在 vw 源 + `pd.RISK_TERMINAL_WORDS == ("关闭","收窄","升级")` + `pd.CLOSURE_LEDGER_FILENAME == vw._DEFERRED_LEDGER_FILENAME`。**`_DEFERRED_LEDGER_FILENAME` 残留口径裁决：诚实**——grep 证实其在引擎侧仅剩写侧用途（vw:23970 定义、24758 write-guard 写路径、17586 展示），是存储契约字面量而非第二采集实现，且被测试钉相等；R6 冻结面下保留写侧别名是最小侵入的合理工程取舍。源级钉子为按名钉（对改名非绝对），但由 7-fixture 接口等价测试背书，守护充分
4. **F-P3-2a 跨平台稳定性声称**: ✅ 成立——`write_bytes(b"\xff\xfe not utf8")` + `read_text(encoding="utf-8")` 在任何平台/CPython 确定性抛 UnicodeDecodeError（\xff 永非合法 UTF-8 起始字节），无需权限技巧，优于原建议的注入式构造；两臂均同时断言 direct == via_engine（失败态下等价性仍成立）
5. **伴随扩面**: ✅ baseline diff 恰只 git_head + anchor_loc 两字段（官方 --regen 产物形态）；**anchor_loc 27352 与 verify_workflow.py 实际物理行数（27,352）精确吻合（本 Reviewer 机核）**，且 −137 == 引擎 hunk 净变化（161−24）——regen 真实性实证；ratchet 字面量同步（27352）+ rider 注释归因自洽（−155 移出 +18 保留 = −137）

## 验收标准逐项

① **双端单源调用**: ✅ 引擎（vw:7354-7356 薄委托）与 bootstrap（ba:644-654）同调 `checks.provenance_domain.collect_session_closure_events`；6 个镜像符号 grep 全仓零残留（仅测试钉子与历史文档提及）
② **差分转接口等价**: ✅ SessionClosureSingleSourceTests 5 测试：7-fixture 接口等价 + 源级单源钉 + 两 read-failure 臂 + face≡Check42 判定同核；净 +3 测试与 55→58 及全量 4659→4662 的 +3 声称结构吻合
③ **F-P3-1/2/3 收口**（对照 review-FEAT-082-CODE-R0 §五 L120-122 原文逐项核实）:
- F-P3-1 ✅ `skip["skip_kind"] == SKIP_ORCHESTRATION_FALLBACK`（ba:648-651 导入、676 判等）——与 Check 42 自身 `_SKIP_FALLBACK_42` 导入（vw:17550）同口径
- F-P3-2a ✅ 两 read-failure 臂补齐（真实失败构造）；F-P3-2b ✅ behavior 平键集升级为恰 8 键集合相等断言（= DEC-302 先例性质的机器强制化）
- F-P3-3 ✅ `_clip(window_note, 160)`——`_clip` 为字符级截断（ba:160-164），完整降级注记约 111 字符 < 160，测试断言全文 ADR 锚「ADR-021 §3.2.3 / §2.4 L4」在
④ **全量回归零新失败**: Developer 声称 4662P/0F/1S（基线 4659P）——**作声称对待**（Reviewer 无 Bash 不重跑），结构交叉核对一致（+3 恰为票内净新增）

## 5 维度结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | ✅ 通过 | 采集核逐行比对为引擎 canonical 原样迁移；四项披露差异逐一验证无害：默认值留薄委托（叶保持 engine-global-free）、splitlines 统一=引擎口径（cell.strip 后 CRLF 等价；\u2028 边缘差异以引擎为准已披露）、.format≡f-string 同输出、控制流取简语义全同（anomaly 优先级 ledger>row_read 保持；window note 文本逐字节同） |
| 安全性 | ✅ 通过 | 无新输入面/注入面/密钥；只读采集 + fail-closed 披露保持（缺台账=真空、不可读/坏行=anomaly、永不静默零——CR-R1-2） |
| 可维护性 | ✅ 通过（带 P3） | ~150 行漂移面消除（RISK-063 收敛路径落地）；R2 引擎无关边界保持（checks 叶零引擎导入）；R6 冷导入面两端零变化；1 处 docstring 计数陈旧（P3-1） |
| 性能 | ✅ 通过 | 算法/复杂度不变；冷导入面不变（双端函数局部导入）；无新循环 |
| 测试覆盖 | ✅ 通过 | 接口等价（7 fixture）+ 单源钉 + 两失败臂 + face≡Check42 + F-P3-2b/2b/3 钉子；旧差分覆盖面经 _VARIANTS 全继承 |

## AI 专项 5 项

1. **mock 残留: 无**——新测试全真文件/真函数/真引擎导入（`_import_engine`）；文件头 `unittest.mock` 导入为既有他用
2. **硬编码返回值: 无违规**——2 常量为存储契约/词表契约且被测试钉值（合法钉子形态）
3. **幻觉 API: 无**——逐一实存复核：SKIP_ORCHESTRATION_FALLBACK（lgp:119）、parse_ledger_line/deferred_events_from_entries（lgp `__all__`）、classify_observation_face、session_closure_rate、collect_session_closure_events、Check42DeferredSignalTests（tvw:20750）、_DEFERRED_LEDGER_FILENAME（vw:23970）
4. **未实现 TODO: 无**——diff 内零 TODO/FIXME/占位 pass
5. **过度实现: 无**——变更恰为提取 + 3 项 F-P3 + 既定伴随 regen，无票外多余面

## 设计一致性比对

- **review-FEAT-082-CODE-R0 §6.3**: ✅ 按建议落地（checks/ 纯叶 + 双端导入 + 差分降级）；实际采用更强形态（接口等价 + 源级钉 > 最低「存在性断言」）；叶放 provenance_domain 而非建议示例名 closure_collection.py——在 §6.3「如」的弹性内且纯度契约段诚实披露（P3 备注记录设计选择）
- **ADR-021 §3.2.2/§3.2.3**: ✅ 口径锚全保留（判定函数零改动；迁移 docstring 同 ADR 引用）
- **DEC-302**: ✅ FEAT-083 为指定承载票；嵌套子面先例经 F-P3-2b 升格为机器强制
- **FEAT-040 冻结面**: ✅ behavior 平键集不变（8=7+1），现由测试钉死
- **R6/R2 纪律**: ✅（见上）；伴随 regen 与 R7 baseline-stale 纪律及 FIX-410~421/FEAT-081/084 先例一致

## 发现列表（全 P3，非阻塞）

| # | 级别 | 位置 | 问题 | 建议 |
|---|---|---|---|---|
| 1 | P3 | checks/provenance_domain.py:14 | 模块 docstring「Three functions」在新增第 4 个 bullet（collect_session_closure_events）后计数陈旧 | 后续小修改「Four functions」或去计数（下个触达该文件的票顺带） |
| 2 | P3 | checks/loop_gate_processor.py:46-48 | docstring「All I/O (ledger file read/append) stays with the engine」在读取移入 shared leaf 后已过时（票外文件，本次不改正确） | 后续文档同步票顺带更新 |
| 3 | P3 | tests/test_bootstrap_aggregate.py:1217 | `expected_skip == "orchestration_fallback"` 用字符串字面量——与 F-P3-1 在生产码退役的口径同型；该行为 FEAT-082 既有保留行（非本票引入，F-P3-1 原定义范围是生产码） | 可选：后续改导入常量与生产码同口径 |
| 4 | P3 | 任务上下文统计口径 | Coordinator/Developer 汇总数字（vw −169/+14、ratchet +11、合计 +392/−365）与 diff hunk 实算（vw 净 −137=161−24、ratchet +10/−1）有小幅出入；机器相关一致性（anchor_loc==物理行数 27352、anchor Δ−137==引擎净变化）全部成立 | 无代码动作；后续报告引用统计以 git diff --stat 实测为准 |

**未验证事项声明（事实依据红线）**: 全部测试通过数字（58/58、4662P/0F/1S、verify/xref/manifest/archguard R1~R7、活体投影 4747B/8 键）为 Developer 自报，本 Reviewer 无 Bash 权限未独立重跑；已做结构交叉核对全部吻合（净 +3 测试数、anchor_loc==实际行数、baseline 2 字段形态、退役符号零残留）。

## 建议后续动作（Coordinator）

- 机录 review-record：verdict=APPROVED_WITH_NOTES、unresolved_blockers=0、round=0
- 4 条 P3 无需返工，可入遗留池（P3-1/P3-2 可合并为一个 doc-sync 微票；P3-3 可选；P3-4 无动作）
- RISK-063（镜像漂移）收敛路径已执行落地，可按其复评窗（2026-10-31）推进关闭
