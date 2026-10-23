# FEAT-103 — DSH 隔离补丁设计 R2 修订版独立复审 R2（round=2，逐条对照 F1–F4，承接 R0/R1 审查链）

- 日期：2026-10-20（Asia/Shanghai）；取证 UTC 10:10:25Z–10:13:07Z（逐条见 §8）。
- 身份：**新实例** Design Reviewer（本 R2 复审实例）；不是 R0/R1 审查实例，不是设计作者。已完整读取 R0 报告、R1 报告（F1–F4 权威描述）与 R2 修订版全文，逐条对照。按 `agents/design-reviewer.md`、`skills/design-review/SKILL.md` 执行；任务指令明确授权本实例对真实安装 SDK 严格只读核验（Read/grep/sha256sum）并逐条上报命令。复审本质是验证修复——本报告不重开 R1 已裁定无需重开的方向讨论。
- 审查对象：`docs/architecture/dsh-upstream-owned-registration-R1.md`（文件名沿用，内容为 **R2 修订版**，原地修订），SHA256 `7b43101cb9aa25561f655f976c5e4c6d1fcf16c3bd0e1aafaf42261c1eba3734`（immutable——R1 审查时为 `5367f9ab…`，差异即 R2 修订本身）。
- 只读输入：R1 报告 `docs/reviews/review-FEAT-103-DESIGN-R1.md`（SHA256 `ca7093a0864ea238c7b556bba841956ffe33adeb912488e90c820182d13df124`——结论 NEEDS_CHANGE，F1–F4）；R0 报告 `docs/reviews/review-FEAT-103-DESIGN-R0.md`（SHA256 `ae848da49a09eae2f95bfd6bdf6f979b22c87192a55d3ff808fadf0e02fcd52f`——与 R1 记录一致，未被改动）；原设计 `docs/architecture/dsh-upstream-owned-registration.md`（SHA256 `be5741d44a74751efaabe371f50fd3ce3a4d0e3a7e8ce041faa0c6cae12fb52f`——与 R0 记录一致，未被改动）；SDK `C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh`（0.2.1-rc.2）严格只读。
- 零回退核验方法说明：设计文档在 git 中未跟踪（untracked），无 R1→R2 diff 可用；零回退判定以 R1 报告逐字引用的冻结文本（CH-1.1 代码、CH-1.2 步骤 4/6、CH-1.5、T01+ 要素、B2/B3 PASS 要素清单）为基线做内容比对，辅以 SDK 锚点文件哈希零漂移证明全部 SOURCE 事实立于 R1 取证时相同字节。
- 权限边界：仅写本报告一个文件；未运行/probe/写入 SDK；未写 `.governance/`；未与用户交互；未做最终决策。真实环境命令逐条见 §8（Coordinator 机录 EVD 用）。

## 1. 结论

```text
conclusion=APPROVED_WITH_NOTES
unresolved_blockers=0
round=2
review_identity=NEW_INDEPENDENT_INSTANCE_R2
predecessor_review=docs/reviews/review-FEAT-103-DESIGN-R1.md (NEEDS_CHANGE, F1-F4)
review_scope=FEAT103_R2_REVISION_F1_F4_VERIFICATION
current_sdk=0.2.1-rc.2 (hash-checked vs R0/R1, zero drift)
r1_findings=F1:FIXED F2:FIXED F3:FIXED F4:FIXED
r1_regressions=NONE (R0 closure surface intact)
new_findings=N1(P3/NOTE) N2(P3/NOTE) N3(P3/NOTE)
implementation_authorized=false (remains false; Coordinator to authorize)
runtime=NOT_RUN
storage_regression=NOT_RUN
```

**R1 四项 finding（F1 BLOCKING + F2 P2 + F3/F4 P3）全部真实修复，无修复引入的新缺陷**：

