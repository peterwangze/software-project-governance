# FIX-445 — R10 补核报告事实校准（同 Reviewer，同轮）

**对象**: `docs/reviews/supplement-FIX-445-DESIGN-R10-evidence.md`（105 行已 persist，冻结不改）。本文件只补校准事实，不删除旧文错误、不新 design round、不触产品。角色与 tech-review/design-review 规范沿用本会话已加载版本；本轮工具仅 read×3 + glob×1，零执行零写。

```json
{"verdict":"APPROVED_WITH_NOTES","round":10,"unresolved_blockers":0,"review_scope":"static_contract_analysis_factual_calibration","implementation_authorized":false}
```

**校准性质**：以下四项均为 **supplement 自身的事实错误/无证断言**，经逐行重读 hook :478-554/:698-812 与独立 glob 复核确认。独立重推后**无一项改变 R10 analysis（mention-contract-R10.md）的中心结论**——analysis 仍通过；理由逐项附后。

## 一、:46 窗口字符数 12 → **14**

`已知no-separator` = 已知(2)+no(2)+`-`(1)+separator(9) = **14 字符**，非 12。重推：wl=14 ≤16（:781 过）、trim 后 wn=14 ≤16（:785 过）→ 进入双表切分（:786-800），`已`不在 24-否定表（:717）亦不在 19-填充表（:719）→ 首字符残留 → bad=1（:805）→ BLOCK。**判定更精确**：该窗口是**残留拒绝**而非长度溢出拒绝；BLOCK 结论不变。R10 analysis §4 未给字符数（12 为 supplement 误加）——analysis 无此错。

## 二、:50 R8 前缀归属错拼 → 两条独立 match 分列

原文「mo=外层 将/把（:763），前缀 将结论/把结果 均不可消费」把两条 match 的属性接错。正确（每例两条 match，均拒）：
- **outer match**（:752-764）：mo=句首 `将`/`把`，op 前无 isterm（:777-778）→ cs=1 → wl=0 → **空窗口，cnt=0** → :801 `ok && cnt==1` 不成立 → bad。**前缀为空，计 0 拒**。
- **inner match**（:766-768）：mo=`视为`/`当作` 位置，前缀=`将结论`/`把结果` → `将`/`把`两表皆无 → **残留拒**。

两例 BLOCK **结论不变**。R10 report :75「ms=mo at 将/把, not the inner mid」与 analysis §4「rejects their unqualified frameworks」均无此归属错误——错误仅在 supplement。此前缀归属描述由本校准取代。

## 三、:56 撤回无证断言，方向分写，population 独立复核

**撤回**：「当前 incidents 目录 FIX-445* JSON 文件远少于 24，现窗口不触发」「方向保守=误拒豁免面而非逃逸」——当时未做 inventory 即断言（无证），且 glob 非 JSON-only。

**独立 glob 复核**（`.governance/incidents/*FIX-445*`，fileonly）：**54 条命中，其中 26 条 `.json`**，余 28 条为 .py/.ps1/.md/.log——与 parent metadata 一致。含义：
- 54 > 32：0 refs 时 `files[:32]`（:497）在 sorted glob 序上**当前即发生截断**；26 JSON > 24——**R2 glob ≤24 字面违反的 population 条件当前已满足**（28 个 non-JSON 亦占 files 名额并在 :528-534 被 open+read、:536-539 perr 归零记录——IO 成本面在场）。
- **方向必须分写**：(a) refs 稀少时 glob 可占满 32 席 = **扩大 eligible credential 集合与读取成本面**（超出 R2 授权语料面的契约扩张，**非保守 fail-safe**；每条凭据仍须 C-1~C-5 全链，故非已证 escape，但亦不得断言无逃逸）；(b) refs 占位挤压 glob（32 全占/16 剩 16）= **缩减 availability**（合法凭据来源不足——保守方向）。两方向相反，不得一概而论。
- **未测 unknown**：当前 canonical run 的实际 selected 32 条构成、产出 records 数、对判定与耗时的实际影响——本 reviewer 未执行 hook，不构造结论。

**对 analysis 的影响**：analysis §3 只披露「allocation rules 不一致」，未做当前触发断言——无此错。校准**增强** W1 现实相关性（触发条件当前满足），W1 定性仍为 WARNING（R10 report：披露过的 discrepancy 不拒分析），产品重开前必须裁决——不升级为 analysis blocker。

## 四、:60 W1 最小 fix 位置修正（proposal 级，非 product authorized）

原文「:496 后对 glob 结果独立 `[:24]`」**不等价独立 glob cap**：:490-496 的 refs 与 glob 已合并入同一 files 列表，loop 后加 `[:24]` 截的是合并列表、可能截掉 refs。修正 proposal（供 decision packet，需授权票 + focused tests 才可实施）：
- glob-only list 在 join 前构建并独立截断：`globs = sorted(glob(...))[:24]`，对 refs 去重后并入，最后 `files = files[:32]`；或 bound-merge（refs 全留 → glob 补至 24 → 合计 [:32]）。
- glob 容量超限诊断（如 `globcap`）须与 PATHDROP（outside-repo drop :510/:519）**分开计数**，不混用现有 drop 口径。

## 结论

四项校准全部落在 supplement 层；R10 analysis 的中心论断（EVD1587 冲突、R9/R8 拒绝、credential/guard 边界、W1 披露）经校准后重推**全部保持成立**——**analysis 仍通过（APPROVED_WITH_NOTES/unresolved_blockers=0，校准确认）**，无需 new analysis blocker。事实差异不触及 scope/安全契约变更，无 user critical decision 新增项。不变项：旧 seq46/47 机录、原 R10 report、evidence supplement 均冻结；产品未动；64 tests/92.738s/1FAIL、CodeR6 BLOCKED/3、W1、健康/交付门全部保持；CPU27.8/CLI36/434339/32MiB/1500 不改；无 R11、无实现授权。

（正文约 690 中文字。persist 建议：原样保存至 `docs/reviews/supplement-FIX-445-DESIGN-R10-calibration.md`，机录沿用上方 JSON。）
