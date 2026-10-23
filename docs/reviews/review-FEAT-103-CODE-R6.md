# REVIEW-FEAT-103-CODE-R6 — M5 终态批 + T09+ 修复微批独立复审

- 日期：2026-10-23（Asia/Shanghai；命令时刻均 UTC）
- **结论：APPROVED_WITH_NOTES**
- **unresolved_blockers=0**
- P0=0，P1=0，P2=0，P3=2
- Reviewer：Code Reviewer（R12 同链新实例；机录链 round 14）。指令隔离：本轮未收到任何来自其他 agent 的转包/委派/验收请求（通信异常：无）。
- 审查对象：副本 controller 修复（+9/−0）+ t-m5 三用例（前任产物）+ M5-REPORT/M5-TEST-AUDIT + m5-audit/
- 只写本报告 + scratch `.codex-sandbox/FEAT-103/review-code-r6/`（含三环境 t-m5 审计 JSON）；未改任何被审对象；未 stage/commit/push；未启动宿主；DSH_HOME 全程隔离重定向 `.governance/sandboxes/feat103-r6-review-20261023`。

## 1. 对象绑定（独立复算）

### 1.1 副本七文件

| 文件 | SHA-256（首8） | 行数 | 判定 |
| --- | --- | ---: | --- |
| session-controller `lib/index.js` | `24E3C2F4`（…34030830） | 3429 | 修复后（基线 B9999EE6/3420L，**+9/−0**） |
| registry `lib/index.js` | `5ABBA552` | 1280 | = M3 后基线 ✅ |
| registry `lib/types/index.d.ts` | `1B2E6C26` | 232 | 同上 ✅ |
| subagent `lib/index.js` | `16E9F593` | 3386 | = M3 后基线 ✅ |
| subagent `lib/types/child-agent.d.ts` | `2C4B6731` | 158 | 同上 ✅ |
| core/agent `lib/types/index.d.ts` | `0855B0E5` | 387 | = M1 起基线 ✅ |
| core/agent-loop `lib/index.js` | `0C0C589F` | 2036 | = M2 起基线 ✅ |

### 1.2 安装态七文件（只读）

`95EDCC66` / `52251982` / `A9801ACB` / `35318991` / `CF57E3EC` / `9A9572E7` / `F885F282` — 全部与 R10/R12 基线逐位一致，零写入 ✅（审查前后两次核对）。

### 1.3 测试与报告

| 对象 | SHA-256 | 备注 |
| --- | --- | --- |
| `tests/t-m5-final-closure.mjs` | `AC7FB101…A381867`（248 行） | 前任产物；复跑前后 SHA 不变（Reviewer 未改） |
| `M5-REPORT.md`（138 行）/ `M5-TEST-AUDIT.md`（37 行） | — | 报告声明与亲读逐项一致（§3） |

## 2. T09+ 修复亲读核验（核心）

### 2.1 短路块（controller :467-475，+9/−0）

- **位置**：claim live 分支内、cwd 冲突检查（:466）之后、composeAgent（:476）之前——先于 resolve 拒收源 ✅
- **条件四元组逐条语义**：`request.agentPreset !== void 0`（显式指定才短路）&& `request.reusable(live.id)`（复用判定）&& `this.isBlank(live.session)`（blank 会话）&& `this.presetForSession(live.session) === request.agentPreset`（live 现行 preset 与请求同一）——与设计 §5.3 #2/§8 T09+「live 同 preset → 复用成功且 P=0」语义精确对应 ✅
- **与 reuseLive（:521-527）同构性亲读成立**：reuseLive 入口 `!reusable || !isBlank → undefined`（:522）+ `assertPresetApplicable`（:523）+ `current===target → return live`（:527，target 来自 composeAgent 解析、解析成功时恒等于请求 id）——短路块取同一组条件并直接以请求 id 替代解析产物，**唯一行为差别 = 跳过 composeAgent→resolve**（正是 closed 拒收源）；resolve 成功场景的原路径 :476-477 逐字保留，行为不变 ✅
- **assertPresetApplicable 不破坏短路**（:560-563 亲读）：仅检查 roster 存在性（`ctx.get("agentPresets")`），**不 resolve**——closed 状态（registry 状态而非 roster 缺失）不触发 `ApiSessionPresetConflict` ✅
- **缺省边界**：`agentPreset === undefined` 不短路 → composeAgent default 解析（注释 :471 明示）；live 无 preset 投影（undefined ≠ 显式 id）不短路 → 改选面 ✅

### 2.2 M5-1 归因链独立验证（成立）