- **F1（BLOCKING）已修复**：R2 选定 R1 推荐的最小解除方案 (a)——`WeakMap<Fiber, Set<OwnedRecord>>` 多值 owner 索引。CH-1.1 listener 对集合内全部 record 依序 close（first-reason-wins/幂等/不抛）；CH-1.2 步骤 4 改 get/add-else-set 不覆盖、步骤 6 改按 record 精确移除（Set 空才删 WeakMap 条目）；CH-1.3 每 begin 独立 effect；CH-1.5 顺序合同对每条 record 独立成立；T01+ 增同 owner 双 record 反例行；§9 性能行 O(该 fiber owned records)；§10 R2 增量含 (a)/(b) 二候选与排除理由。单值映射的两条失败链（set 覆盖→通知丢失→等待环复活；tombstone 连删兄弟映射）在多值结构下**结构性消除**，race-free 论证（步骤 5 复核）在多值下逐 case 复核仍成立（§3 详证）。
- **F2（P2）已修复**：S-C8 更正与 SDK 直读逐行一致（本实例独立核验，非采信 Architect 自检）：dispatch :259 thisArg 仅在 args[0] 为 object/function 时取；:1093 创建发射 args[0]=事件名字符串 → thisArg=null、filter=undefined、无 scope 过滤，与 teardown 发射同路径；判别只靠 uid。§9 补发射次数说明（创建发射同样进入监听者、uid 判别 O(1) 早退）。R2 新增的"创建发射经 emit :280-282 无 per-callback try/catch、异常传播至 :1094 catch 触发 fiber dispose 并重抛"遏制不对称注亦核实属实。
- **F3（P3）已修复**：§5.5 措辞澄清与 SDK `reuseSetup` :483-491 直读一致——:488 append 位于包装器内、`composition.setup`（:486）返回之后，仍为 pre-publication append，实质语义未变。
- **F4（P3）已修复**：T01+ 增 root-context owner 观测行（终态理由 `registry-disposed`、经 registry fiber teardown 发射的 closeAllOwned、不虚构 root 专属发射）。

**R0 闭环面零回退**：B1 机制层（CH-1.1 锚点仅索引基数与 S-C8 注释更正，机制未动）、CH-1.5 反例合同与禁 timeout/最终清理抵销原文（三处在位）、B2 全部（§4）、B3 全部（§5.2–5.4 零改动、§5.5 仅措辞）、D1–D3（§6）、§3.4/§3.5（证伪出口）、§8 末段不降门承接——全部在位（§4 逐项）。SDK 五锚点文件（cordis/controller/registry/subagent/agent-loop）SHA256 与 R0 §2 记录**逐一相同**——R1/R2 文档全部 SOURCE 事实立于零漂移字节。

**新 findings 仅 3 项 P3 备注**（N1 证据时戳说明 / N2 测试行时序排列提示 / N3 实现细节备注），无 P0–P2。按 SKILL 终态语义，`APPROVED_WITH_NOTES` 为无未解决 BLOCKING finding 的通过终态，可结束复审链；实现授权仍 false，由 Coordinator 裁决后续。

## 2. 取证方法与基线

