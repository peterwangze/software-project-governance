# Rollback Plan — 0.94.0

- **日期**: 2026-10-03（准备态——tag 未打） · **回滚分类**: 可逆发布（**零新增数据面声明**——本版载荷无 `.governance` schema 变更、无迁移新增、无旗标新增；写侧台账为 0.88.0 FEAT-060 既有面，face-5 观测族按既有三键格式追加行；代码面=11 commit 可单独 revert + 版本面确定性再生回收）

## 回滚区间锚定

**回滚区间 = `0e277af..<发布tip 回填位>`**（回退点 = `v0.93.1` tag peel transition）：

- 下界 `0e277af` = v0.93.1 tag peel 实测（M-6/M-7 candidate_to_released transition 提交；taggerdate 2026-10-01 22:44:14 +0800 权威〔FIX-349，M-8b `84f8819` 回填口径〕）。
- 上界 = **M-5b transition 提交（发布 tip）= 回填位**（生成后实测回填——0.81.0 先例 F-04 终点纪律：终点=发布 tip，起草期不预编造）。
- 窗口计数（@起草时点 HEAD `af7cfbd` 实测，旧→新）：`4bfa1f5`（REL-097 M-5a——0.93.1 线收尾）→ `8f6a147`（REL-097 M-8a——0.93.1 线收尾）→ `84f8819`（REL-097 M-8b——0.93.1 线收尾）→ **本版载荷十一提交**：`2aa2377`（FEAT-081）→ `5de8548`（FEAT-082）→ `9a527cb`（FEAT-084 立项评估 memo——docs 件）→ `8568b1b`（FIX-421）→ `0377b78`（FEAT-084）→ `768021b`（FIX-422）→ `9018006`（FIX-423）→ `c00d70c`（FEAT-083）→ `3883407`（FIX-424）→ `b0075d8`（FIX-425）→ `af7cfbd`（FIX-426）；REL-098 组装提交与 M-5a/M-5b 提交后入区间（终值 = M-8 批回填位）。

## 发布前回滚（任一门禁 FAIL）

fail-closed 阻断——修复后重跑门禁，不跳门（release-checklist 纪律）。候选态发现问题的回滚 = 丢弃候选提交（`git reset`）或修复追加，无外部影响；candidate manifest（M-5 才创建）随候选提交一并消失，无独立清理面。**受控整改优先于整体回滚**（REL-095/096/097 先例同构）。

## 回滚序列（代码面与数据面分别明确——按序执行，禁跳步）

1. **序① 数据面（先行声明——本版零新增数据面动作）**：
   - 0.94.0 载荷**零 `.governance` schema 变更、零迁移新增**——本版 git revert 不需要、也不会触发任何治理数据复原动作。
   - 写侧台账 `.governance/.write-guard-deferred-ledger.jsonl`（append-only JSONL，三键桶格式）为 0.88.0 FEAT-060 既有面；0.94.0 FEAT-081 face-5 词集检测按**既有格式**追加新观测族行（deferred_registration WARN 姿态）——revert 后新行停止产生，既有行不受影响，无行级清理动作（append-only 契约不变）。
   - **`.governance/` 台账非 git 管理（gitignored，AUDIT-082 口径同根 CLAUDE.md）**：git revert 物理上不触及治理台账；数据面回退与代码面回退互独立，须分别决策、分别验证（write-guard 复跑对账）。
