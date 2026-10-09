# Rollback Plan — 0.97.0

- **日期**: 2026-10-09（准备态——tag 未打） · **回滚分类**: 可逆发布（**零新增数据面声明**——本版载荷无 `.governance` schema 变更、无迁移新增、无旗标新增；DEC-329 风险改形为 .governance 状态列改形按既有格式；代码面=四票载荷 commit 可按依赖逆序 revert + 版本面确定性再生回收）
- **回滚基线**: **tag `v0.96.0`@`325289f`**（transition commit；taggerdate 2026-10-07 16:29:10 +0800 权威〔FIX-349〕——plan-tracker 版本路线图实读）。

## 回滚区间锚定

**回滚区间 = `325289f..<发布tip 回填位>`**（回退点 = v0.96.0 tag peel transition）：

- 下界 `325289f` = v0.96.0 tag peel 实测（M-5b candidate_to_released transition 提交；ledger NATIVE_RELEASED 双 PASS——REL-100）。
- 上界 = **M-5b transition 提交（发布 tip）= `<M-6b 回填位>`**（tag v0.97.0 将指向此 commit；taggerdate M-7 权威）。
- 窗口构成（@起草时点 git log 实测）：`1b3636f`（M-8 回填）/`c9dc84f`+`a4c73b8`+`af8fba0`（FEAT-089 链）/`aca1fe4`（FEAT-090/091/092 批）/`602dc79`（批收口修复）+ REL-101 组装提交（三件套+m-0 报告+CHANGELOG 0.97.0 段）+ M-1 版本面提交（23 文件）+ M-5a/M-5b 提交（回填位）。当前分支 **ahead 5**（master...origin/master——M-7 统一推送前全部为本地提交，回退成本最低窗口）。

## 发布前回滚（任一门禁 FAIL）

fail-closed 阻断——修复后重跑门禁，不跳门（release-checklist 纪律）。候选态发现问题的回滚 = 丢弃候选提交（`git reset`）或修复追加，无外部影响（**本版 ahead 全部未推送——无远端回滚面**）；candidate manifest（M-5 才创建）随候选提交一并消失。**受控整改优先于整体回滚**（REL-095~098 先例同构）。

## 回滚序列（代码面与数据面分别明确——按序执行，禁跳步）

1. **序① 数据面（先行声明——本版零新增数据面动作）**：
   - 0.97.0 载荷**零 `.governance` schema 变更、零迁移新增**——git revert 不需要、也不会触发任何治理数据复原动作。
   - DEC-329 风险改形（RISK-039/050/066 状态列）为 `.governance` 登记行改形——revert 产品代码后新形态登记停止产生，既有登记行为治理事实不受 git revert 影响；如需回退改形效果本身，回退三行状态为「打开」并接受 2 stale WARN 基线（DEC-329 回退语义支）。
   - **`.governance/` 台账非 git 管理（gitignored）**：git revert 物理上不触及治理台账；数据面与代码面回退互独立，须分别决策、分别验证（write-guard 复跑对账）。
2. **序② 版本面（git 面）**：`git revert <REL-101 M-1 版本面提交>` + `release-projection --write` 再生（幂等——版本面收敛回 0.96.0 投影面）+ `sync_entry_projection.py --write`（双根 entry 再生；仓库根 CLAUDE.md 为 gitignored 工作树面须单独再同步）+ `check-projection-sync`/`check-version-consistency`/`check-entry-bootstrap-sync` 验证；引擎锚（REQUIRED_SNIPPETS 六针脚）与 hooks `@version`×4 随版本面提交 revert 一并回收；`project/CHANGELOG.md` 0.97.0 段随组装/M-1 提交 revert 回收。投影面为确定性再生，不存在手改漂移。**无 B2 豁免面**。
3. **序③ 载荷面（按需——四票 revert 序列，新→旧 + 依赖链纪律）**：全版本弃用场景下按依赖逆序单独 revert：
   - `602dc79`（批收口修复——依赖 aca1fe4 文本）→ `aca1fe4`（FEAT-090/091/092 批——**单 commit 承载三票+测试，整组 revert**）→ `af8fba0`（FEAT-089 治理面机录）→ `a4c73b8`（FEAT-089 rider）→ `c9dc84f`（FEAT-089 主体）。
   - **测试面回退随票携带**：各票测试与代码同票——禁单边还原（半回退混合态）。
   - **依赖链警告**：602dc79 是 aca1fe4 内文本的路径修复——revert aca1fe4 前先 revert 602dc79；FEAT-089 的 rider（a4c73b8，anchor 27895）依赖主体（c9dc84f）增量且后续批再锚至 27934——revert 批 commit 后基线悬空属预期，复跑 `archguard-ratchet` 按回退态判定并以 DEC 披露。
   - **同文件多票警告**：`verify_workflow.py` 承载 FEAT-089（30c 执法常量）+FEAT-091（review-record 参数）+FEAT-092（--budget）三票；`behavior-protocol.md`/`SKILL.md` 承载 FEAT-090+091 双票；冻结字面量（anchor 27934/FACTS_PRINT_TOTAL 1376）随基线票 revert 同步——禁单票选择性还原，revert 须整组评估。
   - **30c 执法回退特殊面**：PROVENANCE_FAIL_ESCALATION_VERSION="0.97.0" 硬编码（review_domain.py:3188）随 FEAT-089 revert 回收——执法自动回 WARN 基线（单向棘轮在 git 面的可逆性=版本回退，与 feature-flags-0.97.0.md §Kill Switch 同口径）。
