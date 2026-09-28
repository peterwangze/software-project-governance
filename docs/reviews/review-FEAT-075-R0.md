# Review FEAT-075-R0 — 四行族 dry-run + 聚合层例外标注（DEC-278 单元二）

- **round**: R0（首轮，无前轮引用）
- **日期**: 2026-09-28
- **Reviewer**: Code Reviewer（只读；采信 Developer 测试输出+静态交叉印证）
- **审查对象**: 工作树未提交 6 产物（archive.py / verify_workflow.py / exception_registry.py〔新〕/ test_archive.py / test_verify_workflow.py / feat-075-four-family-dryrun-20260928.md〔新〕）
- **基准**: DEC-278（§3.1 单元二 + §3.2 MUST NOT + §4 可证伪验收）+ feat-074-classification-diff-20260928.md + 盘点 §2.3
- **结论**: **NEEDS_CHANGE**（P0=0；P1×1〔验收档算术，代码面零必改〕+ P2×1 + P3×3）

## 1. 五维度结论表

| 维度 | 结论 | 关键事实（文件+行号） |
|---|---|---|
| 正确性 | PASS（1 项 P1 在验收档算术，代码逻辑未发现错误） | ①分类核抽取：`_make_ref_verdict`（archive.py L1581-1658）与 `_classify_evidence_rows`（L1661-1836）单一来源接线（L1739 调用，闭包体已移出）；EVD 族扫描直接调用 `_classify_evidence_rows`（L2466-2468）=构造性零漂移；REVIEW/TRIAGE/RECO 共享 `_make_ref_verdict`+模块级 `_REF_FAILURE_SUBSTATE_ORDER`（L1143-1149，L1815 与 L2351 同一序）零平行实现。②写边界：五守卫亲证（L1893 `_migrate_evidence`/L2678 `migrate_evidence_resumable`/L3079 `migrate_by_version`/L4916 `migrate_auto`/L5351 CLI migrate）+ default-deny（非 EVD 一律 raise）+ 委托链纵深（migrate_auto→migrate_by_version→_migrate_evidence 各自独立守卫）+ rollback 只回灌 `\| EVD-` 行（L4408 过滤器）非旁路 + 产品代码内无第六调用面（grep 定谳）。③例外机制：exception_registry.py 亲读全文——四态+artifact_missing（L180-215）、条目畸形/错 schema/重复 id 全惰性且入 errors（L75-166）、作用域=check_id+artifact 精确匹配（L249）、纯标注不变异（L218-274）。④四族 schema：`_ROW_FAMILY_ID_RES`（L2217-2221）REVIEW 复合 ID/SCOPE/轮次、legacy 无轮次、版本区间异形→unknown 显式计数（live 实证 L1146 `REVIEW-0.43-0.44.1`）；门控=ID 内嵌∪关联列 fail-closed 并集（L2281）。⑤例外四态 fixture 11 用例+拒绝面 11 用例（4 入口×3 族×dry_run 双态=24 subTests，L5439-5471）断言拒绝先于任何写入（L5470-5471）。 |
| 安全性 | PASS | 输入校验：registry schema marker/必填字段/正整数 growth_control/ISO 日期序/重复 id 全校验（L46-49, L75-166）；无注入面（纯文件读取+JSON 解析，OSError/ValueError/UnicodeDecodeError 捕获 L134-138）；无密钥；输出路径拒入 .governance（L2594-2614，code=family_scan_output_refused）；scan 前后 sha256 相等断言常驻（test L5396-5414）。 |
| 可维护性 | PASS（1 P2 + 2 P3） | 单一来源纪律延续（FIX-385 先例注释 L1289）；族规格/守卫/扫描器/报告职责分离；`_now_iso` 死代码（L347-348，P3）；注释子计数不可复算（L2210-2215 vs test L5341「187」回推 183，P3）。 |
| 性能 | PASS | 扫描单遍逐行 O(n)；registry 无缓存系有意设计（L139-142 注释——正确取舍）；TSV 确定性排序（L2550-2567）；无 N+1。 |
| 测试覆盖 | PASS | 22 新用例（11+11）亲读全量：四族共享语义/REQ 双向/EVD 与单元一逐行一致（L5384-5392）/只读 sha256/TSV 确定性/输出拒绝/写边界全入口/EVD 既有路径保持/CLI 拒绝与 scan；例外四态+畸形+错作用域+惰性+渲染后缀+字节级向后兼容+release 披露不翻 verdict。test_archive `def test_` 计 170（grep 171 含 1 条 class 行）=档称 170/170 静态印证。 |

## 2. Findings

