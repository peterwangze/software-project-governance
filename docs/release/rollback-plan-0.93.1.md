# Rollback Plan — 0.93.1

- **日期**: 2026-10-01（准备态——tag 未打） · **回滚分类**: 可逆发布（**零新数据面声明**——本版载荷无 `.governance` schema 变更、无迁移新增、无旗标新增；代码面=六 commit 可单独 revert + 版本面确定性再生回收）

## 回滚区间锚定

**回滚区间 = `8107e02..<发布tip 回填位>`**（回退点 = `v0.93.0` tag peel transition）：

- 下界 `8107e02` = v0.93.0 tag peel 实测（M-6/M-7 candidate_to_released transition 提交；taggerdate 2026-09-30 20:41:25 +0800 权威〔FIX-349，aa405c7 G-4 回填口径〕）。
- 上界 = **M-5b transition 提交（发布 tip）= 回填位**（生成后实测回填——0.81.0 先例 F-04 终点纪律：终点=发布 tip，起草期不预编造）。
- 窗口计数（@起草时点 HEAD `693fea8` 实测，旧→新）：`e9a0869`（FIX-413——0.93.0 线 post-transition 内容件，非本版载荷）→ `aa405c7`（REL-096 G-4 taggerdate 回填——0.93.0 线收尾）→ **本版载荷八提交**：`65cf188`（FIX-414）→ `fe0afcb`（FIX-415）→ `2fa1ebd`（FIX-416）→ `263779f`（FIX-397 docs 归档）→ `7d6c4a7`（FIX-397 revert——否证回退对，净零）→ `bdc037e`（FIX-419）→ `b12eee1`（FIX-417）→ `693fea8`（FIX-418）；REL-097 组装提交与 M-5a/M-5b 提交后入区间（终值 = M-8 批回填位）。

## 发布前回滚（任一门禁 FAIL）

fail-closed 阻断——修复后重跑门禁，不跳门（release-checklist 纪律）。候选态发现问题的回滚 = 丢弃候选提交（`git reset`）或修复追加，无外部影响；candidate manifest（M-5 才创建）随候选提交一并消失，无独立清理面。**受控整改优先于整体回滚**（REL-095/096 先例同构）。

## 回滚序列（代码面与数据面分别明确——按序执行，禁跳步）

1. **序① 数据面（先行声明——本版零新数据面动作）**：
   - 0.93.1 载荷**零 `.governance` schema 变更、零迁移新增**——本版 git revert 不需要、也不会触发任何治理数据复原动作。
   - 0.93.1 窗口内执行的归档两轮+衍生清扫（对账台账 §一 #6）属 0.93.0 数据线既有迁移面的执行，其复原路径（fix407-backup 主锚 + journal 逐 ID 复原 + `archive.py rollback`/`rebuild-index`）见 `docs/release/rollback-plan-0.93.0.md` 序①——**不随本版代码回退自动消失或恢复**。
   - **`.governance/` 台账非 git 管理（gitignored，AUDIT-082 口径同根 CLAUDE.md）**：git revert 物理上不触及治理台账；数据面回退与代码面回退互独立，须分别决策、分别验证（write-guard 复跑对账）。
2. **序② 版本面（git 面）**：`git revert <REL-097 组装提交>` + `release-projection --write` 再生（幂等再生——版本面收敛回 0.93.0 投影面；0.92/0.93 先例同构）+ `sync_entry_projection.py --write`（双根 entry 再生；仓库根 CLAUDE.md 为 gitignored 工作树面，须单独再同步——AUDIT-082 口径）+ `check-projection-sync`/`check-version-consistency`/`check-entry-bootstrap-sync` 验证；引擎锚（REQUIRED_SNIPPETS 六针脚）随组装提交 revert 一并回收。投影面为确定性再生，不存在手改漂移。**无 B2 豁免面**。
3. **序③ 载荷面（按需——六 commit 单独 revert 序列）**：全版本弃用场景下按新→旧单独 revert（DEC-260 纪律：rider 随主提交同序）：
   - `693fea8`（FIX-418）→ `b12eee1`（FIX-417）→ `bdc037e`（FIX-419）→ `2fa1ebd`（FIX-416）→ `fe0afcb`（FIX-415）→ `65cf188`（FIX-414）。
   - **测试面回退随票携带**：FIX-414/415/418 的测试修改与各自代码修改同票——禁单边还原（只回代码留测试=半回退混合态）。
   - **同文件多票警告**：`verify_workflow.py` 承载 FIX-416 regen rider（static_pins 再锚）与 FIX-418 pin 维护（host-facts/class/method pin+ledger dead entry 清理）——禁单票选择性还原；`archive.py` 系承载 FIX-417 拆分（archive.py+archive_parsing.py+archive_indexing.py 三文件模块面）——revert 须整票携带伴随模块。
   - **否证回退对**（`263779f`↔`7d6c4a7`）已自抵（revert 在窗口内），无回退动作；仅整窗回退场景需两票同序 revert 保持账面一致。

## 发布后回滚（tag 已推）

1. **插件面（消费者）**: 用户侧 `/plugin update` 回退到 0.93.0（marketplace 历史版本可得）；本版无破坏性行为变更（B-21/B-22 为 CLI 口径对齐与阈值重校准，非旗标翻转——feature-flags-0.93.1 §非旗标面），回退无数据兼容风险。
2. **仓库面（维护者）——回滚三步序列**（=§回滚序列，按序执行）：Step 1 数据面决策（序①——零新数据面，通常无动作）→ Step 2 git revert 链（序②版本面→序③载荷面按需）→ Step 3 投影再生验证（check-projection-sync/check-version-consistency/check-entry-bootstrap-sync + write-guard 复跑）。
3. **tag 误推**: 删 remote tag 重打——历史 tag 变更 MUST 有独立 DEC（release-checklist 纪律，缺 DEC 不创建/不改 tag）。
4. **发布后缺陷**: hotfix 0.93.2 路径——**不重写已发布 tag**。

## 数据兼容性

- `.governance/` 治理记录：零 schema 破坏性变更（本版零数据面——见序①）。
- 消费者面（插件安装态）：入口 bootstrap 版本戳 0.93.1 经 FEAT-035 确认门自升级（用户未响应前零写操作）——回退 = 再 `/plugin update`（0.93.0 历史可得）。
- e2e fixture：投影 writer 收敛（17 面）——回退随版本面 revert+regen 一致回收。

## 边界声明（保守边界——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 裁定关闭〔前提移除式〕+1.0.0 前置族暂缓——用户 2026-09-30 裁定）。