4. **ledger 处置（tag 已推场景）**：已 released transition 为 append-only 事实——**不重写历史 ledger**；`core/releases/0.97.0.json` 随版本面/发布 commit revert 一并回收（git 面）；remote ledger 状态与 git 现状的重新对齐经 `release-ledger --version 0.97.0 --remote origin` 复跑验证，差异如实披露并按 ADR-010 契约处置（不伪造 released 状态）。

## 发布后回滚（tag 已推）

1. **插件面（消费者）**: 用户侧 `/plugin update` 回退到 0.96.0（marketplace 历史版本可得）；本版无破坏性行为变更、无 schema/迁移面（checklist §A/§F）——回退无数据兼容风险；入口 bootstrap 版本戳经 FEAT-035 确认门自升级，回退后下次会话自回 0.96.0 面板（契约 7~9 注入随之消失——行为回退语义）。
2. **仓库面（维护者）——回滚三步序列**（=§回滚序列，按序执行）：Step 1 数据面决策（序①）→ Step 2 git revert 链（序②版本面→序③载荷面按需+序④ ledger 处置）→ Step 3 投影再生验证（check-projection-sync/check-version-consistency/check-entry-bootstrap-sync + write-guard 复跑）。
3. **tag 误推**: 删 remote tag 重打——历史 tag 变更 MUST 有独立 DEC（release-checklist 纪律，缺 DEC 不创建/不改 tag）。
4. **发布后缺陷**: hotfix 0.97.1 路径——**不重写已发布 tag**（受控整改优先于整体回滚）。

## 验证方式（回滚完成判据）

1. `check-version-consistency` —— 13 处版本声明全部回到 0.96.0 一致。
2. `check-projection-sync` + `check-entry-bootstrap-sync` —— 投影与双根 entry 回 0.96.0 收敛。
3. **全量测试基线** —— `python -m pytest skills/software-project-governance/infra/tests/ -q` 回 0.96.0 基线值（4757P/1S 口径——EVD-1351；若 M0Fixture pin 随批 revert 则以 0.96.0 终态基线为准并以 DEC 披露）。
4. `check-governance` —— 回 0.96.0 基线面（无新增；RISK 改形是否回退独立决策——DEC-329）。
5. `archguard-ratchet` —— 回退态基线判定（仅版本面回退则 27934 维持 PASS；载荷面整组回退则按 DEC 披露回退态）。
6. `.git/hooks/` 四 hook 实例核验 —— 版本面回退后 hooks `@version` 回 0.96.0。
7. write-guard 复跑对账（数据面与代码面分别验证声明）。

## 预计回滚时间

版本面回退 ≈15 分钟（含投影再生与三面验证）；载荷面整组回退 ≈45~60 分钟（含依赖序评估+archguard 回退态判定+全量复跑）。

## 触发条件（何时启动回滚评估）

- M-2/M-4/M-5 任一门禁 FAIL 且无法受控整改（fail-closed 阻断超时）。
- 发布后 P0 缺陷（宿主会话无法 bootstrap/数据损坏面）且无 hotfix 快速路径。
- 30c 执法激活在宿主侧产生不可接受的大面积误伤（豁免清单载体失效场景——DEC-146 升级路径的保守退出）。

## 数据兼容性

无迁移面（序①零声明）——`.governance` 既有台账在 0.96.0↔0.97.0 双向兼容（read 兼容；DEC-329 状态形态为合法词汇两版解析一致——「打开（登记观察…）」前缀口径 FIX-397④）。

## 边界声明

本计划覆盖 git 面/插件面/治理台账面的回退序列；不声明 marketplace 历史版本的永久可得性（平台侧策略外控）；tag 变更须独立 DEC；ledger 为 append-only 不重写。保守口径（REL-021 token 全量）：不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 先例口径延续）。
