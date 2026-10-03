# Review Record: REL-098 — M-3a 版本面组装审查（CODE，R0）

- **Task**: REL-098（M-3a——发布链双审第一面；第二面 Release Reviewer 发布门禁由 Coordinator 于 M-2 完成后派发）
- **Reviewer**: Code Reviewer Agent（角色定义 + code-review SKILL 已加载并遵循；只读）
- **对象**: 0.94.0 版本面组装（24 M + 4 A + gitignored 根 CLAUDE.md = 28 追踪面 + 1 工作树面），diff 工件 docs/reviews/REL-098-M1-R0.diff（397 行逐行读完）
- **日期**: 2026-10-03 · **Round**: R0
- **结论**: **APPROVED_WITH_NOTES**（unresolved_blockers = 0）· P0=0 / P1=0 / P2=0 / P3=3

## 硬门槛自检

P0 阻塞=0 ✅ · 5 维度 100% 覆盖 ✅ · 发现全标级 ✅ · 设计一致性检查（062414e 先例 + FIX-011/349/361 + AUDIT-082）✅ · AI 专项 5 项 ✅

## 逐项核验结果（独立核实，非采信自报）

**1. 权威源与投影 17 面**：SKILL.md frontmatter 0.94.0（根/e2e blob 同 hash = byte-identical 实证）；投影注册表 353 行全读：28 registry 面 = 17 本批实写 + 11 幂等镜像——与「written=17 / sd_integrity 28 scanned」自报完全吻合。

**2. 双根 entry sync ×4**：根 AGENTS.md / e2e AGENTS+CLAUDE tracked 面确认；gitignored 根 CLAUDE.md 工作树实读 L5 = `@bootstrap-version: 0.94.0` ✓（AUDIT-082 口径）。commands/governance-init.md ×3 与 e2e 镜像同步——FIX-011 canonical 纪律遵守。

**3. 版本一致性独立 grep**：全仓 0.93.1 命中 110 处 / 18 文件逐文件裁决——活跃版本声明面**零残留**；17 文件历史性正当保留 + 第 18 个为本 diff 工件自身。@bootstrap-version 全部活跃 marker 实测 0.94.0。

**4. 引擎锚**：REQUIRED_SNIPPETS 六针脚 0.94.0（L1057-1072 实读恰 6 处）；STATIC_PIN_EXEMPTIONS +2 行宿主为 tests/test_verify_workflow.py L20573/L20576——实读确认恰为 FEAT-081 `_TRACKER_SEED`/`_TRACKER_DEFERRED_ROW` 目标版本单元格——**豁免精确锚定，非越权**；与历代 bump-time 登记同构（FIX-361）。skills/ 下 0.94.0 token 19 处逐一归位。

**5. CHANGELOG 载荷十票**：Added×3 + Changed×1 + Fixed×6 全在场分类正确；对照 plan-tracker L80-89 十行任务一一对应；决策链/证据/EVD 抽验 7/14 全部实存吻合；载荷窗口 `84f8819..af7cfbd` git 实测 11 commits 与 rollback plan 枚举逐一吻合；HEAD=af7cfbd、v0.93.1-13-gaf7cfbd。

**6. 发布四件套实质**：checklist 60 行 / rollback 45 行（可执行回滚序列 + 依赖闭链警告）/ flags 28 行 / reconciliation 80 行——非空壳；引用工具实存。

**7. e2e fixture 边界**：恰为注册表既定面，diff hunk 全部仅版本行，零测试语义改动。

## 5 维度结论

正确性 ✅（单调 bump 零遗漏零冲突；byte_copy blob 同 hash；三源一致）· 安全性 ✅（纯元数据/文档/字面量批次）· 可维护性 ✅（单源投影纪律保持；四件套同量级沿模板）· 性能 ✅（零运行时逻辑改动）· 测试覆盖 ✅（动态断言面静态一致；全量复跑归 M-2）

## AI 代码专项 5 项

mock 残留：无 · 硬编码返回值：无新增风险（版本字面量即设计内 pin）· 幻觉 API：无（引用全实存）· 未实现 TODO：无 · 过度实现：无（git status 逐文件对账恰为申报 28+1 面）

## 设计一致性（先例 062414e / REL-097）

27 面先例与本批 28 面**逐面同构**，唯一增量 = version.py（FEAT-081 双信号依据正当）。FIX-011 ✓ · FIX-349 ✓ · FIX-361 ✓ · AUDIT-082 ✓。

## 发现列表（全 P3，非阻塞）

- **F-1（P3）** contract_matrix/golden_samples.txt:1296-1352——0.93.1 期 snippet 事实为 bump 前时点捕获，本批未再生成。建议 M-8 收口时 `generator.py --golden` 再生成。零门禁影响。
- **F-2（P3）** CHANGELOG 0.94.0「版本面再生纪律」段未按 0.85~0.89 先例披露 bump-time 登记（一句之差；豁免事实已在 version.py + M-1 申报面披露无信息缺失）。建议随 M-8 补记或维持。
- **F-3（P3·信息性）** plan-tracker 总览行叙述「当前活跃版本 0.93.1」vs 工作流版本单元格 0.94.0——M-1 提前写回的良性偏离已自文档化；总览叙述留待 M-8 刷新属既定惯例。

## 验证边界（诚实声明）

Developer 自报运行时验证按声称对待，未独立复跑（全量复跑为 M-2 执行门职责）。本审查独立完成全部静态可核实面（diff 逐行 / 工作树抽样含 gitignored 与 4 新文件 / 全仓双版本 grep 逐文件裁决 / 豁免行宿主实读 / 注册表全读 / git 窗口机验 / 十票对照 / EVD 抽验 7/14）——静态面与自报零矛盾。

**终态：APPROVED_WITH_NOTES（unresolved_blockers = 0）**——版本面可进入 M-2 门禁与 M-3b 发布门禁审查。