- 防漂移（本实例直接计算，R2-V01/R2-V03）：cordis `6a9394c0877ff45218818c6e815edd038f8057e1a1deb390a8d43ec81c57691e`、controller `a9801acb…`、registry `95edcc66…`、subagent `9a9572e7…`、agent-loop `cf57e3ec…`——五者与 R0 §2 记录 hash 全一致；R0 取证（08:18Z）→R1 复核（09:31Z–09:45Z）→本 R2 复审（10:10Z–10:13Z）期间安装态零漂移。
- 文档基线（R2-V00，仓库内）：R0 报告与原设计 hash 与 R1 记录一致（未被动）；R1 报告 hash `ca7093a0…`（本报告输入）；R2 修订版 hash `7b43101c…`。
- F2 事实抽检：cordis/lib/index.js 四窗口直读（dispatch :258-264 / emit :280-282 / emitPluginDisposed :968-984 / Fiber.dispose+创建发射+root 分支 :1075-1113），逐行比对 R2 §2.3 S-C8/S-C2/S-C3/S-C4/S-C9 更正后文本。
- F3 事实基线：controller :481-494 直读（reuseSetup 包装器结构）。
- F1 合同前提复核：原设计 :70-71（`beginRegistration(definition, {owner, signal})` 无单 record/owner 限制）、:89（LOADING/ACTIVE owner 可 begin、effect 先于分配安装）、:192（同 id closed→new begin 允许）——F1 的"合同合法输入"前提与 R2 §3.3 引用一致。
- tombstone 时点依据：原设计 :193"tombstone 回收 = drain 完成且旧 reader 已得到终态后按 identity 删除"——R2 CH-1.1"集合在 close 期间不被修改（无需快照迭代）"所引合同原文属实。
- 所有判定基于直接读取证据；不采信 Architect 自检，也不因自检 PASS 跳过验证。

## 3. F1–F4 逐条判定（round=2 核心）

### 3.1 判定总表

| # | R1 finding（级别） | 判定 | 证据（文档章节 + 本实例独立核验） |
|---|---|---|---|
| F1 | `WeakMap<Fiber, OwnedRecord>` 单值映射不能表达同 owner 多 record；覆盖→通知丢失→R0-B1 等待环复活；tombstone 连删兄弟映射（BLOCKING/P1） | **已修复**（方案 (a) 多值索引；无新引入） | §3.3 CH-1.1（类型+listener 循环 close）/CH-1.2 步骤 4/5/6/CH-1.3/CH-1.5、§7 registry 行、§8 T01+ 双 record 行、§9 性能行+BR1'、§10 R2 增量、§1.1 响应表；原设计 :70-71/:192/:193 合同前提直读核验；race-free 多值化逐 case 论证见 §3.2 |
| F2 | S-C8 事实错误（:1093 创建发射实际 thisArg=null 无 scope 过滤）+ §9 发射次数未成文（P2） | **已修复** | §2.3 S-C8 更正行 + §9 性能行；SDK 直读：dispatch :259（thisArg 仅 args[0] 为 object/function）、:262-263（filter=undefined→`!filter` 短路全量 hook）、emit :280-282（同步、无 per-callback try/catch）、:1093（args[0]=事件名字符串→thisArg=null）、emitPluginDisposed :968-984（per-callback try/catch+:980 Promise rejection 消费）、Fiber.dispose :1078→:1079→:1080-1083→:1084→:1085-1088→:1089、:1092-1097（创建发射 catch→dispose+重抛）——全部与 R2 更正后文本逐行一致 |
| F3 | §5.5 ":488 保持 setup 内 append"措辞不精确（P3） | **已修复** | §5.5 澄清文本；SDK 直读 :483-491：:485 blank 复查→:486 `await composition.setup(...)`→:488 append（在包装器内、setup 返回后）→:489 return commit——措辞现与代码结构精确对应，实质语义（pre-publication append）未变 |
| F4 | T01+ 缺 root-owner→registry-disposed 观测行（P3） | **已修复** | §8 T01+ "root-context owner（F4）"行：整体卸载时终态理由呈现 `registry-disposed`（经 registry fiber teardown 发射的 closeAllOwned 关闭，不虚构 root 专属发射）——与 CH-1.4 合同声明、S-C9（root `dispose=()=>restart()` 无发射，SDK :1102-1113 直读核实）一致，可观测可验收 |

### 3.2 F1 修复质量详证（多值索引的合同/时序/GC 三面）

