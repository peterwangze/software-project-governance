<!-- review-record: task=FIX-324+FIX-326 reviewer=code-reviewer round=R0 verdict=APPROVED_WITH_NOTES unresolved_blockers=0 -->

# review-FIX-324-326-CODE-R0 — 产品代码面合并审查（REL-078 M-0 prep 并入项路由补审）

- **审查对象**：暂存区（基线 HEAD `845c050`，实测一致）中 3 文件的产品面增量：
  1. `adapters/dsh/adapter-manifest.json`（native_entry.note +1 句，FIX-326①）
  2. `adapters/dsh/host-contract.json`（3 处 note：L34 evidence.note / L38 dsh_cli_version_current_measurement / L860 recorded_slice，FIX-326③）
  3. `skills/software-project-governance/infra/tests/test_change_triage.py`（+15/−1，日期炸弹修复，REL-078 prep）
- **审查者**：Code Reviewer（只读审查 + 验证性命令；未修改任何产品代码）
- **审查日期**：2026-09-17（当日真实时钟 > 旧钉死日期 2026-09-10，红→绿在未修改的真实时钟上天然成立）

## 结论：APPROVED_WITH_NOTES（unresolved_blockers=0）

P0 = 0，P1 = 0；3 条 P3 级备注（见 findings），均不阻塞合并。

---

## 硬门槛独立复现（全部从仓库根运行，本审查者亲自执行）

| 门槛项 | 声明 | 独立复现结果 | 裁决 |
|---|---|---|---|
| test_dsh_adapter | 53 OK | `python -m pytest .../test_dsh_adapter.py -q` → **53 passed** (12.97s) | ✅ 一致 |
| test_dsh_contract | 120 OK | `python -m pytest .../test_dsh_contract.py -q` → **120 passed** (4.17s) | ✅ 一致 |
| test_change_triage | 93 OK | `python -m pytest .../test_change_triage.py -q` → **93 passed** (16.06s) | ✅ 一致（含被修复用例，真实时钟 2026-09-17） |
| check-agent-adapters | OK | → `[OK] agent adapter contracts synchronized`，dsh adapter runtime-verified，exit 0 | ✅ |
| Check 28w（check-dsh-boundary） | K-12 PASS | → Result: PASS，0 failing；**K-12 PASS**，其 PASS 理由原文即「the doctor command key `dsh-doctor` is registered, so the verdict comparison has a subject」 | ✅（K-12 判据直接消费 manifest +1 句） |
| 契约 SHA 复算 | 96F92485…→63B28311…28DF2（75331 bytes） | `git cat-file blob` 双 blob 字节导出 + SHA-256：HEAD `96F9248579FC…43FC6E`（74702 B）、staged `63B28311330D…53228DF2`（**75331 B**） | ✅ 前后缀与字节数精确一致 |
| 契约变更面 = 恰 3 note | 无其他字节变化 | `git diff --cached` 完整差异 = 3 个 hunk、3 行 −/+，全部位于 note 字符串内；由此推论 `recording.writer` 字段与钉扎测试（test_dsh_contract.py 不在暂存清单）未动 | ✅ |
| 时钟注入 2027/2030 | 双点任意日期绿 | 独立 harness（仓库外 %TEMP%，经生产函数 `acquire_dispatch_locks` 的 `now` 注入缝——CLI 子进程即调此函数、传 now=None）：INJECT-2027 `written=True warn=YES`、INJECT-2030 `written=True warn=YES`、阴性对照 BOMB-REPRO（旧钉死 2026-09-10 + 注入时钟 2027-06-01）`written=True warn=NO` | ✅ 修复形状任意日期 WARN 照常披露；旧弹形状 WARN 静默缺失（红机制复现 + harness 有效性双证） |

## 审查重点逐项

### 1. manifest note 语义准确性（对照 dsh_doctor.py 实现与 DEC-193）——PASS

+1 句声称的四个事实全部与实现吻合：