| # | 级别 | 位置 | 问题 | 修复建议 |
|---|---|---|---|---|
| F-1 | **P1** | feat-075-four-family-dryrun-20260928.md §3（L60-74） | **495→708 双向归因算术不闭合**：解锁 238（REQ 74+FEAT 154+FX 10）− 收紧 119（duplicate 56+oor 24/unparseable 26/keep 5/active 8）= +119 行/+129,739 B，仅解释实际偏差 +213 行/+167,575 B 的 56%（行）/77%（字节）；**残余 +94 行/+37,836 B 无任何方向行承载**（字节：263,163+187,753−58,014=392,902≠430,738）。且 L60 headline「偏差全部可由…双向解释」与「495 行中无一行被证伪为判可迁实不可迁」同表内收紧面 119 行（估算判可过→六条件阻塞）措辞自相矛盾。plan-tracker L84 验收条件明列「495 行估算逐条原因差异解释」——方向分解不闭合即不满足验收字面。最可能缺列的第三方向=估算仅按关联任务列判可解析（盘点 L141），而扫描器门控=ID 内嵌任务∪关联列（archive.py L2281）——嵌入任务可解析而列空/非任务的行 est-excluded→measured-migratable。 | 用已入库 `scan-families --report-json` 对逐行 TSV 机械分解补第三方向行（或如实改 headline 为「主要方向+未闭合残余 94 行/37,836B」）；同步修正「无一行被证伪」措辞矛盾。**代码面零必改**（FEAT-074 R0 P1 先例同类——档级 finding）。 |
| F-2 | P2 | exception_registry.py L237+L285-296；verify_workflow.py L16629/L22459 | 注册表**文件级错误**（畸形条目/错 schema/不可读）只在 release_disclosure_block（L314-315）披露；28s 段与 `_archguard_print_findings` 两条渲染路径对 `registry["errors"]` 零呈现——作用域匹配但登记畸形的例外在这两条路径静默不标注。底层 FAIL 原样保留（fail-closed 方向未破坏），但「not effective 必披露」承诺在该两路径不完整。 | `_exception_note` 调用侧或 28s 块尾部在 `registry["errors"]` 非空时附加一行 registry-error 提示。 |
| F-3 | P3 | exception_registry.py L347-348 | `_now_iso()` 定义后全模块零调用（死代码）。 | 删除或注明保留意图。 |
| F-4 | P3 | archive.py L2210-2215 注释 vs test_archive.py L5341 | live 子计数不可复算：模块注释 404 plain+42 scope+4 malformed，按总数 633 回推 no-round=183≠测试注释「live: 187」（差恰=malformed 4，疑误含或早时点数）。 | 勘正其一。 |
| F-5 | P3 | archive.py L2253-2261（`_split_ref_ids`） | token 语法部分匹配即收整 token（live 实证：TRIAGE-FIX-302 受损列「FIX-3更控制」整体入 refs→missing fail-closed 拦截，方向安全）。继承单元一既有语法面，非新漂移。 | 无需本票修改；记录为与单元一一致的已知模糊性。 |

## 3. 审查重点 1-8 逐项结论

1. **分类核零漂移：过**（构造性证明 L2466 EVD 直调 + 共享 typer/序无平行实现；live 字节级交叉：EVD 全窗 204/642,749 与 FEAT-074 §2.1 after 精确一致、副窗 192/611,147 精确一致）。
2. **写边界完备性：过**——五入口亲数 + default-deny + 委托链纵深 + rollback EVD-only 过滤器 + 无第六入口；不论 dry_run 一律拒绝；payload code 可解释，CLI 捕获打印 payload exit 1（L5370-5375）。
3. **例外 fail-closed：过**（schema 亲读；四态+artifact_missing；有效→标注、过期/超界/状态不匹配/缺登记→不生效且披露；底层 severity/bytes/summary/exit 不变——测试断言亲读 L22439-22444/L22535-2236/L22556/L22590-22592；无注册表=惰性且输出逐字节一致——exceptions.json 当前不存在亲证 + L22538-22549 字节级断言）。
4. **聚合层接线：过**（三处亲证：共享渲染器 L22459-22461 后缀+rstrip；Check 28s 段 L16629-16631；check-release L7456-7464 仅存在的 registry 加 details 键、永不触 issues）；延迟导入保 R6（L1109/L1118 函数体内，模块级零新增 import）。
5. **四族 dry-run：过**（schema/门控并集见维度表；覆盖对账 2,922=1,477+9+1,436 独立复算 ✓；malformed 14=REVIEW 4+EVD 10 显式；§2.1 四族 reason 行/字节加总全部独立复算闭合——486/633/199/159 与 1,170,274/488,744/66,300/53,013 逐项 ✓）。
6. **495 复核表：不闭合**（F-1；时点漂移披露本身合格——985→991 行 +6 与 ±桶披露在档）。
7. **MUST NOT 红线：全过**——三族写迁移零执行（守卫外无旁路）；热冷读取切换零变更；loop_migration 契约零变更（零 FEAT-075/row_family 标记）；28s 语义零变更（例外≠语义切换）；零抬阈缩窗。
8. **AI 专项 5 项**：mock 残留 0；硬编码 0（live 数字带 sha256 锚）；幻觉 API 0（stdlib-only 亲证）；未实现 TODO 0；过度实现 0（无未经裁决的迁移执行能力——显式拒绝而非实现；owner/recheck_on 字段对应 DEC-278(5) 问责要件）。