1. composeAgent :351-365 亲读：:360 `const resolvedId = (await presets.resolve(presetId)).id` 无守卫；:356-359 保护意图注释逐字确认（M2 只防了 acquire 半边："Acquiring here would reject the zero-factory live-reuse path… and leak a token"——resolve 面对 closed 同样拒收）✅
2. registry resolve :860（亲读 grep 锚定）：`definitions.get(wanted) === undefined → RemoteError("agent-preset/not-found", "Unknown agent preset: …")`——owned close→`_forget` 清主表后 resolve 必然 not-found（§3.3 已批语义）✅
3. reuseLive :518 短路本身正确（M5-2 spy 探针 PASS 精确证明）——修复前失败被隔离在 resolve 面 ✅
4. **非回归**：ctrl-prefix（安装态原版 controller）同场景同一错误 FAIL（本审查独立复现，§4 #2）——T09+ closed 变体合同自始未被任何版本实现，非 FEAT-103 补丁回归 ✅
5. registry 非缺陷：resolve 对 closed 返回 not-found 是已批合同（§5.6 分类）；修复面在 controller 正确 ✅

## 3. 独立复跑（UTC 2026-10-23T00:00:25.582Z→00:00:39.880Z）

| # | 命令 | exit | 实数 |
| --- | --- | ---: | --- |
| 1 | t-m5 权威轮（副本双端） | **0** | **3/3 PASS**（M5-1 转正：`out===live` + `acquireCalls===0`） |
| 2 | t-m5 @ctrl-prefix（FEAT103_CONTROLLER=安装态 controller） | **1** | **2/1**：M5-1 FAIL `RemoteError: Unknown agent preset: g1`（同错误——**安装态原版缺口未动=修复非空转铁证**）；M5-2/M5-3 PASS |
| 3 | t-m5 @reg-prefix（FEAT103_REG_MODULE=安装态 registry） | **1** | **2/1**：M5-1 FAIL `beginRegistration is not a function`（owned API=补丁面，安装态无此 API，构造失败符合预期）；M5-3 PASS（legacy 原行为一致） |
| 4 | B `t-m3-child-selector.mjs` | 0 | 12/12 |
| 5 | A `t-m2-registry-admission.mjs` | 0 | 12/12 |
| 6 | C `t-m2-controller-branches.mjs` | 0 | 14/14 |
| 7 | d1 `t-m2-d1-wiring.mjs` | 0 | 10/10 |
| 8 | M4 `t-m4-contract-closure.mjs` | 0 | 6/6 |
| 9 | T01（仓库根口径 `.codex-sandbox/FEAT-103/tests/`） | 0 | 9/9（stdout JSON total 9/passed 9/failed 0） |

- 九条与 Developer 审计（M5-TEST-AUDIT #13-#21）**逐字一致**；预期失败保持失败，无重跑至绿。
- t-m5 断言未弱化核验：M5-1 断言原文（`out === live` / `acquireCalls === 0`，:173-174）与修复前 FAIL 轮为同一断言——测试不变、实现补齐；M5-2 acquire 陷阱计数（:195）、M5-3 六断言组（:206-230）均真实观测。

## 4. Findings

### P3

**R6-P3-1 — t-m5 文件头设计锚点版本引用滞后**
- `t-m5-final-closure.mjs:8` 写 "R6 D8DE745C, 566L"；设计已至 R7（DDF7875E，591L）且 Architect 最终回写在途。合同句 §5.3 #2 / §8 T09+ 语义跨版本未变（R7 亲读核对），断言不受影响。建议：合入前顺带更新头注释锚点版本（或按"落笔时点基线"口径接受）。

**R6-P3-2 — M5-REPORT §2.1 归因段行号为修复前基线口径，未全局标注**
- 归因链第 2 步引用 ":467 composeAgent" 等——基线 B9999EE6 口径；修复 +9 后该调用现为 :476。修复段已自带新行号，但归因段行号缺"基线口径"总注（仅在 §1.1 表内可推断）。纯文本精度项，不影响复核（本报告以当前文本+基线差分双重锚定）。

## 5. NOT_RUN 确认（无冒充）

真实 host boot/publish 链；物理 storage 注入（M4-5 fixture 不含 AgentLoop scope 回滚）；startActivation 全链；T10 census 全量面；0.1.x。T09+ closed 变体已由本批修复闭环（M5-REPORT §4 删除线标注+建议 Architect 移除 §16 C-1 行）——与本审查独立观测一致。

## 6. 边界合规（Reviewer 侧）

- 只写 `docs/reviews/review-FEAT-103-CODE-R6.md` + scratch `review-code-r6/`（三环境审计 JSON 已落盘：`r6-m5-authoritative.json` / `r6-m5-ctrl-prefix.json` / `r6-m5-reg-prefix.json`）
- 安装态 SDK 只读（七文件审查前后两次 SHA 一致）；node 进程内 Cordis；DSH_HOME 隔离重定向；无宿主进程；未读写真实 `~/.dsh`
- `git status --porcelain -uno` 仅既有暂停 WIP 两行（hooks/commit-msg、test_hooks.py）；`git diff --cached` 空；HEAD `2ed8bb4`
- t-m5 SHA 复跑前后不变（AC7FB101…）；副本七文件复算与对象绑定一致

**结论：APPROVED_WITH_NOTES，unresolved_blockers=0。** T09+ 修复（+9/−0 同构短路）经亲读+九条独立复跑+非空转对照三重验证；M5-1 归因链（实现缺口非回归）独立成立；两项 P3 为文本精度项，不阻断合入判定。
