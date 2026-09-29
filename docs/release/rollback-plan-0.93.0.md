# Rollback Plan — 0.93.0

- **日期**: 2026-09-29（准备态——tag 未打） · **回滚分类**: 可逆发布（**数据面大迁移声明**——本版含 FEAT-076 证据分层三腿迁移 1087 行出热 + FIX-407 narrative DEC 58 行迁移出热：两面均有 journal/索引可追溯与**迁移前全量备份**；`.governance/` 治理记录格式零 schema 破坏性变更）

## 回滚区间锚定

**回滚区间 = `041c0c4..<发布tip 回填位>`**（回退点 = `v0.92.0` tag peel transition）：

- 下界 `041c0c4` = v0.92.0 tag peel 实测（M-5b manifest-only transition 提交；taggerdate 2026-09-29 01:54:45 +0800 权威〔FIX-349〕）。
- 上界 = **M-5b transition 提交（发布 tip）= 回填位**（生成后实测回填——0.81.0 先例 F-04 终点纪律：终点=发布 tip，起草期不预编造）。
- 窗口计数（@起草时点 HEAD `4f52c6b` 实测 12 提交，旧→新）：`90b0b0f`（REL-095 M-8 发布态回填——非 0.93 行为载荷）→ `0ba86ce`（FIX-403）→ `f627c57`（FIX-404）→ `f297eeb`（FEAT-077）→ `130ed19`（DESIGN-021）→ `3544d09`（FEAT-078）→ `2ef9fc2`（FEAT-079）→ `2f3ecd4`（FEAT-080）→ `344ec8c`（FEAT-080 regen rider）→ `15e0a6d`（FEAT-076）→ `d22a4f9`（FIX-405+406+rider）→ `4f52c6b`（FIX-407+408+409 终窗）；REL-096 组装提交与 M-5a/M-5b 提交后入区间（终值 = M-8 批回填位）。

## 发布前回滚（任一门禁 FAIL）

fail-closed 阻断——修复后重跑门禁，不跳门（release-checklist 纪律）。候选态发现问题的回滚 = 丢弃候选提交（`git reset`）或修复追加，无外部影响；candidate manifest（M-5 才创建）随候选提交一并消失，无独立清理面。R0 先例：发布终审 NEEDS_CHANGE 三处文本级+发布门 7 issues 经 C1~C5 快修闭合——**受控整改优先于整体回滚**（REL-095 M-2 同构）。

## 回滚三序（按序执行，禁跳步）

1. **序① 迁移面（`.governance` 数据——先于 git 面）**：
   - **FIX-407 narrative DEC 58 行**：迁移前全量备份（**主锚** `.governance/backups/fix407-backup-20260929/`——R1-F-15 持久化双锚；decision-log.md sha256 `70F7458446F82CDEF05F7123695A50A3E067729FCDD0869CD1F84365D7EBE217` + archive 树——**保留至发布结账后**；易失副本见 §数据备份与结账纪律）；复原 = 备份回拷 + `archive.py rebuild-index`（Decision 索引 185→127 守恒回退）；归档件 `archive/decisions/decisions-v0.1.0-0.91.0.md` 删除尾部 58 段或整体回退至备份版。
   - **FEAT-076 证据分层 1087 行**：journal 逐 ID 可追溯复原（三腿迁移各带 journal）+ `archive.py rollback`；GovernanceDataSource 读取门面为代码面（随序③ revert 消失），数据复原后读取自动回热表面。
   - **EXC-003 删除面**：`.governance/exceptions.json` 回至含 EXC-003 条目形态（备份随 fix407-backup 或 git 历史不可达——该文件 gitignored，以备份/journal 为准）。
2. **序② 版本面**：`git revert <组装提交>` + `release-projection --write` 再生（幂等再生——版本面收敛回 0.92.0 投影面；0.92 先例 `40eb6f7` 同构）+ `check-projection-sync`/`check-version-consistency` 验证；投影面为确定性再生，不存在手改漂移。**无 B2 豁免面**（本版零 LRC 豁免——较 0.92 少一面）。
3. **序③ 载荷链（按需）**：全版本弃用场景下 12+ 提交按新→旧连载回退（regen rider 随主提交同序——DEC-260 纪律对称）；同文件多票 revert 禁单票选择性还原（verify_workflow.py 承载 FIX-405/406 门面+FEAT-080 接线+版本锚多段 hunk；archive.py 承载 FIX-407 解析器——选择性还原产生半回退混合态）。

## 数据备份与结账纪律

- **fix407-backup 双锚（R1-F-15）**：**主锚** `.governance/backups/fix407-backup-20260929/`（持久化，sha256 校验后复制：decision-log.md `70F7458446F82CDEF05F7123695A50A3E067729FCDD0869CD1F84365D7EBE217` + archive 树 116 文件，index.md hash 一致性双验）+ **易失副本** `C:\Users\peter\AppData\Local\Temp\dsh-edmOzF\rel096-gov-backup\fix407-backup\`（TEMP 生命周期注记——随 OS 清理消失非缺陷）。保留条件：发布结账（M-8 收口+ledger 双 PASS）前禁删主锚；结账后随 `.governance/backups` 例行清理排程。
- **ledger 事件链可溯**：0.93.0 candidate/released 事件（M-5a/M-5b）写入 `core/releases/0.93.0.json`（NATIVE_CANDIDATE→released，integrity sha256 链）——回滚时随 git revert 消失；已 push 的 tag 误推场景见下节。

## 发布后回滚（tag 已推）

1. **插件面（消费者）**: 用户侧 `/plugin update` 回退到 0.92.0（marketplace 历史版本可得）；本版无破坏性行为变更（M1/M2 执法面经 DEC-290/291 授权链，非旗标翻转——feature-flags-0.93.0 §非旗标面）；证据迁移不破坏消费者读取契约（`archive/index.md` 读取为 bootstrap 协议既有），回退无数据兼容风险。
2. **仓库面（维护者）——回滚三步序列**（=§回滚三序，按序执行）：Step 1 迁移面数据复原（序①）→ Step 2 git revert 链（序②版本面→序③载荷链按需）→ Step 3 投影再生验证。
3. **tag 误推**: 删 remote tag 重打——历史 tag 变更 MUST 有独立 DEC（release-checklist 纪律，缺 DEC 不创建/不改 tag）。
4. **发布后缺陷**: hotfix 0.93.1 路径——**不重写已发布 tag**。

## 数据兼容性

- `.governance/` 治理记录：零 schema 破坏性变更（迁移为行搬家+索引重建，格式不变）。
- 消费者面（插件安装态）：入口 bootstrap 版本戳 0.93.0 经 FEAT-035 确认门自升级（用户未响应前零写操作）——回退 = 再 `/plugin update`（0.92.0 历史可得）。
- e2e fixture：投影 writer 收敛（17 面）——回退随版本面 revert+regen 一致回收。

## 边界声明（保守边界——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 维持打开——外部验证/官方提交/1.0.0 review 未满足）。
