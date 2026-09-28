# Rollback Plan — 0.92.0

- **日期**: 2026-09-29 · **回滚分类**: 可逆发布（**数据面有界迁移声明**——本版含 18 行 EVD 有界迁移出热〔DEC-284 授权〕：journal 逐 ID 可追溯+隔离副本实弹演练已证行级复原可达基线〔EVD-1233〕；其余 178 行历史证据面**未迁移**〔EXC-002 纸质治理——无迁移即无数据回滚面〕；例外标注机制 annotation-only **不改原始结果/字节/退出码**；`.governance/` 治理记录格式零 schema 破坏性变更——M-3 CODE 聚合终审对账 51 文件无未申报夹带）

## 回滚区间锚定

**回滚区间 = `bd9bfc1..<发布tip 回填位>`**（回退点 = `v0.91.0` tag）：

- 下界 `bd9bfc1` = v0.91.0 tag peel 实测（`git cat-file -p v0.91.0` 亲证 tag object `0ea429f` → object `bd9bfc1`；taggerdate 2026-09-28 05:24:03 +0800 实测——**FIX-349 口径：taggerdate 权威**）= 0.91.0 M-5b transition 提交。
- 上界 = **M-5b transition 提交（发布 tip）= 回填位**（生成后实测回填——0.81.0 先例 F-04 终点纪律已履行：终点=发布 tip，非候选打包提交；起草期不预编造）。
- 窗口计数：`git rev-list --count bd9bfc1..HEAD` = **13**（2026-09-29 实测，HEAD = `df26f7e` = REL-095-B2；`git describe` = v0.91.0-13-gdf26f7e 交叉印证）；发布终值 = M-8 批回填位。
- 区间内 13 提交（@`df26f7e` 时点，旧→新）：`4cb3081`（REL-094 M-8 发布态回填——非 0.92 行为载荷）→ `e65b317`（FEAT-073）→ `a7bcd5f`+`f06a2bf`（FIX-400 主+regen）→ `136d65e`（FIX-401）→ `b6575bd`（FEAT-074 输入锚）→ `c90768f`（FEAT-074）→ `16a5157`+`484dd77`（FEAT-075 主+regen）→ `dc45e24`（FIX-402）→ `40eb6f7`（REL-095 M-1 版本面）→ `12bef7c`（REL-095 M-2 整改治理文档）→ `df26f7e`（REL-095-B2）；M-4 本批（四件套+M-3 报告收编）提交后入区间。

## 发布前回滚（任一门禁 FAIL）

fail-closed 阻断——修复后重跑门禁，不跳门（release-checklist 纪律）。候选态发现问题的回滚 = 丢弃候选提交（`git reset`）或修复追加，无外部影响；candidate manifest（M-5 才创建）随候选提交一并消失，无独立清理面。M-2 整改链先例：首跑 4 失败面经 DEC-283 受控回退（6 归期行）+DEC-284/285 有界授权消化——**受控整改优先于整体回滚**。

## 回滚三序（本版核心——按序执行，禁跳步）

1. **序① 迁移面（`.governance` 数据——先于 git 面）**：有界迁移 18 EVD 出热的回滚 = **journal 逐 ID 可追溯复原**（DEC-284 验收第 4 项——区分 4 随行 vs 14 补完成）+ **archive.py rollback**；该能力已**隔离副本实弹演练**证实（EVD-1233：evidence 行级复原／任务行尾置与头块残留 runbook 清理可达基线／EOL 规范化注记）。178 行未迁移面**无复原动作**（EXC-002 纸质例外随版本回滚整体失效，无数据操作）。
2. **序② B2 豁免面**：`git revert df26f7e` **单提交自洽**——账本第 5 条 LRC-EXEMPT-FIX401R0-79-1+双锚 re-pin（digest 4f8a6cc8→d47f5d16）+定向测试**同 commit**（锚与账本同提交，整体回退无悬挂）；回退后 LRC 恢复对该行 BLOCKED 判定（发布门禁信号如实回退，非数据损失）。
3. **序③ 版本面**：`git revert 40eb6f7` + `release-projection --write` 再生（幂等再生——版本面收敛回 0.91.0 投影面；**0.91 先例 `bc3f052` 同构**）+ `check-projection-sync`/`check-version-consistency` 验证；投影面为确定性再生，不存在手改漂移。全版本弃用场景下六票载荷 revert 按新→旧连载（regen 分离提交随主提交同序回退——DEC-260 纪律对称；`df26f7e` 已由序②覆盖）。

