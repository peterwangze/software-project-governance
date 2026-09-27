# 0.90.0 版本规划（REL-093 M-0）

- **日期**: 2026-09-27 · **状态**: M-0 冻结（arch GO——DEC-263）· **授权链**: DEC-253（用户预授权+arch 协作协议）→ DEC-255（载荷框架）→ DEC-263（M-0 冻结裁决）
- **主题**: 结构切换第一批——迁移验证与已知缺陷收口（DEC-252 / ADR-019 五步路径第 1~2 步完成态）

## 版本定义（DEC-263 最终措辞）

**「0.90.0 完成 DEC-252 范围内迁移验证、已知缺陷阶段性收口及切片前置；未完成纵向切片、权威翻转和行为级终态验收。」** B-12/B-13 不随版翻转（出厂 WARN-only；RISK-059 未关闭——翻转留独立授权票）。

## 载荷冻结清单（绑定提交）

| # | 票 | commit | 审查 | 验证基线 |
|---|---|---|---|---|
| 1 | FEAT-069 RB-2 前置批 | `f0999f7` | R0 AWN/0 | 4251P/2F→归因既有；28 测试 ×3 连跑 |
| 2 | FEAT-070 E-1-B 人工清单 | `8767858` | R0 AWN/0（DEC-258/259） | 链路 28×exit0；副本三面绿 |
| 3 | FIX-398 迁移链健壮性 | `48d21d9`+`0d31ea2` | R0 AWN/0 | 复演 16/16；RISK-060 关闭 |
| 4 | FEAT-071 E-1-A 结构影子 | `e61e267`+`12f2ea7` | R0 AWN/0 | 28 行零分歧；-k loop 547/547 |
| 搭车 | FIX-397 风险计数口径（非载荷治理修正） | `8f1f5c3` | R0 AWN/0 | 125P 亲验；DEC-256 |

**红线（DEC-263）**: 载荷禁扩；新增失败/证据与冻结提交不一致/越权翻转任一出现 → NO-GO 重裁。

## 已知边界（披露口径——四项强制〔①WARN-only ②2 confirmed/26 blocked ③影子三红不可切换 ④RISK-059 未关闭〕+ 逐项归因；②之 2/26 见 FEAT-070 行——M-3 勘误注记补枚举）

1. RB-2 阻断面出厂 WARN-only（翻转=B-12/B-13 授权票域）
2. 影子判据三红：CJ-1 确认可复现 0/2、CJ-4 结构覆盖 30/32 悬置、CJ-5 外部宿主未验 → **当前不可切换**（如实）
3. 全量测试基线 4351P/1F/1S（M-1 实测）：唯一 F=M0 pin 既有漂移（DEC-249 先例族，非载荷引入）；**不宣称全绿**
4. RISK-059 未关闭（翻转前置）；09-30 风险窗 RISK-036/039/047/048 复评已 2026-09-27 窗内履行（M-4 引用既有留痕）

## 里程碑（M-1~M-8）

| 里程碑 | 内容 | 状态 |
|---|---|---|
| M-1 | 门禁实测：pytest 全量 4351P/1F/1S（25:54）+ archguard 38/38 + check-version-consistency PASS + 版本 bump（SKILL 0.90.0→projection 17 面+宿主标记+六字面量） | ✅ 2026-09-27 |
| M-2 | CHANGELOG canonical 条目（project/CHANGELOG.md——DEC-263 披露口径全量） | ✅ `2869bc7` |
| M-3 | 双半面审查（CODE：载荷声明核对；RELEASE：发布就绪+披露口径） | 待执行 |
| M-4 | 风险复评锚（引用 09-27 窗内复评留痕；RISK-060 关闭态复核） | 随 M-3 |
| M-5 | 发布准备：release commit（version bump 面+ledger candidate event） | 待执行 |
| M-6 | tag v0.90.0 + ledger released event（单父 transition）+ push | 待执行 |
| M-7 | 归档（archive migrate dry-run→执行；integrity 校验） | 待执行 |
| M-8 | 发布后验证：check-release released PASS + session-snapshot + 收尾 | 待执行 |

## 回滚

- 发布前任何门禁 FAIL → fail-closed 阻断修复重跑（不跳门）
- tag 误推 → 删 remote tag 重打（历史 tag 变更需独立 DEC）
- 发布后缺陷 → hotfix 0.90.1 路径（不重写已发布 tag）
