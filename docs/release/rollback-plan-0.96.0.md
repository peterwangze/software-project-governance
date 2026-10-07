# Rollback Plan — 0.96.0

- **日期**: 2026-10-07（准备态——tag 未打） · **回滚分类**: 可逆发布（**零新增数据面声明**——本版载荷无 `.governance` schema 变更、无迁移新增、无旗标新增；治理卫生面（FIX-437）为 .governance 登记改形按既有格式追加；代码面=七票载荷 commit 可按依赖逆序 revert + 版本面确定性再生回收）
- **回滚基线**: **tag `v0.95.0`@`1ee500a`**（transition commit；taggerdate 2026-10-05 20:55:53 +0800 权威〔FIX-349〕——plan-tracker L204 实读）。

## 回滚区间锚定

**回滚区间 = `1ee500a..<发布tip 回填位>`**（回退点 = v0.95.0 tag peel transition）：

- 下界 `1ee500a` = v0.95.0 tag peel 实测（M-5b candidate_to_released transition 提交；ledger NATIVE_RELEASED 双 PASS——L204/REL-099）。
- 上界 = **M-5b transition 提交（发布 tip）= 回填位**（生成后实测回填——起草期不预编造）。
- 窗口构成（@起草时点 git log 实测）：`e1457a8`（FIX-435）/`185aa31`（FIX-434）/`111bbb9`（FIX-433）/`f1a47fd`（FIX-438）/`c442e07`（FIX-436）/`f884829`（FIX-439）/`1a56797`（FIX-440）/`36ff0be`（FIX-441）+ REL-100 组装提交（本批四件套+CHANGELOG）+ M-1 版本面提交（Developer）+ M-5a/M-5b 提交（回填位）。注意：FIX-433/434（0.95.0 发布后收尾票）亦在窗口内——全量回退场景须一并评估（建议只回退至 v0.95.0 功能面时保留）。当前分支 **ahead 8**（master...origin/master——M-7 统一推送前全部为本地提交，回退成本最低窗口）。

## 发布前回滚（任一门禁 FAIL）

fail-closed 阻断——修复后重跑门禁，不跳门（release-checklist 纪律）。候选态发现问题的回滚 = 丢弃候选提交（`git reset`）或修复追加，无外部影响（**本版 ahead 8 全部未推送——无远端回滚面**）；candidate manifest（M-5 才创建）随候选提交一并消失。**受控整改优先于整体回滚**（REL-095~098 先例同构——含 REL-098 M-2 NO-GO 修复批先例；M-2 披露面 GO 终审为授权整改路径非回滚触发）。

## 回滚序列（代码面与数据面分别明确——按序执行，禁跳步）

1. **序① 数据面（先行声明——本版零新增数据面动作）**：
   - 0.96.0 载荷**零 `.governance` schema 变更、零迁移新增**——git revert 不需要、也不会触发任何治理数据复原动作。
   - FIX-437 治理卫生面（Check 30c 豁免预登记/RISK-066 改形）为 `.governance` 登记行改形/追加——revert 产品代码后新形态登记停止产生，既有登记行为治理事实不受 git revert 影响。
   - **`.governance/` 台账非 git 管理（gitignored——AUDIT-082 口径同根 CLAUDE.md）**：git revert 物理上不触及治理台账；数据面与代码面回退互独立，须分别决策、分别验证（write-guard 复跑对账）。
2. **序② 版本面（git 面）**：`git revert <REL-100 M-1 版本面提交>` + `release-projection --write` 再生（幂等——版本面收敛回 0.95.0 投影面；0.92~0.95.0 先例同构）+ `sync_entry_projection.py --write`（双根 entry 再生 ×2 root；仓库根 CLAUDE.md 为 gitignored 工作树面须单独再同步——AUDIT-082 口径）+ `check-projection-sync`/`check-version-consistency`/`check-entry-bootstrap-sync` 验证；引擎锚（REQUIRED_SNIPPETS 六针脚）与 hooks `@version`×4 随版本面提交 revert 一并回收；STATIC_PIN_EXEMPTIONS 0.96.0 bump-time 登记行随 revert 回收；`project/CHANGELOG.md` 0.96.0 段随组装/M-1 提交 revert 回收。投影面为确定性再生，不存在手改漂移。**无 B2 豁免面**。
3. **序③ 载荷面（按需——七票 revert 序列，新→旧 + 依赖链纪律）**：全版本弃用场景下按依赖逆序单独 revert（DEC-260 纪律：rider 随主提交同序）：
   - `FIX-441`（`36ff0be`——rider）→ `FIX-440`（`1a56797`）→ `FIX-439`（`f884829`）→ `FIX-437`（治理面——无产品 commit，见序①）→ `FIX-436`（`c442e07`）→ `FIX-438`（`f1a47fd`）→ `FIX-435`（`e1457a8`）。
   - **测试面回退随票携带**：各票测试与代码同票——禁单边还原（半回退混合态）。
   - **依赖链警告**：FIX-441 re-anchor（27866）依赖 FIX-436 增量（c442e07）与 FIX-438 首跳（27792）——revert FIX-438/436 前须先 revert FIX-441 否则基线悬空；FIX-440 承接 FIX-439 R0 findings（CRLF 修复建立在 FIX-439 双读点之上）——revert FIX-439 前先 revert FIX-440；FIX-435 exclusions 回收与拆分同票不可拆。
   - **同文件多票警告**：`adapters/dsh/launch.py` 承载 FIX-439（段边界/守护/校验前置）+FIX-440（CRLF/dry-run）双票；`core/architecture-baseline.json` 承载 FIX-438/441 两跳 regen；`verify_workflow.py` 与 `test_archguard_ratchet` 冻结字面量（anchor 27866/FACTS_PRINT_TOTAL 1371）随基线票 revert 同步——禁单票选择性还原，revert 须整组评估并复跑 `archguard-ratchet`（回退后按回退态基线判定，若回退致 ratchet FAIL 属预期态以披露处理）。
   - **FIX-437 特殊面**：治理登记票（无产品 commit）——.governance 登记行为 append-only 事实不可擦除；如需回退其效果（Check 30c 豁免预登记/RISK-066 引用形），经 DEC 记账另行处置非 git revert。