## EXC 到期处置（EXC-001/EXC-002 到期预案——RL-F3/P3-2 承载义务）

- **均不自动续期**：EXC-001 expires **2026-10-12**（recheck_on 2026-10-05）；EXC-002 期限 **min(0.93 准入评审开始, 2026-10-12 绝对截止)**——延期须重审批（非周报续期）。
- **失效路径**：2026-10-12 前未完成 0.93 准入 → 两例外失效 → **28s/Check 27 恢复硬阻断**（原始超标/178 行回归 FAIL 形态——两面原始输出均保留，恢复即呈现）→ **发布冻结直至重评**（新 DEC 另批）。
- **周义务**：EXC-001 冷热/总量/积压指标（首期=**M-8 排程**；recheck 2026-10-05）+ EXC-002 周报（增长容忍 0 监控）。
- **0.93 承接**：FEAT-076（五条件+91 物理未归档 ID 回填 C-3）；EXC-002 关闭条件=获授权迁移完成+Check 27 原生 PASS+读取验证通过。
- **两面互不覆盖**：EXC-001（机注）与 EXC-002（纸质）作用域/期限/owner 三维独立（M-3 RELEASE 重点 2 亲证）——任一面到期失效不自动波及另一面，处置各自按条款重评。

## 发布后回滚（tag 已推）

1. **插件面（消费者）**: 用户侧 `/plugin update` 回退到 0.91.0（marketplace 历史版本可得）；本版无破坏性行为变更（B-1~B-7 每项回滚独立在案——feature-flags-0.92.0 §非旗标面；数据面有界迁移 18 EVD 出热**不破坏消费者读取契约**——`archive/index.md` 读取为 bootstrap 协议既有），回退无数据兼容风险。
2. **仓库面（维护者）——回滚三步序列**（=§回滚三序，按序执行）：Step 1 迁移面数据复原（序①）→ Step 2 git revert 链（序② B2 豁免→序③ 版本面，按需连载荷六票）→ Step 3 投影再生验证（序③尾段）。同文件多票 revert 禁单票选择性还原（verify_workflow.py 承载 FIX-400 超时面+FEAT-075 例外面+M-1 版本字面量多段 hunk——选择性还原产生半回退混合态）。
3. **tag 误推**: 删 remote tag 重打——历史 tag 变更 MUST 有独立 DEC（release-checklist 纪律，缺 DEC 不创建/不改 tag）。
4. **发布后缺陷**: hotfix 0.92.1 路径——**不重写已发布 tag**。

## 数据兼容性

- **18 EVD 出热**（DEC-284 有界迁移）：消费者读取契约=`archive/index.md`（bootstrap 协议既有——归档证据=有效证据口径不变）；迁移回滚能力=序①（隔离副本实弹演练 EVD-1233 已证可达基线）。
- **FIX-402 C-2 写回 11 处**=确定性数据校正（逐处可溯——台账 `docs/governance/fix-402-data-corrections-ledger-20260928.md` 在案）。
- 零 schema 变更；annotation-only 例外标注不改原始结果/字节/退出码；bootstrap 升级路径（0.91→0.92）经 check-version-consistency PASSED（13 文件+bootstrap markers——M-3 CODE 亲跑）。

## 回滚影响评估

- **序①**：放弃有界迁移增益——18 EVD 回热（evidence-log 尺寸回升；EXC-001 上限口径不变、不滚动）。
- **序②**：LRC 恢复 BLOCKED 判定（FIX-401-R0 审查行——发布门禁信号如实回退；B2 为 DEC-283 题 2 一次性授权，回退后该行处置须重评）。
- **序③**：放弃六票增益——strict 余量回 9 tok 口径（5991/6000）／release-gate 恢复 180s 假红面／loop 计时恢复环境敏感（RISK-048 面 reopen）／scan-families+例外标注机制移除／台账写回回退。
- RISK-036 边界与官方审批状态不受回滚影响（本版未声明任何官方审批）。

边界声明（保守边界——REL-021 token 全量）：本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 维持打开——外部验证/官方提交/1.0.0 review 未满足）。