| note 声称 | 实现事实（文件:行） |
|---|---|
| `python …/verify_workflow.py dsh-doctor` 诊断入口 | 子命令已注册：`verify_workflow.py:23817-23819`（parser）+ `:24403`（分发表）；引擎路由 `cmd_dsh_doctor`（`:21295-21333`）不吞退出码 |
| stages S0-S7 | `dsh_doctor.py:105-114` `STAGES` 恰 8 项 S0…S7 |
| four switches | 4 个互斥入口模式（默认 S0–S7 / `--selftest` / `--record-evidence` / `--rehearse`，`main()` `:1882-1889`）；「four switches」措辞与引擎路由 docstring 自有词汇一致（`verify_workflow.py:21298-21299`） |
| exit codes 0/1/2 | `dsh_doctor.py:100-102` EXIT_OK=0 / EXIT_FAIL=1 / EXIT_REFUSED=2（模块 docstring §5.1 对齐 SMOKE_EXIT_*） |
| per-stage crash isolation → NOT_RUN | `:1198-1200` `_crashed`：崩溃阶段 NOT_RUN + stage_error，其余继续；自测 `--selftest` 逐阶段断言隔离规则 |

设计边界核对：设计 §2.9.4（`docs/requirements/dsh-compat-design-0.81.0.md:293`）明列 manifest 登记面 = `native_entry.note` 或 `validation` 段、「本版不扩面，只加一行」——本改动为 note 追加一句（JSON 单行内 +1/−1），符合。该 +1 句同时闭环 review-FEAT-031-CODE-R0 F-13（「adapter-manifest.json 未登记 dsh-doctor」）。

### 2. 契约 note as-built 更正（对照 DEC-193 与实证）——PASS

三处 note 新措辞与 DEC-193（`decision-log.md:131`，2026-09-13）逐点一致：
- 「采集单点 = 该命令（证据采集 = 单点）」⇔ DEC-193「§2.7『证据写入 = 单点』读作『证据采集 = 单点』」✓
- 「--record-evidence 只把实测写入 factsheet」⇔ 实证 `dsh_doctor.py:47-51`（唯一写路径 = --record-evidence，只写 `--out` 指名文件）+ `record_evidence` `:1651-1661` + `:1671-1672` `FACTSHEET_NAME_RE`（任务prompt所指 L1671 实证点）✓
- 「契约内值由维护者在受审提交中回填——探针直改契约会让单一事实源未经审查地可机变（取舍 Coordinator 已裁决接受）」⇔ DEC-193 理由原文 + `_guard_out_target` `:1675-1689`（契约本体一律拒写）✓
- 「null = 未记录 ⇒ NOT_RUN」⇔ DEC-193「契约未记录时 K-7/S3 一律 NOT_RUN，绝不默认 PASS」；本次 28w 实跑中 K-7 即按此 NOT_RUN，其提示语「recording is the maintainer's reviewed-commit step」与新 note 互证 ✓
- L38 / L860 两处为同一口径在对应字段的措辞同步，无语义漂移；「读取方只读，不得自动刷新」原文保留 ✓
- `recording.writer` 字段未动（3-hunk 字节差异推论）✓

### 3. 日期修复正确性——PASS

- 机制核实：`acquire_dispatch_locks`（`change_triage.py:906-907`）`now=None` ⇒ 真实时钟；`cross_check_triage_files`（`:748-749`）`created_at != today` ⇒ None ⇒ WARN 静默（`:911-919` WARN 实由文件集不匹配产生，与日期解耦）。旧 fixture 钉死 2026-09-10，真实时钟越过即必红——与 0.81.0 Gate 10 #6 `'WARN' not found in ''` 症状吻合。
- 修复核实：`test_change_triage.py:1507` `today = datetime.now().date().isoformat()`（`datetime` 导入 L41 已存在），fixture 与 CLI 子进程（`_run_cli` `:1473-1479` 真 subprocess，`verify_workflow.py agent-locks-acquire`）共享同一时钟源；断言目标（WARN + `product/to_be_created.py`）来自文件集，语义与修复前完全保持（cross-check 语义未动，只修日期源）。
- 无同类炸弹残留：全文件 `created_at` 仅 5 处——helper 默认值（L1179/1184）仅被纯函数测试使用且显式双端传 `today`（L1194/1206/1218，日期安全），CLI 用例即本次修复处。✓
- 独立注入证明：见硬门槛表「时钟注入」行（2027/2030 双点 + 旧弹阴性对照）。