**结构面**：
- CH-1.1 冻结类型 `WeakMap<Fiber, Set<OwnedRecord>>`，listener 改 `const owned = this.ownedByFiber.get(fiber); if (owned !== undefined) for (const record of owned) record.close('owner-disposed')`——对集合内**全部** record 依序 close（Set 插入序，确定性），每 record 独立 first-reason-wins/幂等/不抛。与 id 主表（definitions）联动的双向成员关系由 CH-1.2 步骤 4/6 维护。R1 指出的"第二次 set 覆盖第一条"失败链在 add-else-set 语义下不存在。
- CH-1.2 步骤 6：`ownedSet.delete(record)` 按 record 精确移除、Set 为空才移除该 fiber 的 WeakMap 条目——R1 指出的"tombstone 删条目连带删兄弟映射"失败链消除。
- CH-1.3：同一 owner 多次 begin 时每 begin 安装独立 effect、闭包捕获各自 record——兜底面与索引面一致，无覆盖。

**时序面（race-free 论证多值化后是否仍成立——逐 case）**：CH-1.2 步骤 1–6 同步无 await，owner dispose 同步前缀（:1078–:1079 相邻同步语句，SDK 直读）与 begin 序列因 JS run-to-completion 不交错：
- 发射先于步骤 4：本 record 未入集合、由步骤 5 复核 close（此时 uid 必已 null，S-C4 :1078 先于 :1079）；**兄弟 record 在发射时已在集合内、已被 listener close——不受影响**。
- 发射后于步骤 4：集合内全部命中（含本条）；步骤 5 复核遇已 close 为幂等 no-op。
- 步骤 5 的"不存在发射与插入之间的窗口"结论在多值下逐 case 复核成立。
- **close 期间集合不变性**：tombstone 移除按原设计 :193 只能发生在"drain 完成且旧 readers 终态后"，而 drain 完成要求 payload barrier 释放——晚于同步 close 循环；close 期间的重入 begin 被步骤 2 uid 预检阻断（disposing fiber uid=null→OWNER_INACTIVE）。即使实现偏离，JS Set 迭代中 add/delete 语义亦有定义——"无需快照迭代"结论稳健。
- registry fiber 自卸载分支（`fiber === this.ctx.fiber → closeAllOwned`）与多值索引正交，机制未动。

**GC 面**：owner fiber 被收集时 WeakMap 条目连同 Set 整体不可达（records 经 id 主表存活至自身 tombstone 回收）——无泄漏；fiber 可收集前必经 dispose（teardown 发射已同步送达），不存在"fiber 已 GC 而通知未发"的窗口。

**测试与性能承接**：T01+ 双 record 行覆盖"均 LOADING、各自 await lease.ready→owner dispose 后**两条** closed/readers 终态先于 barrier 释放、互不覆盖"与"A 先 tombstone 回收不影响 B 映射"；§9 性能行更正为"每 teardown 发射 O(该 fiber 的 owned records)"+创建发射次数说明；BR1' 含多 record 形态；§10 R2 增量成文 (a)/(b) 二候选、(b) 排除理由（拒收合同合法输入/新增错误面）、可逆性（回退须重开合同文本+错误表+T01+ 并重新过独立复审）——ADR 纪律完整。

### 3.3 F2 更正抽检明细（SDK 直读，全部一致）

