# Rollback Plan — 0.95.0

- **日期**: 2026-10-05（准备态——tag 未打） · **回滚分类**: 可逆发布（**零新增数据面声明**——本版载荷无 `.governance` schema 变更、无迁移新增、无旗标新增；exploration 记录区块复用既有 evidence 载体按既有格式追加行；代码面=载荷 commit 可单独 revert + 版本面确定性再生回收）
- **回滚基线**: **tag `v0.94.0`@`6da8d04`**（candidate=4789f96 → release=6da8d04；taggerdate 2026-10-04 权威〔annotated 4d4da76——plan-tracker L206 实读〕）。

## 回滚区间锚定

**回滚区间 = `6da8d04..<发布tip 回填位>`**（回退点 = v0.94.0 tag peel transition）：

- 下界 `6da8d04` = v0.94.0 tag peel 实测（M-5b candidate_to_released transition 提交；ledger NATIVE_RELEASED 本地+remote 双 PASS——L206/EVD-1311）。
- 上界 = **M-5b transition 提交（发布 tip）= 回填位**（生成后实测回填——0.81.0 先例 F-04 终点纪律：终点=发布 tip，起草期不预编造）。
- 窗口计数（@起草时点）：**回填位**——已知锚：FIX-432 两 commit `9a28e4d`/`c68cbbd`（DEC-316 实录）；其余载荷 commit（FEAT-085/FEAT-086 产品面、AUDIT-157/158 docs 面）与 REL-099 组装/M-5a/M-5b 提交哈希待 Coordinator git log 实测回填（Release Agent Bash 禁止——m-0 报告 §7 清单第 10 项）。窗口构成预期：五票提交 + REL-099 组装提交（本批四件套+CHANGELOG）+ M-1 版本面提交（Developer）+ M-5a/M-5b 提交。

## 发布前回滚（任一门禁 FAIL）

fail-closed 阻断——修复后重跑门禁，不跳门（release-checklist 纪律）。候选态发现问题的回滚 = 丢弃候选提交（`git reset`）或修复追加，无外部影响；candidate manifest（M-5 才创建）随候选提交一并消失，无独立清理面。**受控整改优先于整体回滚**（REL-095/096/097/098 先例同构——含 REL-098 M-2 NO-GO 修复批先例）。

## 回滚序列（代码面与数据面分别明确——按序执行，禁跳步）

1. **序① 数据面（先行声明——本版零新增数据面动作）**：
   - 0.95.0 载荷**零 `.governance` schema 变更、零迁移新增**——git revert 不需要、也不会触发任何治理数据复原动作。
   - exploration 记录区块（M10.2 四字段：判定/理由/动作+资源引用/结果状态）**复用既有 evidence 载体**按既有行格式追加（FEAT-085/DEC-312(2) 设计即不建子系统）——revert 产品代码后新形态行停止产生，既有 evidence 行为治理事实不受 git revert 影响。
   - **`.governance/` 台账非 git 管理（gitignored，AUDIT-082 口径同根 CLAUDE.md）**：git revert 物理上不触及治理台账；数据面回退与代码面回退互独立，须分别决策、分别验证（write-guard 复跑对账）。
2. **序② 版本面（git 面）**：`git revert <REL-099 M-1 版本面提交>` + `release-projection --write` 再生（幂等再生——版本面收敛回 0.94.0 投影面；0.92/0.93/0.93.1/0.94.0 先例同构）+ `sync_entry_projection.py --write`（双根 entry 再生，repo root + e2e fixture 两调用；仓库根 CLAUDE.md 为 gitignored 工作树面，须单独再同步——AUDIT-082 口径）+ `check-projection-sync`/`check-version-consistency`/`check-entry-bootstrap-sync` 验证；引擎锚（REQUIRED_SNIPPETS 六针脚）与 hooks `@version`×4 随版本面提交 revert 一并回收；`project/CHANGELOG.md` 0.95.0 段随组装/M-1 提交 revert 回收。投影面为确定性再生，不存在手改漂移。**无 B2 豁免面**。
3. **序③ 载荷面（按需——五票 revert 序列，新→旧）**：全版本弃用场景下按依赖逆序单独 revert（DEC-260 纪律：rider 随主提交同序）：
   - `FIX-432`（commits `9a28e4d`/`c68cbbd`+回填位）→ `FEAT-086`（回填位）→ `FEAT-085`（回填位）→ `AUDIT-158`/`AUDIT-157`（docs/research 报告+治理入账面——回填位）。
   - **测试面回退随票携带**：各票测试与代码同票——禁单边还原（只回代码留测试=半回退混合态）。
   - **依赖链警告**：FEAT-086（前瞻验收+六平台 channels 物理化）依赖 FEAT-085（M10 协议唯一规范源+exploration schema）——单独回退 FEAT-085 而留 FEAT-086 会产生协议断链（manifest `exploration_channels` 声明无对应规范源），须按依赖逆序整组评估；FIX-432 的 manifest note 规范标记依赖 FEAT-086 的六 manifest 现状、quote_sync 守卫依赖 note 标记形态——revert 任一票后须复跑 `check-cross-references`/`check-manifest-consistency` 定向组验证。
   - **同文件多票警告**：`references/behavior-protocol.md` 承载 FEAT-085 M10 新节+FIX-432 称谓 sweep（M0 节注记）；六 platform adapter-manifest 承载 FEAT-086 channels+FIX-432 note 标记；`verify_workflow.py` 承载 FIX-432 quote_sync+L969 存在性锚——禁单票选择性还原，revert 须整组评估。
   - **AUDIT 票特殊面**：AUDIT-157/158 为分析票（docs/research 报告+`.governance` 入账）——报告文件可随 revert 回收，但治理记录（DEC-312/313、EVD-1312/1313）为 append-only 事实不可擦除；如仅回退产品行为面，AUDIT 票 docs 可选择保留（建议随整组回退保持窗口纯净，另行 DEC 记账）。
