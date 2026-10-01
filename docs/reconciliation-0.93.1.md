# 0.93.1 收尾对账报告（Reconciliation Ledger）

> 状态：**草稿（随收尾进度更新）**——终态版随 REL-097 M-8 发布。
> 口径：arch 顾问元裁决三态——**已修复**（缺陷真实消除）/ **历史已对账**（不可逆历史事实，来源与处置已核实）/ **裁定闭环**（用户决策前提移除式关闭，非证据式）。
> 授权链：用户 2026-09-30 授权令（0.93.1 M-0）+ 范围裁定（1.0.0 暂缓/官方提交暂缓）+ arch 顾问 D1-D7 裁决集。

## 一、已修复（本轮会话）

| # | 项 | 处置 | 证据锚 |
|---|---|---|---|
| 1 | 28c 热事实三面（REL-096 行翻转/roadmap taggerdate 回填/发布链终态） | 治理回写 | EVD-1273；plan-tracker |
| 2 | REL-096 收口清单①②③ | DACL+残留清理+三验证 | EVD-1273；WRITE_PROBE=PASS |
| 3 | FIX-414 测试期望与 FIX-413 契约错配（released 复跑 1F） | 测试对齐 | commit 65cf188；EVD-1274；R0 AWN/0 |
| 4 | FIX-415 HotFact 16F+1F cwd 耦合（HOST_PROJECT_ROOT import 绑定+plugin-scope 门） | 测试钉根+SD 虚构化 | commit fe0afcb；EVD-1275；R0 AWN/0 |
| 5 | FIX-416 归档永续红（CLI --row-family 默认与 ALL 口径脱钩+守卫误拒 ALL+消息误导）+ regen rider | CLI 口径对齐+再锚 | commit 2fa1ebd；EVD-1276；R0 AWN/0；DEC（migrate --auto 默认 ALL） |
| 6 | 归档两轮+衍生清扫（7 task+28 EVD+26 家族行+1 风险行） | migrate --auto（用户确认×2+裁定衍生） | check-archive-integrity [PASS] |
| 7 | Check 5 EVD-1245（8 格） | 全角 ｜ 结构归一（内容零变化） | 管道 9→10 实测 |
| 8 | Check 31 ragged（本会话两次手术回归） | 全表 44 行管道审计归零 | mismatch=0 审计输出 |
| 9 | Check 34 完成必推荐缺（414/415/416） | RECO 机录×3 | tpa --evidence-task |
| 10 | Check 18c 族（缺包） | execution-packet×3+契约填充 | packets json |
| 11 | 28q release_docs_versions | ~~docs 归档子目录化~~ **路径否证已回退**（commit 7d6c4a7——claim-gate 会计注册表锚原路径，触发 31/28m FAIL×4）；改走 FIX-419 阈值重校准（arch D4 政策口径：30→100+增长预算+rationale） | 见 FIX-419 |
| 12 | 28q hooks_drift（prepare-commit-msg） | 重装 | .git/hooks 面复验 |
| 13 | Check 2/8 风险逾期+陈旧 | 见「裁定闭环/复评」 | risk-log |

## 二、进行中（0.93.1 载荷）

| 项 | 状态 |
|---|---|
| FIX-417（28n 拆分 6016→4241+7 函数分解） | ✅ commit `b12eee1`；EVD-1282；R0 AWN/0 |
| FIX-418（infra-cwd 11F 根治——双 cwd 4591/4591） | ✅ commit `693fea8`；EVD-1283；R0 AWN/0 |
| 417/418 契约 status 收口 | ✅ 真 PASS 证据回填（4577P/4591×2+等价性） |
| REL-097 M-1~M-8 | 🔄 M-1 组装完成（27 面 staged）；M-2/M-3 在途 |

## 三、历史已对账（不可逆历史事实——不伪造补写）

| # | 项 | 对账结论 |
|---|---|---|
| 1 | Check 13 DEC-ID 间隙 [3,24,141,142,178] | 历史缺口（前纪元分配/撤销痕迹）——不可凭空补造 DEC；逐个有权威记录则恢复、否则记核实缺口（arch D3 纪律）〔终态版附逐个核查表〕 |
| 2 | Check 30c V7 ×2（REVIEW-FIX-256/258 手写行） | 前 CLI 纪元手写事实——机器标记不可补写；当前复核引用在案（M7.4 step 4.6 演进史） |
| 3 | Check 30 closure WARN ×13 | 历史降级族（FIX-233/413 语义下已对账的行）——逐条终态版列表 |
| 4 | Check 14 结构面 ~187 条（0 blocking） | 0-blocking 历史形态（列宽/分隔符/装饰日期族）——逐项分类终态版呈现；不改写历史行 |
| 5 | 28s evidence 495K | DEC-295① track-1 用户裁定校准（2026-09-29：稳态基准 515KB 实测+wobble 余量；warn 400K/error 650K）；现值在校准稳态内=设计内预警，不追当前值再校准（arch D4） |
| 6 | 28s tracker 200.4K | 窗口工作集——0.93.1 M-8 归档窗收敛（历史规律：发布后下窗迁移） |
| 7 | RB2 demo 契约 WARN（'release 0.90.0' BLOCK 判定/enforcement off） | 设计内负例夹具（_RB2_DEMO_SENSITIVE_ACTION 常量+专属测试三例）——授权票翻转前 enforcement off 为设计语义（arch：不为消警开启 enforcement/不改 BLOCK 为 ALLOW） |