### 4. 范围纪律——PASS

暂存区 24 文件 = 3 审查对象 + 21 版本 bump 投影/发布面文件，逐一核对：5 个 plugin manifest/package.json（version 0.81.0→0.82.0）、AGENTS.md.template 与 cordis preset template（v 标记）、SKILL.md×2 + e2e 投影 + core/manifest.json（version）、hooks×4（`@version` 标记）、`core/releases/0.82.0.json`（声明性发布 ledger）、docs/release 三件套与 CHANGELOG（发布文档，其中 CHANGELOG 段与本审对象互洽）。**3 文件之外零产品逻辑改动，无本审归属外的产品面触碰。**

### 5. AI 专项 5 项——全部通过

| # | 检查 | 结论 |
|---|---|---|
| 1 | mock 残留 | 无新增 mock；被修复用例为真 subprocess + 真文件 |
| 2 | 硬编码返回值 | 修复本身即移除硬编码日期；无新增 |
| 3 | 幻觉 API | `datetime.now().date().isoformat()` 合法；manifest note 引用的命令/阶段/开关/退出码全部实现可查（见 §1 表） |
| 4 | 未实现 TODO | 无 TODO；新增注释为历史故障签名的事实性说明，与代码行为一致 |
| 5 | 过度实现 | +1 句 / 3 note / +15−1，均为声明边界内最小改动，无扩面 |

## 五维度结论

正确性 PASS（同源时钟语义正确；cross-check 语义保持）｜安全性 PASS（契约 note 实为安全属性文档化：单一事实源免于未审机变，`_guard_out_target` 强制）｜可维护性 PASS（注释解释 why + 历史签名；术语与引擎 docstring 对齐）｜性能 PASS（无算法变化）｜测试覆盖 PASS（修复用例即 WARN 端到端守卫；`now` 注入缝 + 纯函数测试已覆盖判定矩阵）。

## Findings（全部非阻塞）

| ID | 级别 | 位置 | 描述 | 建议 |
|---|---|---|---|---|
| F-1 | P3 | `test_change_triage.py:1507` | 午夜跨越残余竞态：`today` 在测试进程取时钟，子进程稍后重取——若套件恰跨越午夜，两端日期分叉 ⇒ WARN 缺失 ⇒ 该用例单点红。确定性炸弹已消除，残余为极小概率竞态，非本次引入的回归（任何「当日派生」测试形态固有） | 可留待后续：CLI 暴露 `--now` 测试缝或接受该残余；不阻塞 |
| F-2 | P3 | `adapter-manifest.json` native_entry.note | 「four switches」为引擎 docstring 专有词汇（4 个互斥入口模式）；argparse 实有 10 个旗标，按旗标计数的读者可能停顿。措辞与既有权威口径一致，不构成错误 | 可选：改为「four entry modes」；非必须 |
| F-3 | P3（观察项，非本 diff 引入） | host-contract.json evidence.* | 契约内实测值仍未记录（verified_on=null），28w 的 K-7 按设计 NOT_RUN——这是 DEC-193 下的合法 as-built 状态，非缺陷 | 0.82.0 checklist 保持该项可见：recording = 维护者受审提交步骤 |

## 产出物与验证痕迹

- 本报告：`docs/reviews/review-FIX-324-326-CODE-R0.md`
- 验证 scratch（仓库外，%TEMP%\rv-fix324-326\）：双 blob SHA 导出件 + `rv_inject_clock.py` 注入 harness（三案例输出见上表）
- 全部测试/检查命令从仓库根 `D:\AI\agent\claude\coding\project_management_workflow` 运行，exit code 逐项核对

—— Code Reviewer，R0，2026-09-17
