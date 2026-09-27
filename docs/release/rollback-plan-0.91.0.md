# Rollback Plan — 0.91.0

- **日期**: 2026-09-28 · **回滚分类**: 可逆发布（**数据面零迁移声明**——本版零 schema 变更、零数据迁移、迁移工具协议戳未触碰；`.governance/` 治理记录格式零破坏性变更——窗口 diff 恰=载荷两票+六锚版本字面量+基线面〔M-3 RELEASE 审查亲跑 #9 亲证：37 文件，6000/限额/计量器/激活类守卫 token 零命中〕）

## 回滚区间锚定

**回滚区间 = `3f87459..bd9bfc1`**（回退点 = `v0.90.0` tag）：

- 下界 `3f87459` = `git rev-parse v0.90.0^{}` 实测 = 0.90.0 transition 提交；tag object `d2b2a6d`，taggerdate 2026-09-27 22:07:49 +0800 实测（**FIX-349 口径：taggerdate 权威**）。
- 上界 = **M-5b transition 提交（发布 tip）= `bd9bfc1`**（v0.91.0 tag peel 实测，tag object `0ea429f`，taggerdate 2026-09-28 05:24:03 +0800 权威——REL-094 M-8 批回填）：

  <!-- 发布 tip = bd9bfc1：M-5b transition 提交生成后实测回填（0.81.0 先例 F-04 终点纪律已履行——终点=发布 tip，非候选打包提交） -->

- 窗口计数：`git rev-list --count 3f87459..HEAD` = **5**（2026-09-28 实测，HEAD = `98104cb` = REL-094 M-1R；`git describe` = v0.90.0-5-g98104cb 交叉印证）；**发布终值（M-8 批回填）：`git rev-list --count 3f87459..bd9bfc1` = 8；`git describe` = v0.91.0 精确命中（HEAD 即 peel）**。
- 区间内 8 提交（发布终值，M-8 批回填，旧→新）：`8d25101`（0.90.0 收尾披露批——非 0.91 行为载荷）→ `196894a`（FEAT-072）→ `9bafdf6`（FIX-399）→ `bc3f052`（REL-094 M-1 版本面）→ `98104cb`（REL-094 M-1R 基线面）→ `5277ca5`（REL-094 M-4 四件套）→ `fed2f53`（REL-094 M-5 candidate manifest+发布态改写）→ `bd9bfc1`（REL-094 M-5b transition = 发布 tip）。

## 发布前回滚（任一门禁 FAIL）

fail-closed 阻断——修复后重跑门禁，不跳门（release-checklist 纪律）。候选态发现问题的回滚 = 丢弃候选提交（`git reset`）或修复追加，无外部影响；candidate manifest（M-5 才创建）随候选提交一并消失，无独立清理面。

## 发布后回滚（tag 已推）

1. **插件面（消费者）**: 用户侧 `/plugin update` 回退到 0.90.0（marketplace 历史版本可得）；本版无破坏性行为变更（推荐卡升级为 agent 行为契约呈现面——CLI 旗标零增删改〔M-3 CODE 亲证：窗口 `add_argument`/`def cmd_`/`sys.argv` 变更行 = 0〕；stdlib-only 无依赖变更；28c 修复为判据召回向放宽，纯格式旧行行为不变），回退无数据兼容风险
2. **仓库面（维护者）——回滚三步序列**（按序执行，禁跳步）：
   - **Step 1 git revert 发布链提交序列**（新→旧，单轨可逆）：`git revert 98104cb bc3f052 9bafdf6 196894a`（如需连披露批一并回退再加 `8d25101`——非 0.91 行为载荷，按需取舍并留痕）；同文件多票 revert 禁单票选择性还原（verify_workflow.py 承载 FEAT-072 锚面+FIX-399 正则区+M-1 六锚字面量三段 hunk——选择性还原产生半回退混合态）
   - **Step 2 版本投影再生回滚**：回退后运行 `release-projection --write`（幂等再生——版本面收敛回 0.90.0 投影面）+ `check-projection-sync`（期望 28/28）+ `check-version-consistency` 验证；投影面为确定性再生，不存在手改漂移
   - **Step 3 manifest lifecycle 回退**：candidate 态（M-5 后、M-7 前）= candidate 提交随 revert 一并消失；released 态（M-7 tag 后）= release-ledger `withdrawal` 事件置位（`infra/release/ledger.py` `derive_effective_state` 语义——withdrawn=True）；**历史 tag 变更 MUST 有独立 DEC**（release-checklist 纪律，缺 DEC 不创建/不改 tag）
3. **tag 误推**: 删 remote tag 重打——历史 tag 变更须独立 DEC（同上）
4. **发布后缺陷**: hotfix 0.91.1 路径——**不重写已发布 tag**

## 数据兼容性

无 schema 变更；`.governance/` 治理记录格式无破坏性变更。M-1R 的 M0 fixture 双源重钉（behavior-protocol.md [512,556]→[522,566]、SKILL.md [223,230]→[225,232]）为**治理 fixture 元数据面**、携 rebaseline 溯源块与 prior 双源哈希逐字节存档（授权变更重钉非静默漂移——DEC-262② sanctioned regen 同型），不触宿主用户数据；bootstrap 升级路径（0.90→0.91）经宿主标记同步验证（check-version-consistency PASSED——M-3 审查亲跑）。

## 回滚影响评估

回滚唯一影响面=放弃本版两票增益：①FEAT-072 推荐卡契约呈现升级（agent 行为契约面——无机器消费方解析推荐卡正文〔M-3 CODE §5.2 亲证：RECO 行机器写入格式未变、无 schema 断言依赖旧文案〕，回退不破坏任何机检链）②FIX-399 误报消解回退（28c 对装饰日期单元格恢复旧误判行为——已知面回归，非数据损失）。RISK-036 边界与官方审批状态不受回滚影响（本版未声明任何官方审批）。

边界声明（保守边界——REL-021 token 全量）：本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 维持打开——外部验证/官方提交/1.0.0 review 未满足）。
