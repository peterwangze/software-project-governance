# REL-094 M-8 发布态回填批 — R0 发布审查报告

- **审查对象**：未提交 diff，4 文件 24+/23−（`project/CHANGELOG.md`、`docs/release/release-plan-0.91.0.md`、`docs/release/rollback-plan-0.91.0.md`、`docs/release/release-checklist-0.91.0.md`）
- **审查类型**：快审（机械回填批）——先审后提交（R0）
- **Reviewer**：Release Reviewer Agent（governance bootstrap-version 0.91.0）
- **日期**：2026-09-28
- **审查结论**：**APPROVED_WITH_NOTES** · **unresolved_blockers=0**
- **边界声明**：本审全程只读（git / release-ledger / grep 亲跑均为只读检查命令），未修改任何产品文件与 `.governance/**`；唯一产出=本报告。亲跑系任务义务（权威值一致性与勾选真实性抽验），非审查文档替代。

---

## 1. 权威值一致性（快审项 1）——PASS

| 事实 | 文档记载 | 亲跑实测 | 判定 |
|---|---|---|---|
| tag object | `0ea429f` | `git for-each-ref refs/tags/v0.91.0` → obj=`0ea429f3da4f…21149`，type=tag | ✅ 一致 |
| peel（发布 tip） | `bd9bfc1` | `git rev-parse v0.91.0^{commit}` → `bd9bfc188d38…0d6c` | ✅ 一致 |
| taggerdate | `2026-09-28 05:24:03 +0800` | for-each-ref taggerdate:iso 同值 | ✅ 一致 |
| 窗口终值 | 8 提交 | `git rev-list --count v0.90.0..v0.91.0` = **8** | ✅ 一致 |
| describe | `v0.91.0` 精确命中（HEAD 即 peel） | `git describe --tags` = `v0.91.0`；`rev-parse HEAD` = `bd9bfc1` | ✅ 一致 |
| push | origin master `8d25101..bd9bfc1` + tag 完成 | `git ls-remote origin`：refs/heads/master=`bd9bfc1…`、refs/tags/v0.91.0=`0ea429f…`；`merge-base --is-ancestor 8d25101 bd9bfc1` = true | ✅ 一致（远端实况亲证） |
| 8 提交清单（CHANGELOG 终账/rollback-plan/release-plan 三处） | `8d25101→196894a→9bafdf6→bc3f052→98104cb→5277ca5→fed2f53→bd9bfc1` | rev-list 逆序逐一比对，含各提交归属注记（FEAT-072/FIX-399/M-1/M-1R/M-4/M-5/M-5b） | ✅ 全等 |
| 0.90.0 锚（历史值复用） | peel `3f87459`、object `d2b2a6d`、taggerdate 2026-09-27 22:07:49 +0800 | `for-each-ref refs/tags/v0.90.0` + `rev-parse v0.90.0^{commit}` 同值 | ✅ 一致 |
| CHANGELOG 标题日期 | `## [0.91.0] - 2026-09-28` | = taggerdate 日期粒度；与 `## [0.90.0] - 2026-09-27` 同型（Keep-a-Changelog 行式一致） | ✅ 同型同粒度 |

附：`git show --stat bd9bfc1` = 1 文件 +1/−1（releases json manifest-only），与 EVD-1213「manifest-only 单父」申报一致；`rev-parse bd9bfc1^` = `fed2f53`（单父亲证）。

## 2. 占位清零（快审项 2）——PASS

对四文件亲验 grep：

| 模式 | 命中 | 判定 |
|---|---|---|
| `<发布 tip>` | 0 | ✅ 清零 |
| `<待回填 taggerdate>` | 0 | ✅ 清零 |
| `待回填` | 0 | ✅ 清零 |
| `占位` | 6（CHANGELOG L541/578/586/2765/2900、checklist L50） | ✅ 全部正当：前五处为 0.81/0.85 时代历史条目对占位行为的描述（FIX-339/B-1/FIX-021）；checklist L50 为 ⑨ 行「日期/taggerdate/tip 占位**消解**」完成态描述，非活跃占位 |
| `不预填` | 12 | ✅ 全部正当：CHANGELOG 0.86~0.90 各段历史「发布时点」纪律注记 + release-plan 起草期纪律行（L15~17/L101/L130，均已挂「已履行（M-8 批回填）」或注明起草冻结时点语义） |

两处占位注释改写后均为实名回填注记：CHANGELOG 标题注释（taggerdate 全值+FIX-349 口径）、rollback-plan 注释（tip=`bd9bfc1`+F-04 终点纪律已履行）——无任何悬空占位残留。

## 3. 勾选真实性（快审项 3）——PASS（抽验 4 处）