2. **序② 版本面（git 面）**：`git revert <REL-098 组装提交>` + `release-projection --write` 再生（幂等再生——版本面收敛回 0.93.1 投影面；0.92/0.93/0.93.1 先例同构）+ `sync_entry_projection.py --write`（双根 entry 再生，repo root + e2e fixture 两调用；仓库根 CLAUDE.md 为 gitignored 工作树面，须单独再同步——AUDIT-082 口径）+ `check-projection-sync`/`check-version-consistency`/`check-entry-bootstrap-sync` 验证；引擎锚（REQUIRED_SNIPPETS 六针脚）随组装提交 revert 一并回收。投影面为确定性再生，不存在手改漂移。**无 B2 豁免面**。
3. **序③ 载荷面（按需——11 commit 单独 revert 序列）**：全版本弃用场景下按新→旧单独 revert（DEC-260 纪律：rider 随主提交同序）：
   - `af7cfbd`（FIX-426）→ `b0075d8`（FIX-425）→ `3883407`（FIX-424）→ `c00d70c`（FEAT-083）→ `9018006`（FIX-423）→ `768021b`（FIX-422）→ `0377b78`（FEAT-084）→ `8568b1b`（FIX-421）→ `9a527cb`（FEAT-084 memo——docs 件）→ `5de8548`（FEAT-082）→ `2aa2377`（FEAT-081）。
   - **测试面回退随票携带**：各票测试修改与代码修改同票——禁单边还原（只回代码留测试=半回退混合态）；FIX-424/425（纯 docstring）与 FIX-426（纯测试新增）互为独立票面，FIX-426 依赖 FIX-424/425 的 docstring 现状（bullet 集与计数词）——整组回退须按上述顺序保持 docstring 票先于 pin 测试票回收。
   - **同文件多票警告**：`verify_workflow.py` 承载 FEAT-081 face-5 接线+FIX-421 正则修复+FEAT-084 --scope 契约（三票同文件不同区）——禁单票选择性还原；`contract_matrix/`（snapshots.json/golden_samples.txt/generator.py）承载 FIX-423 regen 与 FEAT-081 deferred_observation 键、FEAT-084 golden 双 face——revert 须整组评估；`checks/version.py` STATIC_PIN 与 `architecture-baseline.json` archguard regen 承载多票 rider（FEAT-081/FIX-421/FIX-422/FIX-423/FEAT-083 regen 链）——revert 任一票后须复跑对应 regen 面再锚。
   - **闭链依赖警告**：FEAT-082（behavior 面指标）依赖 FEAT-081（loop_gate_processor 判定面）；FEAT-083（双端单源）依赖 FEAT-081+082 面——单独回退 FEAT-081 而留 FEAT-082/083 会产生导入断链，须按依赖逆序整组评估（或回退后立即跑定向组验证）。

## 发布后回滚（tag 已推）

1. **插件面（消费者）**: 用户侧 `/plugin update` 回退到 0.93.1（marketplace 历史版本可得）；本版无破坏性行为变更（B-23~B-27 为新增检测面/新增指标键/CLI 新旗标与信号解析修复，非旗标翻转——feature-flags-0.94.0 §非旗标面），回退无数据兼容风险。
2. **仓库面（维护者）——回滚三步序列**（=§回滚序列，按序执行）：Step 1 数据面决策（序①——零新增数据面，通常无动作）→ Step 2 git revert 链（序②版本面→序③载荷面按需）→ Step 3 投影再生验证（check-projection-sync/check-version-consistency/check-entry-bootstrap-sync + write-guard 复跑）。
3. **tag 误推**: 删 remote tag 重打——历史 tag 变更 MUST 有独立 DEC（release-checklist 纪律，缺 DEC 不创建/不改 tag）。
4. **发布后缺陷**: hotfix 0.94.1 路径——**不重写已发布 tag**。

## 数据兼容性

- `.governance/` 治理记录：零 schema 破坏性变更（本版零新增数据面——见序①；FEAT-081 观测族行按既有三键格式追加）。
- 消费者面（插件安装态）：入口 bootstrap 版本戳 0.94.0 经 FEAT-035 确认门自升级（用户未响应前零写操作）——回退 = 再 `/plugin update`（0.93.1 历史可得）。
- e2e fixture：投影 writer 收敛（17 面）——回退随版本面 revert+regen 一致回收。

## 边界声明（保守边界——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 裁定关闭〔前提移除式〕+1.0.0 前置族暂缓——用户 2026-09-30 范围裁定延续）。