4. **ledger 处置（tag 已推场景）**：已 released transition 为 append-only 事实——**不重写历史 ledger**；`core/releases/0.95.0.json` 随版本面/发布 commit revert 一并回收（git 面）；remote ledger 状态与 git 现状的重新对齐经 `release-ledger --version 0.95.0 --remote origin` 复跑验证，差异如实披露并按 ADR-010 契约处置（不伪造 released 状态；UNKNOWN/BLOCKED 不包装为 PASS）。

## 发布后回滚（tag 已推）

1. **插件面（消费者）**: 用户侧 `/plugin update` 回退到 0.94.0（marketplace 历史版本可得）；本版无破坏性行为变更、无 schema/迁移面（checklist §A/§F）——回退无数据兼容风险；入口 bootstrap 版本戳经 FEAT-035 确认门自升级，回退后下次会话自回 0.94.0 面板。
2. **仓库面（维护者）——回滚三步序列**（=§回滚序列，按序执行）：Step 1 数据面决策（序①——零新增数据面，通常无动作）→ Step 2 git revert 链（序②版本面→序③载荷面按需+序④ ledger 处置）→ Step 3 投影再生验证（check-projection-sync/check-version-consistency/check-entry-bootstrap-sync + write-guard 复跑）。
3. **tag 误推**: 删 remote tag 重打——历史 tag 变更 MUST 有独立 DEC（release-checklist 纪律，缺 DEC 不创建/不改 tag）。
4. **发布后缺陷**: hotfix 0.95.1 路径——**不重写已发布 tag**（受控整改优先于整体回滚）。

## 验证方式（回滚完成判据）

1. `check-version-consistency` —— 13 处版本声明全部回到 0.94.0 一致（SKILL frontmatter/manifest.json/marketplace/4× plugin.json/4× hooks @version/双根 bootstrap 标记）。
2. `check-projection-sync` + `check-entry-bootstrap-sync` —— 投影与双根 entry 回 0.94.0 收敛。
3. **unittest 基线** —— `python -m unittest test_verify_workflow` 回 0.94.0 基线值（0.94.0 发布门实测口径——EVD-1311 M-2 末轮 exit 0；计数不预填，以 0.94.0 发布门记录为准）+ 全量 verify PASSED。
4. `check-governance` —— 回 0.94.0 基线面（1 issue〔28n 预存〕口径延续，无新增）。
5. write-guard 复跑对账（数据面与代码面分别验证声明）。

## 预计回滚时间

- **版本面回滚**（序①+序②+验证）：≤60 分钟——投影/entry 为确定性单命令再生，revert 面集中单一版本面提交（0.93.x/0.94.0 先例同构）。
- **含载荷面全量回滚**（+序③/序④+定向回归）：≤ 半个工作日——五票窗口+依赖链整组评估+定向组验证（check-cross-references/check-manifest-consistency/unittest）。
- 消费者面无感知窗口：插件回退经 marketplace 历史版本即时可得。

## 触发条件（回滚决策门）

- 发布后发现 **P0 缺陷**：M10 探索判断阻断正常任务流（应跳过任务被强制卡探索）/检查器误红阻断发布门且无法向前热修（hotfix 0.95.1 不可行时）。
- 版本一致性破裂无法向前收敛（投影再生后仍 FAIL）。
- 用户明示裁定回退（关键决策——AskUserQuestion 确认后执行）。
- 观察期信号（stage-release SKILL 口径）：发布后冒烟/门禁复跑异常且 30 分钟内无法定位根因 → 按 P0 路径升级决策。

## 数据兼容性

- `.governance/` 治理记录：零 schema 破坏性变更（exploration 区块按既有 evidence 载体格式追加——append-only，revert 后停止产生、既有行不受影响）。
- 消费者面（插件安装态）：无迁移、无旗标——回退 = `/plugin update`（0.94.0 历史可得）。
- e2e fixture：投影 writer 收敛面随版本面 revert+regen 一致回收。

## 边界声明（保守边界——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 先例口径延续）；回滚方案中「unittest 基线」「载荷 commit 序列」两项含回填位——起草期零预编造（Release Agent Bash 禁止，git/命令事实由 Coordinator 复跑回填）。