4. **ledger 处置（tag 已推场景）**：已 released transition 为 append-only 事实——**不重写历史 ledger**；`core/releases/0.96.0.json` 随版本面/发布 commit revert 一并回收（git 面）；remote ledger 状态与 git 现状的重新对齐经 `release-ledger --version 0.96.0 --remote origin` 复跑验证，差异如实披露并按 ADR-010 契约处置（不伪造 released 状态；UNKNOWN/BLOCKED 不包装为 PASS）。

## 发布后回滚（tag 已推）

1. **插件面（消费者）**: 用户侧 `/plugin update` 回退到 0.95.0（marketplace 历史版本可得）；本版无破坏性行为变更、无 schema/迁移面（checklist §A/§F）——回退无数据兼容风险；入口 bootstrap 版本戳经 FEAT-035 确认门自升级，回退后下次会话自回 0.95.0 面板。
2. **仓库面（维护者）——回滚三步序列**（=§回滚序列，按序执行）：Step 1 数据面决策（序①——零新增数据面，通常无动作）→ Step 2 git revert 链（序②版本面→序③载荷面按需+序④ ledger 处置）→ Step 3 投影再生验证（check-projection-sync/check-version-consistency/check-entry-bootstrap-sync + write-guard 复跑）。
3. **tag 误推**: 删 remote tag 重打——历史 tag 变更 MUST 有独立 DEC（release-checklist 纪律，缺 DEC 不创建/不改 tag）。
4. **发布后缺陷**: hotfix 0.96.1 路径——**不重写已发布 tag**（受控整改优先于整体回滚）。

## 验证方式（回滚完成判据）

1. `check-version-consistency` —— 13 处版本声明全部回到 0.95.0 一致。
2. `check-projection-sync` + `check-entry-bootstrap-sync` —— 投影与双根 entry 回 0.95.0 收敛。
3. **unittest 基线** —— `python -m unittest test_verify_workflow` 回 0.95.0 基线值（0.95.0 发布门口径——REL-099 记录；计数不预填以发布门记录为准）+ 全量 verify PASSED。
4. `check-governance` —— 回 0.95.0 基线面（无新增）。
5. `archguard-ratchet` —— 回退态基线判定（若载荷面整组回退，基线回 27352 前态并以 DEC 披露；仅版本面回退则 27866 维持 PASS）。
6. `.git/hooks/` 三 hook 实例核验 —— 版本面回退后 hooks `@version` 回 0.95.0；若 hook 实例缺失/损坏按 §B1 命令重装（prepare-commit-msg 经用户授权安装先例 EVD-1322；28q 守卫在位）。
7. write-guard 复跑对账（数据面与代码面分别验证声明）。

## 预计回滚时间

- **版本面回滚**（序①+序②+验证）：≤60 分钟——投影/entry 为确定性单命令再生，revert 面集中单一版本面提交（先例同构）。
- **含载荷面全量回滚**（+序③/序④+定向回归）：≤ 半个工作日——七票窗口+依赖链整组评估+定向组验证（archguard-ratchet/unittest/check-manifest-consistency）。
- 消费者面无感知窗口：插件回退经 marketplace 历史版本即时可得。
- **本版特有成本优势**：M-7 前全部提交为本地（ahead 8 未推送）——发布前回滚免远端操作。

## 触发条件（回滚决策门）

- 发布后发现 **P0 缺陷**：bootstrap 段边界守护误拒合法宿主形态（AGENTS.md 正常结构被 exit 1 拦截）/evidence-append 误拒合法行/checker 误红阻断发布门且无法向前热修（hotfix 0.96.1 不可行时）。
- 版本一致性破裂无法向前收敛（投影再生后仍 FAIL）。
- 用户明示裁定回退（关键决策——AskUserQuestion 确认后执行）。
- 观察期信号（stage-release SKILL 口径）：发布后冒烟/门禁复跑异常且 30 分钟内无法定位根因 → 按 P0 路径升级决策。

## 数据兼容性

- `.governance/` 治理记录：零 schema 破坏性变更（FIX-437 登记改形按既有格式——append-only，revert 后停止产生、既有行不受影响）。
- 消费者面（插件安装态）：无迁移、无旗标——回退 = `/plugin update`（0.95.0 历史可得）。
- e2e fixture：投影 writer 收敛面随版本面 revert+regen 一致回收。
- 外部宿主（DSH 装机 preset）：bootstrap 守卫变化仅影响写入路径行为——已注入宿主文件不受回退影响（无反向迁移需求）。

## 边界声明（保守边界——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 先例口径延续）；回滚方案中「发布 tip/transition 哈希」「unittest 回退基线计数」含回填位——起草期零预编造（git/命令事实由 Coordinator 复跑回填）。