| 更正后声称 | SDK 直读结果 | 判定 |
|---|---|---|
| dispatch :258-264：thisArg 仅在 args[0] 为 object/function 时取，否则 null | :259 `typeof args[0] === "object" || typeof args[0] === "function" ? args.shift() : null` | 一致 |
| :1093 创建发射 args[0] 是事件名字符串 → thisArg=null、filter=undefined、无 scope 过滤，与 teardown 同路径 | :1093 `this.context.emit("internal/plugin", this)` → :280-282 `emit` → :259 null → :262 `filter=undefined` → :263 `!filter` 短路全量；fiber 为载荷参数 | 一致 |
| emit :280-282 同步、无 per-callback try/catch；监听者异常传播至 :1094 catch 触发该 fiber dispose 并重抛 | :281 `this.dispatch("emit", args).map((cb) => cb(...args))`（无捕获）；:1092-1097 catch → `Promise.resolve(this.dispose()).catch(...)` + `throw error` | 一致（R2 新增遏制不对称注属实） |
| emitPluginDisposed :968-984 per-callback try/catch + 返回 Promise rejection 被消费 | :972-977 dispatch 包裹 try/catch；:978-983 每 callback try/catch；:980 `Promise.resolve(returned).catch(...)` | 一致 |
| Fiber.dispose :1075-1091 时序（uid=null→发射→移除→INACTIVE→inertia=_unload→await） | :1078/:1079/:1080-1083/:1084/:1085-1088/:1089 逐行一致；:1085 `if (!this.inertia)` 证实 LOADING 期 _unload 延后（等待环源码依据保持） | 一致 |
| 创建/销毁判别只靠 uid（创建时 uid 非 null）；CH-1.1 `if (fiber.uid !== null) return` 早退正确 | :1093 发射时 fiber 构造已完成、uid 已赋值；:1078 teardown 先清 uid | 一致 |

## 4. R0 闭环面零回退判定（任务维度 2）——**PASS**

| 面 | R2 文本位置 | 核验 |
|---|---|---|
| B1 机制层（CH-1.1 观察者锚点） | §3.3 :144-160 | 仅两处变化：索引基数（单值→多值，F1）与 S-C8 注释更正（F2）；机制要素——uid 早退过滤、同 root 单 hook 表可达性、Fiber 对象身份精确匹配、registry 自卸载 closeAllOwned 分支、失败遏制（close 不抛+S-C2 per-callback 捕获）、重入幂等——与 R1 验证通过的冻结文本语义等价，未动 |
| CH-1.2 无 race 插入序列 | §3.3 :162-169 | 步骤 1/2/3/5 与 R1 引用文本一致；步骤 4/6 为 F1 多值化改写；多值下 race-free 逐 case 成立（§3.2） |
| CH-1.5 反例合同 + 禁抵销 | §3.3 :175-186；§1 :18；§8 :327 | 可观测顺序合同原文结构保持 + F1 扩展段（对每条 record 独立成立）；"不以延长 timeout、不以 late-dispose/0-unhandled/teardown 成功抵销该门（R0 §7 约束原文承接）"在位；§8 末段"不降 schema/base accepted/broken 门、不延时或先 release 帮助通过"在位 |
| B2 全部（§4） | §4 :196-225 | CH-2.1 三分支表（显式独立/cold 独立→按 id 精确 reservation 冻结不重解析；省略→父实际 standing generation、S-U3 同步时点纪律）、CH-2.2/CH-2.3 两条独立拒收规则（继承按父 owned generation、独立按该 id 自身 record、同 id 换代不跨越）、CH-2.4 helper 公开返回类型与 setup hook 传递、能力检查先于 admission、不向 spawn/fork 加 factory、:1797→:1799→:1806 顺序保真、webhook 不声称覆盖——全部在位，与 R1 B2 PASS 要素清单一一对应，零合同改动 |
| B3 全部（§5） | §5 :227-270 | §5.2 双生命周期+token 状态机+逐出口不变量、§5.3 九分支表（含 #6/#7 回退重取分类）、§5.4 selectWithAdmission 五点（删 :757 重解析/持旧 binding 至 append/先恢复后重抛/禁先 collect/成功路径 collect）零改动；§5.5 仅 F3 措辞澄清（实质语义未变，SDK :483-491 直读证实）；CH-3.4 失败分类总则在位 |
| D1–D3（§6） | §6 :272-299 | D1 fence 位置（:1789 后/:1790 前/:1932/:1933）+thenable 拒绝消费+consumer 表（driver 划除/webhook 诚实）+持久化 gap 全文；D2 P/C/R 分支+增量；D3 终态表+覆盖扩展（cold 独立子与 live 复用/改选）——全部在位 |
| §3.4/§3.5 | :188-194 | D2 联动改写（观察者主+effect 兜底）与证伪出口 (a)(b)(c)+核心修改不在预批写面声明——与 R1 验证版本一致 |
| §8 末段不降门 | :327 | 在位（见上） |
| SDK 事实零漂移 | cordis/controller/registry/subagent/agent-loop 五 hash | 与 R0 §2 记录逐一相同——R1/R2 全部 SOURCE 锚点立于相同字节，无"文档引用已失效"回退 |