## 4. 数字一致性抽样

- 四族行数 grep 定谳：EVD **486** / REVIEW **633** / TRIAGE **199** / RECO **159**（合计 1,477 ✓）。
- evidence-log 现态 2,921 物理行 = 档输入态（2,922 split 元素口径）——扫描后无追加行，输入锚自洽。
- §2.2 副窗 708/430,738=459+139+110 与 347,814+46,438+36,486 ✓；§3 含义行 708~722/430,738~435,281 复算 ✓；「纯 FEAT/FX 门控行 164」=154+10 子集行自洽 ✓。
- 与 FEAT-074 档交叉：EVD 两窗字节级精确一致（§2.4 声明成立）；oor 11 vs 9、行 486 vs 484 差=在途 EVD-1225/1226（L2920-2921 亲证）与时点漂移披露吻合。

## 5. 硬门槛自检

- [x] P0 阻塞数 = 0（F-1 为 P1 档级）
- [x] 5 维度全覆盖（100%）
- [x] 每条发现标注级别（F-1~F-5）
- [x] 设计一致性（vs DEC-278 §3.1 四项交付全落位；§3.2 七红线全过）
- [x] AI 专项 5 项全部完成
- [x] 只读纪律：零写入/零命令/零子 agent/零用户交互
- [x] 事实锚定：每条 finding 与通过结论均带文件+行号或独立复算

## 6. 终态结论

**NEEDS_CHANGE**（阻塞 finding：F-1〔P1，验收档算术不闭合——代码面零必改〕）。返工建议：仅勘正 feat-075 落档 §3（补第三方向行或改写 headline+残余数字+措辞矛盾），可用已入库 scan-families 逐行 TSV 机械分解；F-2 建议（非阻塞）可顺带。返工后按 M7.4 spawn 同一 Code Reviewer 复审 R1。F-3/F-4 类 P3 可顺带或遗留。产品代码无必改项——五守卫、fail-closed 四态、三接线、只读契约、向后兼容字节级惰性均亲证通过。

## 证据清单

1. archive.py：L1143-1149/L1581-1658/L1661-1836/L1739/L2187-2250/L2253-2371/L2389-2547/L2550-2621/L1893·L2678·L3079·L4916·L5351（五守卫）/L4399-4416/L5253-5451
2. verify_workflow.py：L164/L1102-1119/L7456-7464/L16613-16634/L22439-22465
3. exception_registry.py 全文 348 行亲读
4. test_archive.py L5229-5515；test_verify_workflow.py L22362-22605 + L22039
5. live 静态印证：evidence-log.md grep 定谳四族行数；总行 2,921；L2920-2921；L1146；L1793；`.governance/exceptions.json` 不存在（惰性面亲证）
6. 档间交叉：feat-075 档 §2.1/§2.2/§2.3/§3 全部数字独立复算（§2 全闭合；§3 不闭合=F-1）；FEAT-074 档两窗一致；盘点档 §2.3 L134-141（F-1 第三方向假说的文本依据）+ §1.4
7. 边界面：core/manifest.json L154（infra/ 为 canonical dir）；checks/manifest.py L391-448；loop_migration.py 零 FEAT-075 标记

## 遗留不确定项

1. `_make_ref_verdict`「verbatim 抽取」未能 git 对照（角色禁命令）——可由 Coordinator 侧 `git diff c90768f` 定谳；现有构造性+字节级证据已强
2. live sha256/字节量锚采信（行数与四族计数已独立印证）
3. Developer 测试声明（R5 97/97、R2-R6 PASS、19F+1E stash 对跑=HEAD 既有）采信；方法与 FEAT-074 R0 同构
4. F-1 第三方向假说（估算列-only vs 扫描器嵌入∪列）未经行级验证——返工时用 scan-families 逐行输出机械分解定谳
5. 测试注释「no-round live: 187」vs 回推 183 的 4 行差（F-4）——返工顺手定谳