| 抽验点 | 勾选申报 | 亲验实况 | 判定 |
|---|---|---|---|
| ⑤ releases json fed2f53/bd9bfc1 | json 随 `fed2f53` 入库 + transition `bd9bfc1`（单父=fed2f53，candidate→released 双翻转） | `git log --diff-filter=A -- core/releases/0.91.0.json` = fed2f53；`bd9bfc1^`=fed2f53；json 实读：`lifecycle_state=released`（顶层+effective_state 双位）、event `rel094-transition` integrity=`sha256:70e09dd9…`、provenance=native | ✅ 属实 |
| ⑦ ledger 双 PASS | 本地+remote 双 PASS / NATIVE_RELEASED / issues=[] | 亲跑 `verify_workflow.py release-ledger --version 0.91.0`：本地 exit 0 / PASS / issues=[] / NATIVE_RELEASED / candidate=`fed2f53…`、release=`bd9bfc1…`；remote exit 0 / tag_facts PASS / issues=[] / local==remote tag_commit=`bd9bfc1…` | ✅ 属实 |
| ⑧ tag+push | tag object `0ea429f`（peel `bd9bfc1`，taggerdate 权威）+ push 完成（`8d25101..bd9bfc1` + tag）；CHANGELOG 日期已回填；plan-tracker L282 已呈已发布态 | §1 全表 + plan-tracker 版本行表 L282 实读（0.91.0 行=已发布 2026-09-28 全链摘要——工作树活文件，`.governance/` 系 FIX-141 gitignore 机制不入 git，与 tag 实况自洽）；CHANGELOG 标题 diff 实改 | ✅ 属实 |
| ⑥ CHANGELOG 日期 | 标题 2026-09-28=taggerdate 权威落字（M-8 批回填） | §1 表末行 + diff 实改；0.90.0 段同型 | ✅ 属实 |

**⑨/⑩ 如实性**：⑨ 标 `🔄 M-8 进行中（Coordinator 面）`——归档迁移/版本收口/released 终验确未完成（evidence-log 尾=EVD-1213 M-5b，无 M-8 机录行），如实；⑩ 未勾选——census/身份集红线维持保守未标记（终版复跑归 ⑨ released 终验），不虚构完成态，如实。

**⑥ 勘正口径**：diff ⑥ 行括注「单 canonical=project/CHANGELOG.md——DEC-242① 继承；原『project+root 投影双位同步』为 0.88 模板残留，M-5 审查 P3-2 勘正」——与 decision-log DEC-242①（L184：CHANGELOG canonical=project/CHANGELOG.md，根面为投影）及 `docs/reviews/review-REL-094-M5-R0.md` P3-2（L76：0.88.0 模板残留措辞，建议 M-8 批勘正）逐句吻合，勘正溯源链完整。

## 4. Findings

| 级别 | 编号 | 内容 | 处置建议 |
|---|---|---|---|
| P0 | — | 无 | — |
| P1 | — | 无 | — |
| P2 | — | 无 | — |
| P3 | N-1 | M-6/M-7 尚无 EVD 机录行（evidence-log 尾=EVD-1213 M-5b；⑦ 回填注记引用「M-6 ledger 权威实测」无 EVD 锚） | 属 ⑨ M-8 收口补账范围；ledger 事实本身本审已亲跑复核为真，不阻断本批 |
| P3 | N-2 | `docs/reviews/review-REL-094-M5B-R0.md`（M-5b 审查报告）当前 untracked | 建议随本批提交一并入库，避免审查报告悬空于版本控制外 |
| P3 | N-3 | 根 CHANGELOG.md 无 0.91.0 段 | 与 M-5 R0 P3-2 既有裁决一致（DEC-242① 前历史残留，非本次引入），无需本批处理，登记备查 |

## 5. 亲跑命令摘要（每命令一次，全只读）

1. `git for-each-ref refs/tags/v0.91.0`（object/type/taggerdate）+ `refs/tags/v0.90.0`（旁证）
2. `git rev-parse v0.91.0^{commit}` / `v0.90.0^{commit}` / `HEAD` / `bd9bfc1^`
3. `git rev-list --count v0.90.0..v0.91.0`（=8）+ `--oneline`（8 提交清单）
4. `git describe --tags`（=v0.91.0）
5. `git ls-remote origin refs/heads/master refs/tags/v0.91.0`（远端实况）
6. `git merge-base --is-ancestor 8d25101 bd9bfc1`（push 区间下界亲证）
7. `git log --diff-filter=A -- core/releases/0.91.0.json`（=fed2f53）+ `git show --stat bd9bfc1`（manifest-only 确证）
8. `python skills/software-project-governance/infra/verify_workflow.py release-ledger --version 0.91.0 --no-remote` 及远端形态（双 PASS 亲跑）
9. `Select-String`（grep 等价）四文件 × 5 模式（`<发布 tip>`/`<待回填 taggerdate>`/`待回填`/`占位`/`不预填`）
10. plan-tracker L275~290、evidence-log 尾部、DEC-242 行、review-REL-094-M5-R0.md P3-2 实读

## 6. 结论

**APPROVED_WITH_NOTES**（`unresolved_blockers=0`）——机械回填批四文件与 git/ledger/远端实况逐项吻合，占位清零完成，勾选真实性抽验 4/4 通过，⑨/⑩ 状态标注如实。本批可提交；P3×3 随 M-8 收口批处置（N-1/N-2 建议本次收口一并消化）。

---
*REL-094 M-8 批 R0 · Release Reviewer（只读快审）· 2026-09-28*