**标签纪律与交接（任务维度 4）——PASS**：SOURCE/PROPOSED/NOT_RUN 三类分离保持——S-C8 更正后仍标 SOURCE 且注明"R2 复核"与 R1 版误记来源；新增代码/合同（多值索引、步骤 4/6、CH-3.3 等）均 PROPOSED；§8 全部、§3.4 fence、§6.2 公开 fence 保持 NOT_RUN。webhook_coverage=NOT_OBTAINED 未冒充（§2.2/§6.1/§7/§11 四处一致）。§11 交接块：`design_revision=R2`、`r1_findings_addressed=F1(option-a),F2,F3,F4`、`independent_review=PENDING (RECHECK-FEAT-103-R2 owed)`——PENDING 是正确状态（文档不得预填复审结论、Architect 不自批；本报告即该 owed 复审的结果，由 Coordinator 机录）；`implementation_authorized=false`、`runtime=NOT_RUN`、`storage_regression=NOT_RUN`、`cordis_core_change_required=false`、`timeout_or_eventual_cleanup_offset=FORBIDDEN_AND_NOT_USED` 全部保持。

## 5. Findings（P0–P3，本 R2 新增）

**无 P0/P1/P2。** 三项 P3 备注（均不阻塞、不影响终态）：

- **N1 [P3/NOTE] §12 R2 复核表无命令级 UTC 时戳**。Architect 角色无 Bash 权限，已如实声明"无命令级时戳、不编造"——透明而非缺陷。证据缺口由本 R2 复审闭合：本实例对同四窗口的时间戳化独立重读（R2-V02）与四锚点哈希零漂移（R2-V01/R2-V03）确认其复核结果全部属实。留痕说明，无需整改。
- **N2 [P3/NOTE] T01+ 双 record 行"A 先 tombstone 回收"子句的测试排列提示**。该子句验证 tombstone 精确移除（A 回收不删 B 映射），其前置条件是 A 先经 signal/显式 close 且 drain 完成回收、**之后**才触发 owner dispose 验证 B 的通知——实现测试时需按此时序排列两阶段。措辞压缩但语义可导出，非缺陷；建议实现阶段照此编排（不改文档亦可）。
- **N3 [P3/NOTE] 步骤 6 精确移除的实现可达性备注**。`ownedSet.delete(record)` 隐含 record 生命周期内保留对 ownerFiber/所属 Set 的反向可达引用（或经 owner Context 重取）。合同面（按 record 精确移除、Set 空才删条目）已清晰冻结；此为实现细节提示，供 Developer 落地时注意，不构成设计变更。

## 6. 其余审查维度

- **方案完整性**：F1 修复二候选 (a)/(b) 均列出、排除理由基于合同事实（原设计 :70-71/:192 直读核验）、评估先于选择——ADR 纪律完整（§1.1/§10）。
- **技术债务**：多值索引是零合同变更的局部数据结构修正，未引入过度工程；无新依赖。
- **可演进性**：§10 R2 增量明示回退路径（回退 (b) 须重开合同/错误表/T01+ 并重新独立复审）——可逆性成文。
- **测试合同**：T01+ 双 record 行 + root-owner 观测行可观测验收（事件屏障断序非 sleep）；T05+/T06+/T07+/T09+/T11+ 全部在位（R1 已验，零改动）。
- **硬门槛**：见 §7。

## 7. 硬门槛裁决