## 四、裁定闭环（用户决策——非证据式）

| # | 项 | 裁定 | 依据 |
|---|---|---|---|
| 1 | RISK-036（官方收录与市场采用准备不足） | **关闭**（前提移除：官方提交暂缓；恢复提交时重开） | 用户 2026-09-30 裁定+DEC op-7e0ee372 |
| 2 | 1.0.0 外部验证前置族 | **暂缓**（1.0.0 不发布；用户声明存在大量未登记需求待登记） | 用户裁定 |

## 五、复评维持打开（实质复评——关闭标准未满足者如实保留）

| # | 风险 | 复评结论 | 下次复评 |
|---|---|---|---|
| 1 | RISK-039（架构腐化看护） | 维持打开（域拆分零进展+外部宿主验证缺）；正向新证：ArchGuard 棘轮活体执法+0.93.1 D1 首获承载 | 0.93.1 发布后 |
| 2 | RISK-050（dsh 上游耦合） | 维持打开（收口差升级演练明细）；0.93.1 载荷零 adapters 触碰实证 | 2026-10-31 窗 |

## 六、审查遗留小项（0.93.1 承载/披露）

- FIX-415-R0 F-1/F-2 注释修正（处置=并入 FIX-416 顺手修；FIX-416-R0 自身编号 P2-1~P3-3）：✅ 已随 FIX-416 落地
- F-3（SD 测试 stdout 消音）/P2-1（preview 口径标注）/P2-2（migratable_total 单源）/P3-2（范围+ALL 组合断言）/P3-3（EOF 空行）/archive.py L2465 docstring：0.93.x 候选披露（零行为面，不阻发布）
- FIX-415 边缘 2（hot-fact API scope 从传入 path 派生）：0.94 候选（产品语义变更需独立立项）


### 六-补：已审发现披露（REL-097-R1 F-2 补遗——staged 窗口闭环）

- FIX-418-R0 F-2（P2）：feat014/fix270 的 facts 钉向真实 dogfood .governance——「零行为变化」形态固有取舍（与绿基线同读取面）；合成 fixture 超 arch D2 最小类修范围——0.94 候选
- FIX-416-R0 P3-1：version.py 归因表述简化（无行为面）
- FIX-418-R0 F-3：FEAT-080 派生使 B3 fixture 版本不可知（DEC-213③ 认可形态——消除 bump 时 ledger 漂移，有意为之）
- FIX-417-R0 F3：archive.py sibling import 的 sys.path 打包约束（当前全部加载方已核实满足；新增远端加载方需先保证 sys.path——docstring 已披露）
- 28n 其他模块 WARN（来源=check-governance strict 2026-10-01 实测输出，非 R0 报告产物）：closure_chain.py 3672+_run_probe/_run_locked、governance_store.py 2694+_decision_append_json、dsh_compat.py 2165、loop_gate_processor.py process_gate_result——既有技术债披露，arch D1 明确不在 FIX-417 范围——0.94 候选
## 七、终态验证矩阵（发布门槛——arch D7）

| 层面 | 放行条件 | 状态 |
|---|---|---|
| 测试 | 双 cwd 独立新进程全席 0F+收集集一致+无未批准 skip | ⏳ 待 417/418 |
| 治理 | strict 0 FAIL；可修 WARN 全修；历史对账/开放风险另行可见 | ⏳ |
| 归档 | integrity PASS+迁移/恢复/幂等回归 | ✅（持续复验） |
| 行为安全 | CLI/路径/权限/敏感动作拦截契约零退化 | ⏳ 随审查 |
| 受管数据 | schema/锚/引用/生成物一致 | ✅ write-guard PASS |
| 发布 | check-release 0.93.1 全 PASS；M-0~M-8 完整 | ⏳ |
| 可追溯 | 被测 SHA=tag=ledger | ⏳ |
| 回退 | 代码回退与数据恢复分别明确 | ✅ rollback-plan-0.93.1.md（六 commit revert 序列+数据面说明） |
