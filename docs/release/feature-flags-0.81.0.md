# Feature Flags — 0.81.0（REL-077）

- **状态**：**M-1 冻结**（2026-09-13）——V8（FEAT-031 `3074120`）已落地，「待 V8 回填」占位已按下述实测事实补齐（CLI / 退出码 / 阶段级崩溃隔离见 `docs/release/release-checklist-0.81.0.md` §「dsh-doctor 预检」；Check 28w 逐条结论见同文件 Gate 7 行）。
- **范围**：0.81.0 引入的**开关 / 可配置项 / 行为变更**清单。本版的设计取向是 **fail-closed 且默认安全**，故**新增开关为零**——变更是"更严的默认"，而非"需要用户打开的开关"。

## 1. 新增/变更的开关

| # | 开关 | 类型 | 默认 | 说明 |
|---|---|---|---|---|
| — | **（无新增 opt-in 开关）** | — | — | 本版**未引入**任何需要用户显式打开的开关。写入守卫（见 §2）**刻意没有 opt-in**——这是已知缺口，登记在 **FIX-324**（需补显式开关或文档同步二者之一） |

## 2. 行为变更（用户可感知 —— MUST 写入 CHANGELOG 与升级说明）

| # | 变更 | 旧行为（0.80.0） | 新行为（0.81.0） | 理由 | 影响面 |
|---|---|---|---|---|---|
| **B-1** | `--install` 对 `package.json` 缺失/不可读的处理 | `rc 0`，并把**占位版本 `"0"`** 写入 `.dsh-bundle-version` | **`rc 1` 拒绝**（消息含文件名与 `byte offset`，无栈） | 占位版本 ⇒ `lib/index.js` 每次 boot 与真实版本比对失败 ⇒ **每次启动重建预设**，摧毁幂等标记的语义 | 仅当 `package.json` 缺失/非 UTF-8/无 `version` 字段时触发（正常发布包不受影响） |
| **B-2** | `--install` / `--sync` / `--uninstall` 在**真实 home 形态**的 `DSH_HOME` 下 | 可用（**会静默改写 `~/.dsh/.agent-presets/governance/`**） | **`exit 2` + `[REFUSED]`**（`--dry-run` 仍放行，只读预览） | 本版开发期间发生**三次真实环境写入事故**；守卫对称化使同类事故在 CLI 面结构性关闭 | 真实 home 形态：未设 / 空串 / 空白 / `<home>` / `<home>\.dsh` / 其子目录 / 符号链接 / 大小写差异 —— **全部拒绝**。隔离 `DSH_HOME`（`%TEMP%` 等）不受影响 |

> **升级提示（面向用户）**：`--install` 的**推荐用法**是让 dsh 自身完成安装（`dsh plugin add` + 重启），或显式把 `DSH_HOME` 指向目标位置。直接对真实 `~/.dsh` 执行手工 `--install` 从本版起会被**拒绝**——这是刻意的（见 B-2 理由）。

## 3. 新增的检查面与命令（加性，默认启用）

| # | 项 | 形态 | 默认 | 说明 |
|---|---|---|---|---|
| A-1 | **Check 28w `check-dsh-boundary`** | 治理检查段（K-1~K-13） | **启用** | 契约↔消费方边界看护（含 K-8 `strong` ⇒ 反相 fixture、K-11 allowlist 棘轮、K-12 一致性判据、K-7 版本证据）。**交付态（V8 `3074120`）**：段号 = **`28w`**（`infra/registry.py` 段表 `("28w", "checks.dsh_boundary.emit_check_section")`，`quickscan_registry.py` 同段）；CLI = `python skills/software-project-governance/infra/verify_workflow.py check-dsh-boundary`；棘轮口径 **cli keys 84/84 + segments 71/71（含 28w 段）**；K-1~K-13 逐条结论见 checklist Gate 7 行；退出码与 `--offline` 适用域见下面 A-2 行。 |
| A-2 | **`dsh-doctor`** | 命令（S0~S7） | 启用 | 单点诊断入口；退出码 `0`（健康）/`1`（**可行动**失败）/`2`（**REFUSED**：用法错误 / 未授权探测）。**实测 CLI（V8 `3074120`）**：`--json` / `--stage S0..S7` / `--offline` / `--selftest` / `--record-evidence` / `--out` / `--rehearse CANDIDATE.json` / `--against BASELINE.json` / `--allow-host-probe` / `--fail-on-issues`（四开关 = `--offline` / `--selftest` / `--record-evidence` / `--rehearse`）。**S2 投影字段**：`coverage` 由单一生成点产出并携带 **`unreadable_compositions`**（F-R1-06 义务；Check 28w K-12 已兑现——`checks/dsh_boundary.py` 机检 `check_dsh_preset_compat` 携带该字段）。**`--offline` 适用域**（设计 §5.1：禁止一切子进程/宿主探测，相关阶段降 `NOT_RUN` 而**不 FAIL**；隔离 `DSH_HOME` 实测归因）：**S2**（Check 28v 需 node 解析安装态 schema）、**S4**（JS 渲染 parity 半边不跑，Python 半边仍输出 sha256）、**S6**（隔离冒烟需起子进程）三阶段带 `--offline:` 原因记 `NOT_RUN` 并各带 remediation；**S5** 记 `NOT_RUN`（宿主入口平面无离线路径，且探测需 `--allow-host-probe` = M7.7 三选一前置）；K-12 的裁决一致性比较限定在**全阶段非 `--offline`** 运行（设计 N-3）。 |
| A-3 | **契约 `adapters/dsh/host-contract.json`** | 数据文件 | 必需 | 唯一机器可读依赖事实源；缺失/畸形 ⇒ 消费方按 §2.5.1 三态降级（`NOT_RUN` / `FAIL`），**不再静默用内联常量** |

## 4. 建议的"降级/回退"开关（本版**未**提供，如实列出）

| # | 场景 | 本版处置 | 归属 |
|---|---|---|---|
| D-1 | 用户需要在本机对真实 `~/.dsh` 执行手工 `--install`（离线/无 dsh CLI 场景） | **不可用**（B-2） | **FIX-324**：补显式 opt-in 或同步 README/`AGENTS.md.template`/ADR-018/`feature-flags-0.80.0` 的文档口径 |
| D-2 | 契约缺失时"退回内联常量"以继续交付 | **刻意不支持**（J-4：保留回退副本 = 第二事实源） | 维持设计裁决（ADR-018） |

## 5. 与 0.80.0 的开关对照（无删除）

- 0.80.0 的既有开关（`--quick` 影子通道、`product-gate` 跳过机制等）**全部保留**，语义未变；
- 本版**未删除**任何开关；
- `uninstall --dry-run` 的不对称（`install --dry-run` 放行、`uninstall --dry-run` 被拒）已在 FIX-316 修复中**对齐**——两者现在都放行且零写入（实测证据：**EVD-1026**）。

---

*M-1 冻结（2026-09-13）。V8（FEAT-031 `3074120`）已落地，「待 V8 回填」占位已按实测事实补齐；§2 的 B-1/B-2 行为变更事实本批未改动。*