| 门槛 | 结果 |
|---|---|
| 候选方案 ≥2 | PASS（B1 三候选 §3.2；**F1 修复二候选 (a) vs (b) §1.1/§10 R2 增量**；B2/B3/原设计候选不变） |
| ADR 关键字段完整 | PASS（§10 R1+R2 增量：日期/背景/决策/备选/排除/影响/后果/可逆/后续；Architect 不自批） |
| 蓝军挑战 ≥3 | PASS（BR1'（含多 record 形态）–BR5，每条有缓解与残余） |
| 模块无循环依赖 | PASS（§7 静态 DAG 不变；多值索引在 registry 模块内，不引入新边） |
| 接口契约/所有权安全 | **PASS**——F1 已修复（R1 唯一 FAIL 项解除；多值索引表达合同合法输入、tombstone 精确移除、race-free 保持） |
| 独立 Bar Raiser | 本报告（round=2 已执行；结论 APPROVED_WITH_NOTES，unresolved_blockers=0） |

## 8. 真实环境只读命令审计（Coordinator 机录 EVD 用；严格只读，全部 exit 0，影响路径=仅读取）

| # | UTC | 命令/工具 | 目标路径 | 结果 |
|---|---|---|---|---|
| R2-V01 | 2026-10-20T10:10:57Z | bash `date -u; sha256sum; grep -n "emitPluginDisposed\|internal/plugin"` | C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis/lib/index.js | hash `6a9394c0…`（同 R0/R1，零漂移）；锚点 :969/:970/:1079/:1093 确认 |
| R2-V02 | 10:10:57Z–10:13:07Z 间 | ZCode Read×3（行窗口 245-299 / 960-989 / 1070-1124） | 同上 | dispatch :258-264 / emit :280-282 / emitPluginDisposed :968-984 / Fiber.dispose :1075-1091 + 创建发射 :1093 + root :1102-1113 逐行（F2 抽检 + S-C4/S-C9 保持性） |
| R2-V03 | 2026-10-20T10:13:07Z | bash `date -u; sha256sum` ×4 | N 下 dsh-api-session-controller / dsh-agent-preset-registry / dsh-subagent / dsh-agent-loop 各 lib/index.js | 四 hash 与 R0 §2 记录逐一相同（零漂移） |
| R2-V04 | 10:13:07Z 后 | ZCode Read×1（行窗口 481-494） | N/dsh-api-session-controller/lib/index.js | `reuseSetup` :483-491（F3 事实基线：:485→:486→:488→:489） |

仓库内（非用户环境）命令：10:10:25Z `date -u` + 四文档 sha256sum + `git log/status`（R2-V00——R0 报告/原设计 hash 与 R1 记录一致；设计文档 untracked，零回退改用 R1 引用文本比对）；10:11:25Z `grep -n` 原设计 beginRegistration/tombstone 行号；Read×2 原设计 60-104 / 178-207（F1 合同前提 + :193 tombstone 时点）。SDK 零写入、零运行、零 probe；`.governance/` 零写入；本实例唯一写面为本报告文件。

## 9. 下一步

1. **复审链终态**：APPROVED_WITH_NOTES（unresolved_blockers=0）——按 SKILL 循环语义可结束复审链；N1–N3 为 P3 备注随实现阶段消化，不要求 Architect 再修订文档。
2. Coordinator 机录本报告结论（§1 结构块）并裁决实现授权（文档侧 `implementation_authorized=false` 保持至 Coordinator 决策；授权后 `independent_review` 面更新为 R2 结果归档）。
3. 实现阶段义务承接：T01+（含双 record 与 root-owner 行）/T05+/T06+/T07+/T09+/T11+ 运行验收；runtime/storage 从 NOT_RUN 转 actual；webhook_coverage=NOT_OBTAINED 开项不因本通过而关闭；FEAT-102 R5 actual 义务不受本报告影响；§3.5 证伪出口 (a)(b)(c) 任一触发即停并独立授权。
