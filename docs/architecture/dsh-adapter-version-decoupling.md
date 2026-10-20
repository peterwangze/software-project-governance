# FEAT-102：DSH adapter 版本依赖解耦设计（待独立审查）

- 日期：2026-10-16；初始时序修订：2026-10-17；G 提案：2026-10-18；R3-B1 所有权修订：2026-10-19（Asia/Shanghai）；需求源：user-named。
- 状态：R0/R1/R2 分别仅准入 S-A/S-A2/S-A3；S-A 时序 FAIL、L FAIL、G permit 后取消 FAIL，R3=NEEDS_CHANGE/1。2026-10-19 修订 §15 待同一 Design Reviewer R4；产品接线 BLOCKED，运行支持/新探针/宿主补丁/发布/重装均未授权。§5.1 与 §14 的旧候选计划保留作历史，不再是当前可执行许可。
- 事实输入：research、Design R0～R3、feasibility/admission/guarded 三份诊断及原型/raw；2026-10-19 官方 npm 精确发布物只读核查。此次仅修改本设计，不重跑宿主场景。
- 范围：本版先恢复当前 DSH 0.2.0-rc.2 的治理预设，并减少宿主升级/插件同版迁移导致的失效。保留 CI 修复与 0.99 收尾主线。
- 用户边界：插件由用户主动卸载；适配、验收并发布后才重装。发布前一切安装/启动验收使用隔离 DSH_HOME；不修改真实 profile。

## 1. 目标与验收

1. 隔离的当前 0.2 安装态能发现 governance、成功 compose Agent、读到所有自有 skills/shims，并使用当前宿主基础工具。
2. 普通预设的 persona、技能目录、配置行和工具保持原样；治理只影响自己的派生预设。
3. 宿主 standard 新增/替换/禁用工具行后，治理预设自然继承有效变更；不维护整套 vendor 工具行副本。
4. 包同版更换真实路径、插件升级、不同 CLI/profile 平面不依赖陈旧版本 marker；不固定 npm 全局目录。
5. 接口缺失/新未知形态只拒绝本插件能力，明确诊断；不改宿主，不自动放宽兼容门，不使非治理 DSH 会话失效。
6. 诊断分清静态交付、有效登记、运行可用；零校验、目录残留、offline exit 0 都不能冒充兼容 PASS。
7. 旧模型明确兼容边界；未复验版本与运行面如实标 NOT_RUN。

## 2. 先定义评估标准，再比较方案

优先顺序：数据安全和 DEC-187 不侵入约束 → 当前可运行 → 公开可维护扩展面 → 自动继承宿主升级 → profile/user 覆盖保真 → 可隔离验证/回滚 → 代码复杂度。

| 候选 | 机制 | 优点 | 代价/排除理由 |
|---|---|---|---|
| A：迁移为静态原生声明 | cordis.patch insert dsh-agent-preset，config.plugins 搬入新版完整 standard 并改 persona/roots | 最接近上游 README 示例，装载和卸载交给 Cordis | 继续复制所有工具/plan/compaction/workflow 的配置；本轮已见缺包、新工具和策略漂移。能做一次适配，不能满足用户反复升级不失效的解耦要求。排除作为最终方案。 |
| B：消费公开 Loader 的当前有效声明，派生自有预设（推荐方向） | 自家 row 注入 agentPresets+loader；在经证明的准入点读实际树中 base preset 的 validated config；纯函数只改两个差量；registry.register 自有 id | 不依赖仓库有 host node_modules；保留当前 profile 覆盖和 !!js；无目录扫描、私有 definitions、整套工具副本；卸载仅 disposer | 旧“apply 后任务等 root”不足以保证初始可见性；必须先完成 §5.1 的登记等待链证明。S-A 失败不否定两个差量边界，也不允许忽略时序失败。 |
| C：从公开 app-boot 组合 reader 生成 | 通过合法宿主 Loader 解析 app-boot，readProfilePatches+composeEntries，找到 standard 后派生 | 源配置顺序清晰，不依赖 registry 的声明登记先后 | 比 B 多一个模块解析面和 profileContext 契约；还须防配置重读与当前已接受运行态不一致。普通 import 在 link:<repo> realpath 下不能假设可解析。可行备选，暂不引入。 |
| D：全局额外注入 skill/provider/persona | 在 host-plane 注册所有会话可见的治理能力，省去派生预设 | 代码很少 | 泄漏治理技能到普通会话，persona 全局冲突，违反既有隔离不变量；排除。 |

原生 PresetDefinition **没有 extends**；推荐 B 由本插件实现有限纯数据派生，不能宣传宿主原生继承。所谓“稳定”指仅使用已公开并经测试的最小组合接口，不承诺未来所有 breaking releases 自动兼容。

## 3. 推荐单一边界

本节及 §4 保留 B 的既定 payload 合同；§14 的 G 是待 R2 接受的结构扩展提案，尚未生效，不可据此实施 guard/wrapper。候选通过后仍须同步更新实际协议/测试/支持声明，不能借本设计提前解锁产品。

**公共 Cordis Loader 实际树 + agentPresets 登记服务**是唯一宿主运行边界。宿主的 shell/fs/goals/subagents/ask-user/workflow 工具由当前 base 预设承担；治理核心仅提供 persona 与两个技能根。

事实锚点（完整根定义见 research）：

- N/cordis-plugin-loader/lib/types/config/tree.d.ts：entries、await、import 都是公开接口。
- N/cordis-plugin-loader/lib/types/config/entry.d.ts：options、disabled、fiber、parent、subtree 是公开字段。
- N/cordis/lib/types/fiber.d.ts：config 注释明确为 validated plugin config；_config、_error 等内部面不得使用。
- N/cordis-plugin-loader/lib/index.js:140-163 的 entries 遍历 nested subtree；:214 import 使用 tree.ctx.baseUrl。不要直接调用 Node 的 loader.internal 或 internal ModuleLoader。
- N/dsh-agent-preset/lib/index.js：EntryGroup 标记保留子 plugins 的 !!js；register 返回 disposer。
- N/dsh-agent-preset-registry/lib/types/index.d.ts：register/resolve；resolve/list 在自身 host activation 内可能 self-wait（实现 :551-568）。

B 不使用 `import('@deepseek-ai/dsh-app-boot')`，也不 import 新 registry 的私有 class 来替代宿主实例。产品入口顶层仍只 import Node builtins/自有代码；repo 被 link: 安装而没有 host node_modules 是必须覆盖的正常形态。若为实现中必要的 schema 枚举导入宿主包，唯一接受路径是所选声明的公开 `entry.parent.tree.import(specifier)`，它沿该树自己的 resolution base 解析；不能使用插件 realpath 的普通 import、硬编码 N、process.argv 扫 profile 或全局缓存猜测。该方法在 closed-runtime 是否仍保真必须实测；失败返回 UNSUPPORTED，不兜底混用另一安装。

### 3.1 模块职责与依赖

| 模块 | 职责（单一） | 输入/输出 |
|---|---|---|
| lib/index.js（入口） | 接入自身 row 生命周期，选择能力协议并委托；失败 warn-only，不做 host 修改 | ctx/config → 自有启动/清理句柄 |
| lib/dsh-preset-source.js（新） | 从公开 Loader 实际树定位一个有效 native base 声明 | ctx.loader、basePresetId → BaseSnapshot 或结构化错误 |
| lib/dsh-preset-overlay.js（新） | 对有效 child rows 做纯数据派生，只拥有 persona.prefix 和两个 roots | BaseSnapshot、OwnPolicy → DerivedDefinition |
| lib/dsh-preset-lifecycle.js（新） | 串行 reconcile、readiness、fingerprint、register disposer、卸载竞态 | source/overlay/registry → RuntimeOutcome |
| 既有 adapters/dsh/launch.py、infra/dsh_compat.py/doctor | 离线物料/隔离验收/诊断相同协议，区分 native 与 legacy | 安装/平面/策略 → 四态证据 |

依赖 DAG：entry → lifecycle → source + overlay；source → 公共 loader；lifecycle → registry；overlay → 自有 policy/contract。infra 消费自有协议和测试 fixture，不反向被产品入口 import；无环。

当前固定 host.rows 数组移入明确的 legacy 分面，不再要求 native 派生行数与旧 30 行一致。自有 host-contract 仍单一事实源，但必须区分 own-policy、protocol-capabilities、legacy-facts、measured-evidence；不能把宿主当前所有工具行变成新的永久自有清单。

### 3.2 自有策略

`OwnPolicy`：

- presetId='governance'（保留已有 session identity）。
- basePresetId='standard'（首版明确默认，可由本包 row 的 config.basePresetId 选择同 profile 中另一有效 native 声明）。
- governancePersona 来自唯一的 `agent-presets/governance/persona.md.template`（从现模板提取治理正文，不包含宿主身份行）；native 将其追加到 base.prefix，保留宿主身份及用户前缀。包版本与包根每次由当前模块/本包 package.json 派生。
- skillRoots=[当前包 skills 的绝对路径, 当前包 adapters/dsh/skill-shims 的绝对路径]。
- personaPackage、skillFilesystemPackage 两个匹配名由契约集中维护。
- 不声明宿主 toolName/provider/maxDepth/plan 文本/compaction 阈值等配置。

basePresetId 不得等于 presetId；不跟随“用户 default=governance”造成自派生循环。当前 profile 必须真的有该 base；不存在时明确 BASE_NOT_FOUND，不能静默切换另一个 profile 或 minimal。

## 4. 输入输出与错误契约

### 4.1 BaseSnapshot

`{protocol:'native-declaration-v1', basePresetId:string, rowAddress:string, resolutionBase:string, config:{id,name?,description?,order?,plugins:Entry[]}, fingerprint:string}`

读取算法：

1. 仅在已证明宿主有效树完成准入后调用公开 loader.entries()，不固定 preset-standard 的 Loader 地址。原 S-A 的 root settle 后读取可用于离线对照；初始产品路径需通过 §5.1 的 S-A2，不能在自身 activation 内调用 root await。
2. 候选仅为本 host Loader 树中 name='@deepseek-ai/dsh-agent-preset' 的有效声明；按 validated `entry.fiber.config.id` 匹配 basePresetId。优先匹配 id，不硬编码 declaration row id。
3. 不能仅读 raw entry.options.config：更新校验失败时 raw 和已接受的 config 可能不同。fiber.config 是公开已校验值；拿不到便 INVALID_BASE，不读 _config/_runner/private definitions。
4. 使用 entry.disabled 的宿主语义排除被禁用及继承禁用的声明；表达式抛错不当作 disabled/pass。
5. 要求恰好一项，plugins 是非空数组、有效 entry list。base 的公开 Fiber 已完成启动与 registry.resolve(basePresetId) 无 broken 是两个不同证据，不能互代；后者只能在不自包含的 root settled 审计点执行，不得嵌入自身 activation。初始候选如何在完成该审计前避免发布无效 base 的派生预设，仍是 S-A2 硬门；无法证明则候选失败，不能删去 BASE_BROKEN 拒收要求。
6. structuredClone 取快照，保留 !!js 对象和嵌套 groups；禁止 JSON.stringify/parse 充当克隆器。fingerprint 只用于比较，可以对规范化数据做 JSON 编码+SHA-256，不能当作加载器。
7. 原始快照不修改、不写回 Loader；不调用 loader.update/create/remove/write；源读取只通过公共声明/ctx 接口。

匹配原生声明 shape 是有限支持边界。第三方任意插件自行 register 的 base 没有该声明时，首版明确 unsupported；不能偷偷读 registry 私有表补齐。

### 4.2 DerivedDefinition

输出 `{id:'governance',name:'治理协调器',description,plugins:Entry[]}`：

- 找 **恰好一个启用的** personaPackage row 和一个启用的 skillFilesystemPackage row。缺失、重复、未知嵌套或不可安全判定条件均拒绝，不猜哪一个。
- 仅将唯一治理正文追加到 persona.config.prefix，保留原 prefix（宿主身份与用户覆盖）、suffix/complete/includeRuntimeContext 以及当前所有其他字段。若完整提示策略与治理上下文冲突，应按 POLICY_CONFLICT 明确拒绝，不静默重写用户策略。base.prefix 为不可安全合并的动态表达式时同样拒收。
- 对 skill row.config.customSkillDirs 追加两个绝对根并去重；保留现有 roots、providerName、includeDefaultRoots、watch 等全部字段。
- 如果 config/customSkillDirs 是依赖运行上下文的 !!js，而无法不提前求值地追加，首版 UNSUPPORTED_EXPRESSION；不可提前执行表达式、丢用户 roots 或覆写为静态空值。
- 其他每一行、disabled、provider、group、isolate、inject、顺序和未知字段原样保留。宿主新加/删除的工具自然传播。
- 新派生结构经真实宿主 register 激活审计；Promise 返回不自动 PASS，必须 resolve 无 broken + compose 通过。

persona/skill 条件判断首版支持已确定的普通启用配置。复杂自定义树可明确拒收；不得把“通用升级”误写成“任意第三方 YAML 都能合并”。

### 4.3 RuntimeOutcome

`{protocol, phase:'starting'|'ready'|'unsupported'|'failed'|'disposed', basePresetId, fingerprint?, packageRoot, hostVersion?, sourceAddress?, reasonCode?, message, validation:{schema,activation,composition}}`

错误码至少：HOST_PROTOCOL_UNKNOWN、BASE_NOT_FOUND、BASE_DUPLICATE、BASE_DISABLED、BASE_BROKEN、BASE_CONFIG_INVALID、OWN_ID_COLLISION、OWN_POLICY_CONFLICT、UNSUPPORTED_EXPRESSION、REGISTRATION_BROKEN、INIT_TIMEOUT、DISPOSED_DURING_START。判断能力不按 host exact version equality；版本只作证据和支持范围诊断。

## 5. 生命周期、刷新与卸载

### 5.1 初始启动

#### 5.1.1 S-A 已证事实与撤回的推断

S-A 最终结论为 `FAIL_POST_BOOT_PRESET_VISIBILITY`，进程 exit 0 仅表示完成采集。20 场景、38 次 schema 校验及原始事件保留在 feasibility 报告；不能将失败改列“可接受的 starting 窗口”。

- **实际 boot + microtask**：register-start 在 boot-return 前，register-complete 在其后；真实 roster/resolve、Web create 通过。registry.register 先同步加入 record，再等待 mount，已有 record 的 resolve/retain 会等 record.ready，因此“record 已存在”与“激活完成”可分离。
- **实际 boot + setImmediate**：boot-return 后立即调用真实 list/resolve，治理 id 缺失，resolve 为 `agent-preset/not-found`。Web create 本身仍成功，因其先 await mkdir(cwd)，给了后台登记机会；没有观察到此自然路径的 create 失败，不能虚构。
- **三个人工 admission barrier**：在 root settle 与 register 之间额外暂停后，真实 create 为 not-found。这些是可证伪窗口，证明自有 readiness 不构成宿主准入门；不是原正常路径必然存在该 barrier 的证据。
- **Headless 更正**：当前 headless 等 Loader 后调用 agents.create，但不选择/挂载 agent preset，AgentLoop 也不自动补挂；它不能证明 governance 首会话可用。此次 consumer 是公开 Web SessionController.create/composeAgent 的真实路径。current-web 仍为首个支持目标，其余 profile NOT_RUN。

旧措辞“apply 已返回后的任务”撤回：它同时容纳 microtask、setImmediate 和任意异步前置工作，无法规定何时登记进入宿主等待链。测试不得先 await 自有 readiness 再触发首次宿主操作，也不得靠 mkdir 的偶然 I/O、sleep、模型耗时或测试额外等待过门。

#### 5.1.2 可证伪的初始准入契约

将启动拆成两个观测点，不新增宿主 API：

1. **登记准入（admitted）**：在当前公开 boot 完成并允许 consumer 读取预设的边界之前，governance 的 register 调用已同步建立自有 record，或宿主已有一条公开且可证明的等待链阻止该 consumer 越过此点。边界后的第一条真实 list/resolve 和显式/default-governance create 必须可见该 id；若 mount 未完成，它们应由 registry 的现有 record.ready 等待激活，不能 not-found。
2. **运行就绪（ready）**：base audit 与派生 record 均无 broken，真实 compose 成功；控制器此后才能记录 READY。registry.register 正常返回不代表通过：activate 会将异常记录为 broken。存在 pending host rows 时，resolve/list 的 diagnostic 会退回 host loader.await，故不得在自身 activation/cleanup 链内执行这些审计。
3. 初始 activation 可以被宿主等待，但其内部不得等待包含自己的 root、等待依赖自己的 provider、或返回只会在 boot-return 后被释放的屏障。cleanup 继续不等待启动任务；期限仅用于报告/终止失败，不能以“到时放行”代替准入证明。
4. 异步 source/schema import、base audit 或其他 await 都必须标在时序图上；“register 前只有同步工作”不能省略这些实际步骤。register disposer 一经返回由 lifecycle 独占；stopped 时立即处置，不覆盖冲突 id。

成功场景必须同时给出因果等待链和 raw event，证明第一条宿主 lookup 的参数在进入 registry 前已固定，且与自有 readiness 无关。单次或多次 fixture 成功只能支持实测范围，不替代公开源码契约。

#### 5.1.3 初始时序候选比较

评估顺序为：无自等待/数据安全 → 初始 lookup 有登记保证 → 有效 base 与 broken 拒收保真 → 公开能力 → 成本。所有候选尚未获产品接线许可。

| 候选 | 可操作机制与等待链 | 事实/代价 | 当前裁定 |
|---|---|---|---|
| M：强制 microtask，root settle 后同一 continuation 立即登记 | 同步 apply 安排 Promise microtask；在 root.await 返回后仅同步读/克隆/overlay，然后立即 register；审计另置不自包含的阶段 | S-A 一条实际 boot 路径通过。但 Loader.await 的多个调用方各有 Promise.allSettled/循环，boot 还有独立 audit；源码未规定插件 continuation 必先于所有 consumer。base resolve、schema import 任一额外 await 都打破“立即”。成本低但调度前提脆弱。 | **不足以单独保证契约，不提升为默认实现**；只保留 S-A 对照，不能把 microtask 禁止额外 await 当成已证充分条件。 |
| L：公开 Loader await intercept 准入，再将 register 挂入自有 activation | 本包 row 的 loader 注入采用公开 `Loader.Intercept.await=true`；Loader 有当前 tasks 时使本包 Fiber 保持 PENDING。该门释放后才读有效声明；apply 返回由 register 激活完成所控制的生命周期 Promise/效果，使自身 inertia 被 host root.await 观察。链为“既有 host tasks → 本包 activation/register → host boot”，不在链内反向 root.await。 | 类型明确描述该 intercept 用途；实现 Service.check 以 getTasks 判定。它与手动调用 loader.await 不同。但自身 inertia 重新出现后是否令该 intercept 再次失效/反复重启、PENDING 行不在 getTasks 的 inertia 集合、首次导入/嵌套组/通知顺序、base pending/broken 审计及 dispose 均需实测；不能因看见开关就宣称无环。成本中等，无新增 host 模块依赖。 | **优先送 S-A2 证伪，非选定产品方案**。若自有 activation 等待的 mount/audit 又依赖自身，或未完成有效 base 审计会暴露非法派生，立即失败退回 R1/R2；禁止改成 detached 任务掩盖。 |
| F：只等待已经启动的 base Fiber，再由自有 activation 控制 register | 前提是公开树完整且唯一有效 base Fiber 已存在；仅 await 该公开 Fiber.await，然后同步快照/派生并 await register；不调用 Entry.init、不等 root | Fiber.await 只等该 Fiber 当前 inertia 并重抛启动错，不保证尚未导入/尚未启动的声明出现，也不保证完整树唯一性。Entry.init 会主动 import/start，不能作为只读等待。仅预载入 host 的受限形态可操作；前置条件缺失必须明确拒收。 | 保留可独立证伪的备选；**NOT_RUN**。无法覆盖 current-web 行前/末及冷启动则不满足本版目标，不以重排行/启动宿主行补救。 |

源码依据（本次只读复核，完整命令见 §13）：EntryTree.await 是 getTasks+Promise.allSettled 循环；getTasks 取 entry 初始化任务/公开 inertia，未声明对外 microtask 顺序。Fiber._reload 会异步执行 plugin effect 并等待其完成；Fiber.await 等当前 inertia。Loader.Intercept.await 的公开注释为“Keep dependent plugins pending while loader entries are still loading”，Service.check 在配置 await 且 getTasks 非空时返回 false。AgentPreset 自身的 Service.init 等 register 并收集 disposer，是注册进入 activation 链的现有例子；这不等于证明 L 的完整 source/audit 链成立。

#### 5.1.4 S-A2 最小证伪计划与退出门

Design R1 仅可批准下列隔离试验；S-B～S-F 继续冻结。沿用真实 Cordis/Loader/registry/Web controller、manifest 参数定位和 repo 无 host node_modules；原 S-A 的失败与对照保留，追加候选结果，不重写历史 raw。

| 门 | 最小场景/必须观察 | 失败处理 |
|---|---|---|
| A2-1 等待链 | L 下本包 row 最前/末；冷启动与 core/base 预载入；记录 PENDING→activation、base Fiber settled、register-start、boot-return、第一条 lookup，并检查自身 inertia 出现后 intercept 不自失效/反复重启。导入和嵌套组延迟用事件屏障，不用 sleep；不得读取私有字段以实现产品方案。 | 任一正常 lookup 先于登记、intercept 提前释放、反复重启或完整树未确定 → L 失败。 |
| A2-2 首次 consumer | 实际 app-boot 返回后立即调用真实 list/resolve；并行真实 Web 显式/default-governance create。mount 延迟只在确认 register-start 后释放，证明等待来自 record.ready；另在 register 前的唯一可疑异步点暂停，证明 boot 确实受自有 activation 门控制。 | 未登记可见性失败即失败；create 的 mkdir 成功不能抵销 list/resolve 失败。不得让 harness 先等自有 READY。 |
| A2-3 base/pending/broken | 缺失/重复/disabled/失败 base、有效 Fiber 但 registry broken、子行缺 host service，以及 profile 覆盖/!!js。明确 base audit 的位置；若 audit 可能 root-await 自身，必须退回设计，不能移除 audit 或开放无效派生窗口。 | 必须拒收自己、保全普通 base；有限超时只能记录失败并允许自身释放，不算成功等待链。 |
| A2-4 卸载/收敛 | 在 intercept PENDING、register 飞行、派生 pending 子行时卸载；先观察 cleanup 返回，再释放相应屏障，drain 后自有 id/监听无残留、无 rejection，普通 standard 保持。 | 任一自锁/晚到幽灵登记失败；不得在 cleanup await 全部启动任务。 |
| A2-5 边界证据 | 动态验证故意坏注册仍不报 READY；记录 fixture/schema 覆盖、same-context 模块路径和完整事件。需要完整 link/current-web、实际技能、热刷新、工具参数的部分仍列 NOT_RUN，由后续切片验证。 | 任何 fixture 成功不得升级为整个 profile/发布通过。 |

若 L 不能满足 A2-1～4，带失败轨迹回同 Design Reviewer；再评估 F 的预置条件或方案 C 的公开组合 reader，不改宿主、不增反向依赖、不静态复制所有工具、不回退旧 HOME writer。M 只有获得更强公开因果证明后才可重新提案。S-A2 通过也仅解除这一时序先行门，须经独立复审明确授权，不能直接发布或重装。

不使用 `readDocument` 作为继承协议；它是 view-only 文字输出，没有本设计所需的 accepted-config/readiness保证。

### 5.2 热刷新

- 监听已公开的 `app-boot/config-reload`（N/dsh-app-boot/lib/types/index.d.ts）；回调只安排串行 reconcile，不把待 root settle Promise 返回给当前 reload 的 dispatch。
- 读取最新已接受 effective tree；相同 fingerprint 不重注册；不同则只退休本包 disposer，再注册新 generation。已有 Agent 的 revision 保留交给宿主。
- 若 base 被删除、禁用、broken 或 persona/roots 不再可安全合并：撤回自己的当前声明、标 failed；不保留 stale 策略给新会话，尤其不抵消安全设置。已存在会话的保留行为如实说明。
- 源应用 reload 时需 epoch/队列合并，禁止旧 reconcile 在新策略后“晚到覆盖”。不会监听文件路径、自行 HMR 宿主模块或解析 argv。
- 宿主版本/安装根改变必须重启整个 DSH；不尝试在存活进程里换宿主 package 版本。
- 不支持该公开 reload 事件的宿主标 restart-required；不能宣称热刷新成功。

### 5.3 清理与竞态

- disposal 首先置 stopped 并移除监听，立即阻止所有后续新登记，然后处置已持有的自有 disposer。
- **cleanup 不能 await 一个正在等 loader.await() 的启动任务**，否则自身卸载成为 root settle 条件形成循环。
- 若 register 正在飞行，晚到 disposer 必须立即执行，Promise 拒绝必须被消费；不再接触已失效 ctx.effect。隔离 harness 提供 drain 观察迟到清理完成。
- 不写/删 .agent-presets、不恢复 profile、不删除孤儿目录；卸载只撤回内存登记及本包监听。这个新 native 分支不产生 HOME 文件。
- 首版注册时序/迟到清理/热刷新均属实现硬验收，不以 SOURCE 推导替代实测。

## 6. 版本协议与旧模型

| 检测结果 | 行为 | 允许声明 |
|---|---|---|
| registry.register + loader.entries/await + native accepted declaration 都满足 | native-declaration-v1；当前目标 0.2.0-rc.2 | 隔离全链通过后声明当前版本 runtime 支持 |
| 已知旧 dsh-agent-presets 目录协议/公开 roots、read、copy/remove 面；无 register | UNSUPPORTED_NO_AUTOWRITER（Design R0 裁定） | legacy renderer/fixtures 仅作离线历史材料，普通 apply/install/repair/update 自动入口均隔离；不声明旧版运行支持 |
| native 缺关键能力/未知 shape/仅有旧目录残留 | 不写任何目录、不自动 legacy fallback | UNSUPPORTED / NOT_RUN，不得 PASS |
| 当前有新 native 又留旧目录 | native 优先；残留作 legacy-residue | 不导入旧目录，不自动清理 |
| 未安装本包 | UNINSTALLED，提供发布后重装路径 | 不自动 repair |

不能以 null compat_range、旧 factsheet 路径或插件版本 marker 判支持。版本支持表可记录实测，adapter 选路按能力。若新增 dsh peers，范围须由 Reviewer 按本矩阵和实际测试裁定，不能精确钉死 rc.2、也不能用 "*" 承诺所有未来 API；peer meta optional 不代表上游 compatibility evaluator 会跳过。不引入固定版本运行时 dsh 依赖副本。

legacy renderer 仍有旧自动 rmSync(target) 的安全债；Design R0 已裁定新交付的自动运行入口明确 UNSUPPORTED，绝不调用旧 writer，不再待定。历史静态材料可保留；恢复 legacy 自动运行需另作安全设计、隔离验证及独立审查，不得借回归测试执行真实 HOME 删除。

## 7. 兼容探针与 doctor 的同步设计

### 7.1 解析必须跟当前 CLI，而非猜 flat node_modules

Coordinator 隔离基线记录：`R/.governance/dsh-02-baseline-compat.log`，输入 DSH_INSTALL_DIR='C:/Users/peter/AppData/Roaming/npm'；CLI0.2正确识别，但四 oracle 包全unknown，createRequire 锚在 npm/node_modules/__dsh_compat_anchor__.js，无法找到 js-yaml，结果 NOT_RUN。当前实际依赖在 CLI 包自己的 node_modules。它是新的布局适配缺陷，不是未安装 Node 或宿主不兼容。

修正 locate/probe 返回结构：

`{cliManifest,cliPackageRoot,resolutionAnchor,profile?,protocol,oraclePackages:[{specifier,version,resolvedPath,declarer}],otherPlanes}`

- CLI 源以命令入口/显式 DSH_INSTALL_DIR 的真实 package.json 为锚；先从 cliManifest 的解析 context 解析其 oracle 依赖，支持 nested/flat/pnpm。
- profile 层必须与实际宿主 install-first/profile-second 语义一致；若无公开解析服务可模拟则标 probe-limited，不混 fallback 到另一旧缓存。
- 不假设所有 oracle 来自同一物理 node_modules；但每个 resolvedPath 必须由**同一个受选 CLI/profile resolution context**得到，并记录所属 manifest/version。
- probe 的 Node createRequire anchor 应为已选 CLI/package/profile 的 package.json，而非外层 node_modules；路径 overrides 的旧输入含义保持显式，不偷偷改 DSH_INSTALL_DIR 验收语义。
- 通过同一个自有 pure overlay 生成 native derived rows，再用安装态 schema 校验；实际 activation 以隔离 boot/registry audit 为准。探针不挂真实用户 profile，不自动 install。

### 7.2 诊断分面

- S0：记录 CLI、实际平面、native/legacy 协议；文件读取可识别版本，offline 不应无理由保留 null。
- S1：native 检查本包交付/有效登记策略；旧残留目录不算 native PASS。主动卸载=UNINSTALLED，说明等待发布后安装。
- S2/S4：检测实际生成 rows 和两个自有差量；native 不再把旧模板 parity 当主路径。legacy 继续原检查且明确协议。
- S3：各 package resolvedPath/version/CLI anchor/缓存 factsheet 新鲜度；历史 rc.1 表不能冒充当前 rc.3/0.2。
- S5/S6：隔离动态登记/Agent compose/工具技能目录；未跑则 NOT_RUN。
- S7：只验证本插件的清理、普通预设无变化；native 不以扫描用户 HOME 找残留代替卸载验证。
- 同步 adapter-manifest、README、boundary/contract 机检。新模型不再宣称 UI 删除目录/打开目录可用。
- hooks 以既有 SOFTWARE_PROJECT_GOVERNANCE_HOME/SPG_HOME/repo-local 路径验证；不为 hook 发明新的 DSH HOME marker。若外部项目缺稳定来源，记录该组合失败并单独最小修复，不触碰暂停 FIX-445 内容。

## 8. 实施切片与文件清单

1. **S-A 公共最小边界隔离探针**：已完成有限 fixture 的有效声明/register/compose/dispose，时序硬门 FAIL；完整 link 安装未验收。R1 仅批准 S-A2，现候选 L 已 FAIL 并退出。当前只提请 R2 审查 §14 的 G 合同变更/S-A3；没有下一切片批准前不运行；所有先行门及独立复审通过前不能开始 S-B～F。
2. **S-B 产品接线**：lib/index.js + 三个自有模块；cordis.patch.yml 仍只 insert 本包 row，可添加本包 config.basePresetId；提取唯一治理正文到 `agent-presets/governance/persona.md.template`，旧 composition 以专用 token 引用它，native builder 消费同一正文；共享 renderer 统一包根/版本/token/newline；禁止旧模板和新模块各留一份bootstrap。同步 `skills/software-project-governance/core/version-projections.json` 原 composition 版本投影到该唯一正文、自有 host-contract 的 payload/render token声明与 validator；legacy/native tests 对同一正文作一致性检查。package exports/files 按需纳入新文件，不添加 vendor runtime复制。
3. **S-C 协议/探针**：adapters/dsh/host-contract.json、infra/dsh_contract.py、dsh_compat.py；native/legacy 分面；CLI resolutionAnchor 模型；capture 新事实表（只能由既有 record-evidence 正道，在隔离环境）。
4. **S-D 工具链**：adapters/dsh/launch.py、dsh_doctor.py、checks/dsh_boundary.py、相关 test_dsh_*；native install/smoke 改为声明登记/隔离 profile，而非把旧目录当已安装。legacy 自动运行按 R0 明确拒收，离线历史 fixtures 保留。
5. **S-E 文档/交付**：adapter README/manifest、顶层 README 的 DSH 安装能力段、发布 checklist/rollback；goal/subagent/ask-user 只核对当前 schema，未发现硬编码旧参数不额外重构核心 goal_bridge。
6. **S-F 升级与发布**：独立 Code Reviewer；当前原生回归和 CI 四门；0.99 发布链完成后，用户环境仅按授权重装本包及必要 profile追加登记。暂停 FIX-444/445 WIP 字节保全。

tests 至少放入既有 test_dsh_adapter.py、test_dsh_compat.py、test_dsh_contract.py、test_dsh_doctor.py、test_dsh_boundary.py；必要的新 Node 生命周期测试可由 Python wrapper 启动隔离 harness。绝不把 fake registry unit 全绿当真实宿主验收。

## 9. 产品测试矩阵（均待产品接线；S-A 有限 fixture 结果不替代本表）

| ID | 场景 | 必须观测 |
|---|---|---|
| T01 | 当前0.2，隔离web，包为 link:<repo>，repo无host node_modules | 本包READY、native resolve无broken、compose成功；无裸import路径失败 |
| T02 | nested CLI依赖/flat fixture/pnpm平面 | 单一解析context选中对应oracle，含实际路径/版本；不混旧缓存 |
| T03 | 原旧插件+新host失败对照，再换新adapter | 旧目录交付不足；新声明可用；无需真实HOME |
| T04 | 普通standard前后对照、两个并行预设会话 | 原配置/工具/persona/roots不变，治理skills仅governance可见 |
| T05 | base新增工具/替换workflow/禁用工具/新增未知字段 | 派生保真，不再维护整套工具数组 |
| T06 | profile对standard修改roots、persona prefix/suffix、permissions/disabled；home和argv overlays | 读取最终已接受树，保留宿主身份和用户prefix，治理正文只追加一次；保留有效用户覆盖；安全禁用不复活 |
| T07 | 同插件版本、换包实际路径；模板内容变更 | 根据当前模块定位新根；无旧marker门；新技能可读 |
| T08 | base缺失、重复、disabled、broken、空plugins、raw更新失败 | 明确原因，自己拒收/撤回；不能fallback其他profile |
| T09 | 多persona/provider、配置 !!js无法合并、恶意循环/非法schema | fail-closed且原base字节不变；不提前执行表达式 |
| T10 | host启动延迟/当前row置最前/末尾/registry登记延迟/timeout | 先过 A2-1～4；登记进入可证明的 host 等待链，无自锁、无固定sleep；starting/admitted/ready 分清 |
| T11 | 首次 boot 后 lookup 与显式/default-governance Web create；mount尚未完成 | 首条真实 list/resolve 可见 id 并等待 record.ready；不靠 mkdir/自有 READY 等待。headless 不计 preset 验收；任一准入失败阻止合入 |
| T12 | 热刷新连发、相同fingerprint、base删除/安全变更 | 串行/epoch保真，只退休自己的generation，旧更新不覆盖新策略 |
| T13 | 启动等root时卸载、register飞行中卸载、重复dispose | 无卸载自等待、无残留注册/监听、无未处理rejection |
| T14 | registry已有另一个governance id | 拒绝冲突，不覆盖/删除对方 |
| T15 | 独立无旧marker的外部项目运行hooks/resolve_entry | workflow-home定位正确；不得依赖过期HOME目录；暂停WIP不变 |
| T16 | old0.1.5-rc.3能力fixture；历史rc.1不可复验 | 自动运行明确 UNSUPPORTED，无旧 writer 调用；区分历史材料和当前实测，不补称旧运行支持 |
| T17 | native缺服务/未知host API形态；存在旧目录残留 | unsupported/NOT_RUN；不调用旧writer，不清HOME |
| T18 | schema零可校验/工具缺失/offline doctor/主动卸载 | 不误PASS；目录残留!=当前登记；offline不声称runtime |
| T19 | 真实governance读取skill/shim、spawn/fork、goal、ask-user参数schema | 现有工具保真；通过无需付费模型的宿主harness部分与需真人/模型部分分开，未跑明确NOT_RUN |
| T20 | install/boot/refresh/uninstall所有sandbox快照 | 写入只限隔离HOME/包目标；真实HOME和已安装DSH源码散列不变 |

安装态 schema + 真实 Cordis 挂载是本版最低发布验收；需要模型/真人的原生交互无法在隔离 harness完成时必须披露，不得把其NOT_RUN补为passed。current-web为优先；desktop/chatgpt profile 未读取/启动，不声明全部profile支持。

## 10. 非功能与蓝军挑战

| 非功能 | 对应措施 |
|---|---|
| 安全/数据 | native零HOME写入；只处置自己register返回的disposer；不改base；原生安全策略逐字段保留；未知形态拒收 |
| 可用性 | 本插件warn-only/unsupported，普通DSH继续；registration broken清晰诊断，停在自己的边界 |
| 可维护/扩展 | 仅两个自有差量；公开Loader+registry能力协议；同版迁移无需版本marker；host tool新字段保真 |
| 性能 | 一次settled扫描+深拷贝/比较；无每轮或每次工具调用扫描；reload合并，相同fingerprint无重挂 |
| 可观测 | RuntimeOutcome四面、sourceAddress/resolutionBase/fingerprint、逐oracle路径、readiness日志；证据不混级 |
| 测试性 | source/overlay纯函数+生命周期fake负例+真实宿主隔离mount；当前版本和升级变体双矩阵 |

- **BC-1：未来registry删除register或Loader结构变了怎么办。** 能力协商拒收自己，报告缺能力；旧目录不fallback。支持范围不是万能兼容承诺；T17。
- **BC-2：新standard采用不同工具或用户关掉某权限怎么办。** 整树取已接受config，除两个差量原样保留；复杂persona/roots策略冲突拒收，不 resurrect disabled；T05/T06/T09。
- **BC-3：插件载入/卸载时root await把自己锁死怎么办。** activation 只能等经证明的下游登记链，不调用自包含 root await/diagnostic；cleanup 不等待启动任务；控制器stopped/epoch/late disposer约束；A2-1～4、T10/T13为先行/合入硬门。
- **BC-4：链接安装没有host依赖/CLI两套版本混了怎么办。** B不裸import宿主包；probe从确证CLI/profilecontext解析，同源oracle；T01/T02。
- **BC-5：旧HOME文件存在令诊断过绿怎么办。** native按声明/运行分面；legacy-residue不等于登记；T18。
- **BC-6：有效树source读到刚失败的raw配置怎么办。** 用公开Fiber.config，在不自等待的审计点验证base无broken；该点与初始准入如何衔接未证，A2-3不能删减；不把Entry.options当accepted config；T08。

以上为 Architect 自挑战；独立蓝军/Bar Raiser 尚待 Coordinator 委派，不能自批通过。

## 11. 迁移、回滚与发布后重装

迁移按**设计审查 → S-A隔离可行性 → 实现+独立审查 → CI/版本发布 → 重装**推进，不提前写用户profile。

- native保留presetId=governance；旧目录作为用户数据完整保留，不自动导入、清空、改名或删除。当前旧文件只用于残留诊断。
- 若用户profile曾选governance，现已卸载导致该id不可用属预期；发布后重装才恢复。已开始的会话不能因迁移强制切换；新session选择新版governance，历史会话重启恢复规则由宿主承担。
- legacy 自动运行明确 UNSUPPORTED；未复验的历史运行材料仍标 NOT_RUN。新版本不得调用旧 delete+rename writer去“修复”原 HOME。
- Git回滚只revert本任务独立提交；不要reset/drop其他0.99 WIP。若新adapter自身失效，停用/移除本包bundle即可恢复普通DSH；不用回滚整个宿主或手改宿主源码。
- 卸载native以Cordis disposer撤回登记；不扫描/清理用户目录。隔离sandbox由任务拥有，清理需验证绝对路径在sandbox内。
- 发布后重装材料须固定已发布artifact/ref：当前package.private=true，不能假设npm已发布。优先已发布tag checkout后用 `dsh plugin --profile web add link:D:/AI/agent/claude/coding/project_management_workflow`，或经验证tgz路径。精确install spec由发布产物决定，禁止虚构registry版本。
- 该真实环境命令由Coordinator在发布成功且当前授权仍适用后执行/交付；执行前按真实环境R1完整备份profile元数据/一致性校验或用户逐项授权，不删原HOME目录。不得把测试sandbox中的初始化当真实重装成功。
- 重装后验证：本包唯一登记、普通preset不变、governance READY、skill/shim可读、无启动错误；UI/真人工具缺证据继续标NOT_RUN。

## 12. Proposed ADR（由 Coordinator 机录）

**标题**：以公开有效预设声明派生替代DSH静态全量模板及目录交付  
**日期**：2026-10-16；时序修订 2026-10-17；候选 L 失败回灌及 G 提案 2026-10-18  
**背景**：DSH当前0.2退休目录扫描；项目旧adapter仅写目录且复制整套标准工具行、只按自身版本刷新，形成宿主升级与路径变动失效。用户先要求适配和解耦，且主动卸载并要求发布后再装。  
**推荐决策**：保留公共 Loader/registry 边界及 persona/roots 内容策略；G 当前形态取消门失败，不再作为可接线实现。§15 建议独立审查 U 的 caller-owned 取消终态/读取唤醒/发布 fence 上游协议需求，Coordinator 就隔离补丁范围取得用户明确授权；该协议待实现，当前没有 runtime 适配完成的决策。  
**备选方案与排除**：A静态声明继续维护工具副本；C公共组合reader可行但增加模块解析和运行态一致性面；D全局注入违反预设隔离。  
**影响范围**：lib入口及三个自有模块、host-contract与infra探针/doctor/launch/boundary、adapter文档/manifest和测试；不得改宿主源码，不触碰暂停FIX-445字节。  
**后果/风险**：S-A 暴露 boot 后登记不可见；S-A2 的 Loader await intercept 候选 L 实测首 lookup 失败，已退出。新 G 提案需要 guard+gated wrapper 的显式基础设施差量，在保持两个业务内容差量之外改变树结构；其 seed/accepted 审核、公开解析、无环及真实卸载全部待 S-A3 证伪，不能把源码构件等同方案可用。C/F 保留，H 当前缺少所需公开 setup/加法挂载契约；旧自动运行按 R0 明确 UNSUPPORTED_NO_AUTOWRITER。  
**可逆性**：可逆产品接线；保留旧目录用户数据，回滚只移除本包原生row或revert本任务提交。  
**后续动作**：同一 Design Reviewer R4 审查 §15 的 caller-owned 取消协议需求；Coordinator 就隔离上游补丁范围取得明确授权后才实施。缺接口时继续独立 CI/工具链，适配目标不标完成；上游与本项目集成门均通过后再解锁产品/0.99发布和发布后重装。  
**审查结论**：R0/R1/R2 仅分别准入三次隔离切片；G 取消门 FAIL，R3 NEEDS_CHANGE/1，R4 PENDING。产品接线 BLOCKED、runtime NOT_RUN，新探针/宿主改动/风险接受均未授权。  

## 13. 2026-10-17 时序修订的外部只读命令审计

本修订未启动宿主或重新运行场景；下列均只读安装态 SDK。UTC 由各命令执行时打印；退出码来自工具完成结果。源码支持候选可提案，不等于 S-A2 通过；S-A 原失败轨迹保持原文件完整不变。

```json
[
  {
    "id": "REV-RO-01",
    "started_utc": "2026-10-16T23:50:38.0181662Z",
    "cmd": "$revStarted=[DateTime]::UtcNow.ToString('o'); Write-Output $revStarted; $revSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$revSdk/cordis-plugin-loader/lib/index.js\" | Select-Object -Skip 105 -First 75; Get-Content -Encoding UTF8 \"$revSdk/cordis-plugin-loader/lib/index.js\" | Select-Object -Skip 710 -First 160; Get-Content -Encoding UTF8 \"$revSdk/cordis/lib/types/fiber.d.ts\" | Select-Object -Skip 20 -First 150",
    "exit_code": 0,
    "impact_paths": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "exit_semantics": "shell exit; searches piped through Select-Object may return no matches without changing shell exit",
    "query_note": "The requested Loader skip-710 slice was beyond that installed file's end; it returned no lines. Correct implementation slices were read in REV-RO-04/05; no absence inference."
  },
  {
    "id": "REV-RO-02",
    "started_utc": "2026-10-16T23:50:38.0496217Z",
    "cmd": "$revStarted=[DateTime]::UtcNow.ToString('o'); Write-Output $revStarted; $revSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$revSdk/dsh-agent-preset/lib/index.js\"; Get-Content -Encoding UTF8 \"$revSdk/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 480 -First 100; Get-Content -Encoding UTF8 \"$revSdk/dsh-app-boot/lib/index.js\" | Select-Object -Skip 4055 -First 55",
    "exit_code": 0,
    "impact_paths": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "exit_semantics": "shell exit; searches piped through Select-Object may return no matches without changing shell exit"
  },
  {
    "id": "REV-RO-03",
    "started_utc": "2026-10-16T23:50:38.1049254Z",
    "cmd": "$revStarted=[DateTime]::UtcNow.ToString('o'); Write-Output $revStarted; $revSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n 'async await|async apply|async start|\\.apply\\(|async init|async update|inertia|pending|runner' \"$revSdk/cordis/lib/index.js\" | Select-Object -First 90; Get-Content -Encoding UTF8 \"$revSdk/cordis-plugin-loader/lib/types/config/entry.d.ts\"",
    "exit_code": 0,
    "impact_paths": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "exit_semantics": "shell exit; searches piped through Select-Object may return no matches without changing shell exit"
  },
  {
    "id": "REV-RO-04",
    "started_utc": "2026-10-16T23:50:50.1508675Z",
    "cmd": "$revStarted=[DateTime]::UtcNow.ToString('o'); Write-Output $revStarted; $revSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$revSdk/cordis/lib/index.js\" | Select-Object -Skip 1035 -First 80; Get-Content -Encoding UTF8 \"$revSdk/cordis/lib/index.js\" | Select-Object -Skip 1325 -First 90; rg -n 'async init|async _init|init\\(|class EntryGroup|async update|Promise.all|ctx.plugin' \"$revSdk/cordis-plugin-loader/lib/index.js\"; Get-Content -Encoding UTF8 \"$revSdk/cordis-plugin-loader/lib/index.js\" | Select-Object -Skip 510 -First 200",
    "exit_code": 0,
    "impact_paths": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "exit_semantics": "shell exit; searches piped through Select-Object may return no matches without changing shell exit"
  },
  {
    "id": "REV-RO-05",
    "started_utc": "2026-10-16T23:51:04.8358689Z",
    "cmd": "$revStarted=[DateTime]::UtcNow.ToString('o'); Write-Output $revStarted; $revSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$revSdk/cordis-plugin-loader/lib/index.js\" | Select-Object -First 110; Get-Content -Encoding UTF8 \"$revSdk/cordis-plugin-loader/lib/index.js\" | Select-Object -Skip 430 -First 80; Get-Content -Encoding UTF8 \"$revSdk/cordis-plugin-loader/lib/types/index.d.ts\" | Select-Object -First 140; rg -n 'async function mountPreset|async function auditRows|async resolve|async retain|async mount' \"$revSdk/dsh-agent-preset-registry/lib/index.js\"",
    "exit_code": 0,
    "impact_paths": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "exit_semantics": "shell exit; searches piped through Select-Object may return no matches without changing shell exit"
  },
  {
    "id": "REV-RO-06",
    "started_utc": "2026-10-16T23:51:32.5296869Z",
    "cmd": "$revStarted=[DateTime]::UtcNow.ToString('o'); Write-Output $revStarted; $revSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$revSdk/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 190 -First 130; Get-Content -Encoding UTF8 \"$revSdk/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 598 -First 60; rg -n 'namespace Inject|interface Inject|type Inject|function Inject' \"$revSdk/cordis/lib/types\" -g '*.d.ts'; rg -n 'await: true|loader:.*await|loader.*await: true' \"$revSdk\" -g '*.js' -g '*.yml' -g '*.json' | Select-Object -First 25",
    "exit_code": 0,
    "impact_paths": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "exit_semantics": "shell exit; searches piped through Select-Object may return no matches without changing shell exit"
  }
]
```



## 14. 2026-10-18：S-A2 失败回灌及 R2 候选提案

### 14.1 退出 L，保留失败事实

`docs/diagnostics/dsh-native-admission.md` 的最终结论为 `FAIL_CANDIDATE_L`。正常冷启动、own 最前行，真实 boot 已返回，Loader tasks=0，own PENDING/inertia=false/activationCount=0；首条固定 governance lookup 为 not-found。两次 raw 是同一失败场景的采集及状态补充，schema_checked=0；后续 base/broken、mount、候选真实卸载均 NOT_RUN。root fixture disposer 完成不等于 L 卸载门通过，也没有证明 own 会永久 PENDING 或认定宿主有缺陷。

L 已触发 R1 退出门，停止扩展；不得手工 notify、Entry.init、重排行或缩小 microtask 窗口来补救。S-A 20 场景/38 schema 的有限 fixture 与其时序 FAIL、S-A2 两次失败 raw 全部保留，均不被本设计改写。2026-10-18 只读 package manifest 仍为 DSH 0.2.0-rc.2；本轮未启动宿主，不能将源码复核当新运行验收。

后续候选必须同时解决 admitted/ready、accepted config 与 broken 拒收、真实 dispose 的等待方向；没有已验证公开无环方案前产品接线状态为 BLOCKED，运行支持 NOT_RUN。此处 BLOCKED 是产品设计条件，非 Coordinator 自动目标状态变更。

### 14.2 新复核的公开事实（SOURCE，不等于运行通过）

本次 SDK 仍为 0.2.0-rc.2。以下事实于 2026-10-18 重新只读核对，不回填上次中断调查的缺失时间。

| 事实 | 公开入口/源码 | 能证明与限制 |
|---|---|---|
| S3-1 | Loader EntryGroup 类型公开 data；update 先设置 this.data=config，再并发 create 各行 | 这是该 group 当前组合输入的完整列表，可以在子行尚未启动时读；它不是“全部嵌套 Include 已展开”或 accepted Fiber.config 的保证。不能称为已经接受的运行快照。 |
| S3-2 | EntryTree.import 使用当前树 resolution base；native AgentPreset 公开 Config，且标记 EntryGroup.key | 可经当前 tree.import 取得真正 native runtime，再用同 context 的公开 resolveConfig 独立验证声明；plugins 中表达式应保留，不能自行提前求值。异步 import 的完成点必须属于初始准入证明。 |
| S3-3 | registry 公开 export livePresetMounts/auditRows；类型要求 live mounts 以当前 runtime root Fiber 限定 | 无需私读 definitions/_config 就有检查挂载的公开入口；历史 revision 可同时存在，不能把任意同 id mount 当成当前 revision。G 的主审计优先使用 root settle 后的公开 resolve(baseId)，不靠猜当前 mount。 |
| S3-4 | PresetTree 构造函数保存并恢复 owner.subtree/subgroup，write 空实现 | 当前实现刻意不把 standing preset tree 接入 host entry 子树。这给“preset guard 等 host settle，而 host 不等 standing guard”的候选提供源码依据；这是内部实现事实，产品只调用公开 API，必须以真实 runtime 证伪，未来不承诺。 |
| S3-5 | register 在 await activate 前同步建立 record；activate 等 mountPreset/auditRows，失败变 broken；resolve/retain 等 record.ready | 可以提出“先建立不可使用的 pending record，再由真正激活门决定是否可用”；不能让非法 payload 先激活并异步撤回。正常返回 disposer 仍不等于 READY。 |
| S3-6 | Web composeAgent 在传入 Agent setup 前先 resolve，setup 唯一调用 presets.mount(agentCtx,id)。public mount 的 bind 对同一 key 保存一个 generation，再次 mount 是 rebind | 普通 native row 在 standing preset 激活时运行，并非每个未发布 Agent 的 setup hook。public mount 不是已证明的多 preset 合并 API；H 的嵌套挂载/identity 保真不能凭 API 名称推断。 |
| S3-7 | public ProfileContext 含 dir/installAnchor/home/overlays；readProfilePatches 读取当前 bundle/profile/home，再合入启动 overlays；composeEntries 以空根应用 patch | C 不需要猜 argv/profile，但它重读现在的文件，不是已启动那次 generation 的冻结输入；raw 更新失败和读写竞争下不能直接当 accepted config。 |
| S3-8 | Fiber._reload 等 plugin effect 完成；真正 dispose 在 inertia 后才运行 disposers | own activation 不得 await mount/guard/base lifecycle。即使只做 SDK import，也须证明有界失败及卸载行为；“cleanup 未 await”不能当框架已能先执行 cleanup 的证据。 |

### 14.3 候选重新评估

评估顺序沿用安全/无等待环 → 首个实际 lookup 准入 → 有效 base 与失败更新保真 → 公开 context/隔离 → 成本。M 不凭调度缩微复活，L 已实测退出。以下均是设计提案，未授权运行或产品接线。

| 候选 | 明确机制 | 优点与代价/未解点 | 裁定 |
|---|---|---|---|
| G：组合输入 seed＋原生激活 guard | 在 own 的普通 activation 中读取同一公开 group 的组合输入，独立 native Config 校验；只等必要 SDK import，不等 base/root/mount。同步调用 register 建立 pending record 后立即释放 own activation。自有 guard 在 standing tree 中等待 host settle，核对真实 accepted base 与 seed、审计 base，然后才放行隔离 payload group。 | 可把“record 可见”与“payload 可用”分开，避免 own activation 等 mount 的卸载环；不重新读取用户文件。**需要增加 guard 和 gated wrapper，是原两差量合同的显式候选变更**；完整树证明、表达式/上下文、模块解析、scope/service 泄漏、取消/late disposer 都需先证伪。 | 优先提请 R2 允许最小 S-A3，仅当前受限 native tree；没有实测可行性，不批准产品。 |
| C-G：public ProfileContext reader＋相同激活 guard | 经当前 tree.import 的 app-boot，调用 readProfilePatches(context)/composeEntries 得 seed；其余与 G 相同，post-settle guard 必须与 accepted declaration 比较。 | 可在树未展开时取得当前 profile 全部声明；无 argv 猜测。但多读取 bundle/profile/home，有文件竞态、运行旧 generation/磁盘新 generation、兼容 preflight 和 Include 覆盖差异；比 G 多一个来源/解析面，仍需 guard，不能单靠 reader 解决时序。 | 保留备选 NOT_RUN，不在 G 失败后自动切换；没有准确 context 或 snapshot 一致性即拒收。 |
| F：只等待已有 base Fiber | own activation 有界等待宿主已经启动的唯一 base Fiber，再派生；不得 Entry.init/改行顺序。 | 公开 API 小，但未出现的 Fiber、尚未展开的树与唯一性无保证；若 await base 等到它 mount 完成，真实 dispose 会等 own inertia，仍须证明取消。只适用于已预载的受限启动。 | NOT_RUN；不满足冷启动条件时直接拒收，不能作为本版通用解。 |
| H：治理桥接 preset 在 Agent setup 内再 mount standard | 需要治理 exclusive 的公开 prepublication setup 扩展点，并需“第二个 mount 增加能力但保留 governance identity”的协议。 | 已核源码：Web setup 为调用方提供、native rows 在 standing tree 激活；本轮未找到“preset row 追加该 setup”的公开契约。对同一 scoped key 再 mount 会 rebind generation，非加法合并；在 standing scope 偷调 mount 也偏离“未发布 Agent setup”的公开契约。覆盖、skills provider、fork identity/事务回滚仍未证。 | **当前公开契约依据不足，SOURCE_REJECTED_AS_PRIMARY**。不是实测嵌套 mount 失败；不运行 H、不劫持 factory/setup、不全局 agent/created 补挂。未来有真正公开 hook/组合 API 才另提案。 |

### 14.4 G 的明确合同变更与协议草案

G 保留对 base 业务字段的两个内容差量（persona.prefix、两个 skill roots），但**派生 entry tree 不再只有这两个结构变化**：新增本包 guard row 与一个 gated payload group/私有 readiness realm。未经 R2 明确批准，原 §3/§4 的严格“两差量、其余行位置均原样”合同不得被悄悄解释成已允许。wrapper 对 relative entry 地址、isolate 继承和表达式上下文的影响也是先行硬门。

1. **Seed 不是 BaseSnapshot**：新输入 `InitialSeed={source:'loader-group-input',treeBase,groupAddress,baseRowAddress,normalizedNativeConfig,sourceFingerprint,scopeLimit}`。只能从 own entry 所属公开 parent/tree/root 的 data 拷贝；要求 own 所在组合平面确定、base 声明唯一且其来源覆盖可证明完整。首试验仅支持同一组合 group 中直接原生声明及可完整遍历的 literal group。未知 Include/动态声明/跨树未展开依赖直接 `SOURCE_SCOPE_UNSUPPORTED`；不借已出现 entries 猜“没有重复”。未支持的 tree 不能通过回退默认 standard/别的 profile。
2. **同 context 真实校验**：只经公开 selected tree.import 加载 native declaration runtime/公开 resolveConfig，规范化 seed；不 bare import SDK，不复制 native schema，不安装宿主依赖。schema 只保证声明形状，不等于 accepted/broken 通过。SDK import 是 own activation 唯一允许的异步准备；不 await root/base Fiber/register 完成。import 拒绝/有界准备期限失败只拒收本插件；卡住 import/卸载的行为仍须 S-A3，若不能满足有界收敛就候选失败。
3. **先准入，后激活，不先放开 payload**：lifecycle 建立 generation state，构造派生 definition，并在 own activation 结束前调用 public register。调用返回 Promise 后立刻安装完成/拒绝处理，不 await 它；own activation 返回自己的 cleanup。当前 register 的同步 record 写入提供 admitted 因果依据；不能在 register 调用之前安排 detached 任务、额外 admission delay 或手工刷新 Loader。
4. **guard 必须真正阻止 payload 启动**：仅把一个 async guard 与原 rows 并排不够，Loader 会并发启动其它 rows。候选结构为本包隔离 frame，包含 guard 及 gated payload group；后者通过公开 group.inject 等待专属 readiness service。guard 不提供该 service，直到审核成功。原 base rows 克隆后只做两个内容差量，放在该 group 内；不改 vendor 行或 provider。readiness service 只在本包 frame 的私有 isolate realm，绝不能落到 host root 或普通 preset；不新增 model-visible tool/skill。
5. **审核不能自包含**：own activation 已结束，host root 等待链不包含 standing guard（S3-4 的实现事实须实测）。generation 的异步 audit 此时等待真正 host loader.await，重新定位恰好一个有效 base Fiber，比较 public Fiber.config/有效 disabled/同一来源与 seed 的规范化语义，再调用 public registry.resolve(baseId) 无 broken；必要 public mount audit 必须限定当前 runtime，不把退休 revision 当当前。差异、失败更新、pending/disabled/duplicate/broken 全部拒收。guard 审核失败时抛错，registry 保持 broken/invalid；payload 始终未启动，未发布 Agent 不可使用治理能力。不是“先登记可使用的无效派生，再异步撤回”。
6. **取消和清理**：own cleanup 先 stopped/epoch失效，取消 generation permit、移除监听和自有 state；不 await root audit 或尚未完成的 register。guard 的等待须可由取消立即拒绝，不依赖 host barrier 释放。已返回 disposer 则处置；迟到 disposer 立即处置，所有 rejection 消费。真实 Fiber.dispose 必须在 mount barrier 释放前完成 own cleanup/卸载；其后释放 barrier 的 drain 验证无残留。SDK import 阶段的实际框架行为必须另行记录，不能沿用 S-A cleanup PASS。
7. **READY 不改口径**：只有 guard 审核放行、真实 payload mount 无 broken、compose 成功才 READY。invalid/unsupported 的诊断可包含治理 id 的 broken 记录，但不算可用支持。用户普通 standard 不变；本包卸载、真实 HOME、暂停 FIX-444/445 约束保持。

建议接口边界：`prepareSeed(tree,scopeLimit) -> InitialSeed|SourceError`、`derive(seed,policy,generationId) -> GuardedDefinition`、`auditAccepted(seed,hostCtx,signal) -> Permit|AuditError`、`generationState.create/cancel/awaitPermit`。generation state 是本包进程内 Promise/nonce 表，不是读写 host 私有表；Entry config 仅携带可序列化 generationId，不塞函数/ctx/Promise。缺 state、旧 epoch 或重复 nonce 均失败。

新增职责只有：guard module 等 permit 后在局部 realm 提供 readiness；state module 管理本包 generation permit/cancel，不依赖宿主。DAG 为 entry→lifecycle→source/overlay/state；guard→state；source→public Loader；lifecycle→public registry/audit。guard 不反向 import lifecycle/source，state 不 import host；模块环=0。已有 modules/§3.1 图仅在 G 获准后按此增量调整，不能提前宣称产品已有这些文件。

### 14.5 S-A3 最小可证伪准入提案

R2 只能授权明确的 `S-A3_G_ONLY`（若 Reviewer 接受合同变更），不能顺带授权 C/F/H 或产品。所有运行限 repo sandbox，manifest 只作为工具参数；产品 runtime 的解析必须通过当前 Loader context 实证，不能再次用 harness manifest createRequire 冒充 link 安装通过。

| 先行门 | 最小观察与判败条件 |
|---|---|
| A3-0 结构/解析 | 真实 Cordis/group/native/registry；parent group.data 中 direct standard 与 own 行首/末；native Config 同 tree.import。先记录 normalized seed 与后续 accepted config。冷启动没有 own activation、tree 尚不完整、解析跨 context 即 FAIL，不重试/notify。保留 repo 无 host node_modules。 |
| A3-1 首 lookup | 实际 boot 后第一条固定 governance list/resolve，及真实 Web 显式/default create；不等自有 READY。在 SDK import 的唯一准备点暂停，boot 不应先越过 admitted；调用 register 后对 mount/audit 分别事件延迟，真实 lookup 必须由 record.ready 等待。任何 not-found 或依赖 mkdir/I/O 才成功即 FAIL。 |
| A3-2 有效 base/零提前 payload | raw 新值失败但旧 Fiber 仍有效、base缺失/重复/disabled/broken/pending、seed与accepted不一致、profile覆盖/!!js。以 sentinel 观察 guard 放行前 payload 无任何 apply/tool/prompt/skill side effect；审核拒绝时始终不启动。若只能先使用再撤回、只检 schema 或忽略 broken，FAIL。 |
| A3-3 等待图/卸载 | host启动屏障、guard audit屏障、register飞行和SDK import准备阶段分别真实 Fiber.dispose；记录 dispose-request、cleanup-start/complete、dispose-complete、各release及late-dispose。除已明确有界的 module准备失败外，不得靠先释放被等待屏障才清理成功；准备期限不能把失败变PASS。root与guard互等、frame provider失效重启、取消不传播均FAIL。 |
| A3-4 隔离/保真 | 私有 readiness service 不泄漏；普通 standard 配置、skills/provider、两个并行会话及 dispose 不变。wrapper 对 disabled !!js、已有 isolate/group、相对路径/entry地址保真；任何未知 shape 明确拒收。真实 payload schema 必须非零，故意坏注册不报READY。 |
| A3-5 完成与退出 | 全 raw、实际模块路径、scope限制、失败和NOT_RUN逐项返回；完整 current-web/link/skills/refresh/tools 仍须后续验收。首个正常冷启动或任一安全/无环硬门失败即停止 G，回同 Reviewer，不转 C/F/H，不换 fake registry、不删矩阵门。 |

蓝军补充：**BC-7** raw seed 与接受值不一致→guard 必须阻止 payload，不能用 schema 顶替；**BC-8** guard 与payload并排→并发可提前启动，必须验证真正 inject gate及私有realm；**BC-9**把 guard 接回 host tree/在 own activation 等 register→形成 root环或真实卸载等待，A3-3直接判败；**BC-10**嵌套 mount 覆盖 identity→H 当前不具公开加法协议，不进入试验。

当前结论：G 有可复查的公开构件与明确等待图，但**整体可行性/实际无环/数据安全仍 NOT_RUN，产品接线 BLOCKED**；只建议独立 R2 裁定合同变更和上述最小 S-A3。若 Reviewer 认为公开构件不足，就保留 BLOCKED 并记录缺少的宿主协议，不拼接未证假设、不要求真实环境重新安装试错。

### 14.6 本轮外部只读命令审计

2026-10-18 重新执行五条 SOURCE 读取；命令 UTC 为当次打印，未补造上次限额中断调查的时间。本轮不调用宿主运行，不读取用户 profile，不作外部写入。

```json
[
  {
    "id": "R3-RO-01",
    "started_utc": "2026-10-18T11:57:56.9086031Z",
    "cmd": "$r3Started=[DateTime]::UtcNow.ToString('o'); Write-Output $r3Started; $r3Host='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh'; Get-Content -Encoding UTF8 \"$r3Host/package.json\" | Select-Object -First 34; $r3Sdk=\"$r3Host/node_modules/@deepseek-ai\"; Get-Content -Encoding UTF8 \"$r3Sdk/cordis-plugin-loader/lib/types/config/group.d.ts\" | Select-Object -First 42; Get-Content -Encoding UTF8 \"$r3Sdk/dsh-agent-preset/lib/index.js\" | Select-Object -First 40; Get-Content -Encoding UTF8 \"$r3Sdk/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 65 -First 48; Get-Content -Encoding UTF8 \"$r3Sdk/dsh-agent-preset-registry/lib/types/mount.d.ts\" | Select-Object -First 40; Get-Content -Encoding UTF8 \"$r3Sdk/dsh-agent-preset-registry/lib/types/index.d.ts\" | Select-Object -First 25",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh"
    ],
    "impact_write": [],
    "access": "read-only installed SDK source; no host process/profile read/write",
    "exit_semantics": "shell completion code; piped searches and explicitly suppressed optional reads do not prove absence"
  },
  {
    "id": "R3-RO-02",
    "started_utc": "2026-10-18T11:58:52.0111340Z",
    "cmd": "$r3Started=[DateTime]::UtcNow.ToString('o'); Write-Output $r3Started; $r3Sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$r3Sdk/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 635 -First 105; Get-Content -Encoding UTF8 \"$r3Sdk/dsh-agent/lib/index.js\" | Select-Object -Skip 325 -First 100; rg -n 'composeAgent|agentPresets.mount|setup:|agentPreset' \"$r3Sdk/dsh-api-session-controller/lib/index.js\" | Select-Object -First 40; Get-Content -Encoding UTF8 \"$r3Sdk/dsh-agent-preset-registry/lib/types/preset.d.ts\" | Select-Object -First 130",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh"
    ],
    "impact_write": [],
    "access": "read-only installed SDK source; no host process/profile read/write",
    "exit_semantics": "shell completion code; piped searches and explicitly suppressed optional reads do not prove absence"
  },
  {
    "id": "R3-RO-03",
    "started_utc": "2026-10-18T11:58:52.0219340Z",
    "cmd": "$r3Started=[DateTime]::UtcNow.ToString('o'); Write-Output $r3Started; $r3Sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$r3Sdk/cordis-plugin-loader/lib/index.js\" | Select-Object -Skip 74 -First 21; Get-Content -Encoding UTF8 \"$r3Sdk/cordis-plugin-loader/lib/index.js\" | Select-Object -Skip 208 -First 25; Get-Content -Encoding UTF8 \"$r3Sdk/dsh-app-boot/lib/types/profile-context.d.ts\" | Select-Object -First 66; Get-Content -Encoding UTF8 \"$r3Sdk/dsh-app-boot/lib/index.js\" | Select-Object -Skip 986 -First 50; Get-Content -Encoding UTF8 \"$r3Sdk/cordis/lib/index.js\" | Select-Object -Skip 1347 -First 58",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh"
    ],
    "impact_write": [],
    "access": "read-only installed SDK source; no host process/profile read/write",
    "exit_semantics": "shell completion code; piped searches and explicitly suppressed optional reads do not prove absence"
  },
  {
    "id": "R3-RO-04",
    "started_utc": "2026-10-18T11:59:10.3082240Z",
    "cmd": "$r3Started=[DateTime]::UtcNow.ToString('o'); Write-Output $r3Started; $r3Sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$r3Sdk/dsh-api-session-controller/lib/index.js\" | Select-Object -Skip 352 -First 26; rg -n 'interface Events|setup|created|before|create' \"$r3Sdk/dsh-agent/lib/types/index.d.ts\" | Select-Object -First 70; Get-Content -Encoding UTF8 \"$r3Sdk/dsh-agent/lib/types/index.d.ts\" | Select-Object -First 140; rg -n 'agent/setup|agent/before|agent/created|options.setup|config.setup|setup\\(' \"$r3Sdk/dsh-agent/lib/index.js\" \"$r3Sdk/dsh-agent-loop/lib/index.js\" | Select-Object -First 55; Get-Content -Encoding UTF8 \"$r3Sdk/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 498 -First 73; Get-Content -Encoding UTF8 \"$r3Sdk/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 190 -First 34",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh"
    ],
    "impact_write": [],
    "access": "read-only installed SDK source; no host process/profile read/write",
    "exit_semantics": "shell completion code; piped searches and explicitly suppressed optional reads do not prove absence"
  },
  {
    "id": "R3-RO-05",
    "started_utc": "2026-10-18T11:59:39.3341635Z",
    "cmd": "$r3Started=[DateTime]::UtcNow.ToString('o'); Write-Output $r3Started; $r3Sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n -C 3 'group:|planning|compaction|delegation' \"$r3Sdk/dsh-web-app/presets/standard.patch.yml\" | Select-Object -First 85; Get-Content -Encoding UTF8 \"$r3Sdk/cordis-plugin-loader/lib/types/registry.d.ts\" -ErrorAction SilentlyContinue | Select-Object -First 20; Get-Content -Encoding UTF8 \"$r3Sdk/cordis/lib/types/registry.d.ts\" | Select-Object -First 42; Get-Content -Encoding UTF8 \"$r3Sdk/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 258 -First 37",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh"
    ],
    "impact_write": [],
    "access": "read-only installed SDK source; no host process/profile read/write",
    "exit_semantics": "shell completion code; piped searches and explicitly suppressed optional reads do not prove absence",
    "query_note": "One optional guessed types/registry.d.ts read under cordis-plugin-loader was nonexistent and suppressed; only real cordis/lib/types/registry.d.ts output used."
  }
]
```

## 15. 2026-10-19：R3-B1 所有权缺口与最小上游协议提案（R4 待审）

### 15.1 当前结论与保留证据

**当前公开组合未找到满足 R3-B1 的提前撤回协议；G 当前形态退出，产品接线仍 BLOCKED。** 不是把“不支持”作为用户要求的适配完成。R3 为 NEEDS_CHANGE/1；本节仅提出可审查的依赖补齐方案，不授权宿主补丁、升级、新探针、风险接受、产品接线或发布。

G 的有限自然首启动、真实 payload gate/compose 通过保留；permit 已放行后 payload activation 仍 flight 时，真实 own cleanup/dispose 完成，但新 resolve 仍等待 record.ready，750ms 观察 FAIL。失败后才释放 barrier、获得 late disposer。6 schema、0 unhandled 不能抵销取消失败；没有取消后 Agent 成功、数据损坏或永久挂死的实测。list 以 Promise.all 等全部 diagnostic 可能拖住 roster 是源码推导，不是 UI 卡死实测。原 S-A/S-A2/S-A3 及 R0～R3/raw/prototype 均不修改。

当前 registry.register(definition) 同步建立 record，随后 await activate/record.ready 才返回 unregister；scope 由 registry owner 创建。diagnostic/resolve 等 ready；取消自有 permit、不再等待本地 Promise 或撤回 readiness provider 都不取得 registry record 的关闭权。公开 live mounts 在挂载审计后才出现。C/F 的 source 改造、H 的挂载设想、原生声明 row 都不改变这个所有权问题；不再启动一轮相同本地候选。

### 15.2 官方发布物核查：升级本身尚无解锁依据

2026-10-19 只读官方 npm 元数据及两个精确版本 tarball，内容仅在内存解包，校验 dist.integrity，不安装、不执行包、不写文件。网页工具直接 open registry 失败后使用只读 HTTP；失败不据此推断包不存在。完整命令见 §15.7。

| 面 | 核查事实 | 对本任务的含义 |
|---|---|---|
| 本机 fresh | DSH/registry 0.2.0-rc.2，Cordis 4.0.5，Loader 1.0.6；本机 registry JS/types SHA256 与官方同版本包相同 | 不是某个本地遗留私改造成当前公开签名差异。版本和 SOURCE 不冒充新 runtime 验收。 |
| 官方 dist-tags | registry latest=0.1.7-alpha.1、alpha=0.2.1-alpha.5、next=0.2.1-rc.2；CLI latest=0.2.0-rc.2 | latest 标签不代表最高或所有未来版本；不能只比较一个 latest 字段。 |
| registry 0.2.1-rc.2 | types:44 仍为 register(definition):Promise<disposer>；JS:470～493 仍 await ready 后返 disposer，:533 起 diagnostic 仍先 await ready，:570 起 list 仍 Promise.all | 已发布 next 中也没有找到所需早期关闭能力；未运行该版本，不能宣称其 runtime 必败/已兼容。单纯升级没有解除 R3-B1 的源码依据。 |
| 新版检查 API/依赖 | next 增加只读 inspectCompositions，旧 livePresetMounts 等导出变化；peer 指向整套 0.2.1-rc.2，app-boot 也为该版 | inspect 不是取消句柄；不得混装单个 registry 覆盖当前宿主。选择新版须作为完整隔离宿主基线另行批准、审查和验证。 |

可复查主源：[官方 registry 元数据](https://registry.npmjs.org/@deepseek-ai%2fdsh-agent-preset-registry)、[0.2.1-rc.2 精确包](https://registry.npmjs.org/@deepseek-ai%2fdsh-agent-preset-registry/0.2.1-rc.2)、[CLI latest 元数据](https://registry.npmjs.org/@deepseek-ai%2fdsh/latest)。官方 tarball SHA256：0.2.0-rc.2=`06890db5db5af002f6f70ed44fedc40061bdfa96abcd003ab00377ce5d14df8f`；0.2.1-rc.2=`ee67df6d09173d9f51bc02451cae58d02ff953ddeb677a182d41551c2e386496`。这不是选定新的最低支持版本；未检查的发布物/未来能力仍 UNKNOWN。

### 15.3 先列机制与证伪点，再作推荐

| 机制选择 | 可实现责任边界/代价 | 证伪点与裁定 |
|---|---|---|
| U：上游提供调用方拥有、立即可关闭的 registration lease | registry 必须拥有并公开取消 record/等待读者的能力；插件只拥有 lease/AbortSignal，不私读表。需要 registry 实现及事务发布调用点的最小补丁，另行授权隔离 checkout；不是直接改用户宿主。 | payload barrier 持有时 close 后 record/query 能否先终结、owner 卸载能否完成、late completion 能否复活、未发布 Agent 能否越过取消 fence；全部必须独立验证。**推荐作为依赖补齐提案，当前待实现。** |
| V：只给现有 register 增加可选 signal/owner | 表面签名改动小，但仍须分离 activation 与终态、唤醒已捕获 record 的 list/resolve、持有内部 scope、处理发布竞争；仅 Promise.race 或参数形状不够。 | 若只是 register 本地提前 reject，而 record/consumer 仍 pending，直接 FAIL。可作为上游实现 U 语义的备选外形，不当成独立已可行方案。 |
| W：保留当前 API，限制为 READY 后卸载或接受 flight 记录暂时 pending | 无需 SDK 新接口，但改变已冻结的取消/可用性门和用户期望；不能覆盖真实卸载/升级窗口，且 list 风险保留。 | **不推荐、不自行接受**。只能由 Coordinator 将具体风险/支持范围交用户裁决；即使接受，也不是完成原有取消门，更不能继续宣称全面升级安全。 |

推荐 U 是因为它把 record 关闭权放到真正管理 record 的 registry；不是因为“新方法名听起来可取消”。当前没有可直接调用的 U/V 实现，不为进度继续缩 microtask、复活 L/M、复制完整工具配置或侵入 host rows/global services。

### 15.4 U 的最小公共接口与终态语义（全部 PROPOSED，当前包不存在）

保留旧 register 的兼容入口，新增明确的 opt-in 协议，避免暗改所有既有 caller：

```ts
// PROPOSED public API — not available in examined releases.
interface OwnedPresetRegistration {
  readonly id: string;
  readonly generation: object; // opaque identity, not host table access
  readonly ready: Promise<AgentPreset>; // usable or broken/cancelled outcome
  readonly closed: Promise<{ reason: string }>;
  readonly drained: Promise<void>; // physical resource convergence, separate
  close(reason?: string): void; // idempotent logical fence, no payload await
}
beginRegistration(
  definition: PresetDefinition,
  options: { owner: Context; signal?: AbortSignal }
): OwnedPresetRegistration;
readonly capabilities: {
  ownedRegistration: 'terminal-cancel-v1'
};
```

这是一项上游协议需求，不是本项目准备直接实现的 shim。capabilities 名称同样是待审提案；不得在当前对象上凭空读出能力。上游可采用 V 的签名，但必须实现下列完全相同的语义并提供明确能力声明。

1. **立即所有权**：beginRegistration 在启动异步 activation 前完成 id/owner/root 校验并交出 lease；caller 从一开始能 close。owner 是逻辑关闭权的拥有者：其真实 effect disposer 同步调用 close，返回不依赖 payload，不能只是保存 caller.context。物理 scope/drain 由 registry 的 collection 边界持有，不能简单改成 own Fiber 的结构子节点，否则 Cordis dispose 又会等待其 activation。registry 自身卸载也触发关闭并管理 drain；重复/活动冲突 id 不覆盖别人。此处是具体的新 lease 所有权协议，不是声称现有 scope 参数已能做到。
2. **终态与 activation 分开**：逻辑状态为 ACTIVATING→READY 或 FAILED/CANCELLED/CLOSED。close 首先设置不可逆 generation fence/关闭原因，使 cancelled record 可立即被审计为 broken/invalid；需要保留取消 tombstone 使当前硬门的 resolve 返回明确 broken，而不是继续 await activation。物理 activation 的 Promise 可以仍在 flight，但它不再是 cancelled record 的公共 ready/diagnostic 唯一等待源。已兑现 ready 不会“反兑现”，后续 admission 始终检查关闭 fence。旧等待读者取得终态且 drain 完成后清除该 tombstone，恢复正常卸载后无自有登记；若新 generation 先取得已关闭 id，则按对象身份原子替换，旧 drain 不得删除新记录，不能覆盖活动他人 id。
3. **唤醒所有等待读者**：已经捕获 record 并在等 ready 的 resolve/list/remote roster/retain/mount/lease 必须观察 closed 终态，在 payload barrier 释放前得到取消结果；关闭后新 lookup 立即拒收。只从 map 删除 record 只保护未来查找，不能唤醒旧 Promise，因此不足。list 不能因这条 cancelled record 继续等待其物理 drain；对其它 preset 的返回不被它拖住。
4. **禁止取消后新 Agent 接入**：retain/bind/lease 提交前以 generation identity＋closed fence 复核，不能在 close 之后授予新绑定；已开始但尚未发布的 Agent setup 也须在 publication commit 处复核并回滚。当前 Web setup 只 await mount，若其返回到 factory 发布之间存在取消窗口，**仅改 registry 的 ready 仍不足**；上游须让相关 setup 返回公开 AgentSetupCommit（或等价已公开事务验证），在真正 commit 点检查这一 lease。不是劫持 factory，也不在 agent/created 后补偿。已在取消前提交的现有 Agent revision 按宿主既有保留规则处理，不能把它们误计为新接入。
5. **资源 drain 如实独立**：close 要立即撤回 admission，并使 SDK 管理的 scope/注册能力进入关闭状态，阻止迟到 effect/provider/child plugin 重新生效。drained 只在真实作用域清理完后完成；未知第三方任意 Promise/外部 I/O 无法由 JavaScript 强制终止，不能承诺“close 已完成等于所有物理资源已清空”。上游需合作式信号/作用域失效和迟到清理；未收敛如实暴露，不用它拖住 roster/owner 逻辑关闭。安全验收仍要证明 SDK 管理的迟到注册被拒绝，无资源复活。
6. **竞态归属**：关闭旧 generation 后旧 activation 完成，只清理旧 scope；不得 READY、不得删新 generation/他人同 id。消费者持有的是精确 generation，不在 wait 后悄悄切换到另一个对象。异常/rejection 全消费且保留诊断；不得把失败当 READY。

无环因果要求为：
```text
owner dispose / signal → lease.close → record terminal + readers wake
                               ↘ owned scope fence / asynchronous drain
payload activation ─────────────→ late completion cleanup → drained
```
第一行不等待第二行或 payload；consumer 接入检查 terminal/commit fence，不等待 cancelled payload 的 audit。插件不调用 host 私有表/字段，也不通过新建自有 createScope 假装获得 registry 内 scope 所有权。

### 15.5 上游最小修改面与必需回归（待实现/NOT_RUN）

| 模块/边界 | 必须承担的改变 |
|---|---|
| packages/preset/agent-preset-registry：公开 index/types、definition/registration、mount/diagnostic | 立即 lease/owner/capability；独立终态与 activation/drain；关闭 tombstone、公共读取取消唤醒、精确 generation 的保留/迟到清理。不能只加 AbortSignal 类型。 |
| scope/Cordis 生命周期边界 | 优先复用其真实公开 scope/dispose；须证明 SDK-managed effects 在关闭 fence 后不能新增。若现 API 做不到，明确作为额外上游需求，不能本项目改私有 uid/epoch。当前不预先批准改核心。 |
| 实际 preset mount consumer；原生 dsh-agent-preset 的边界 | 逐一核对真实 Web/setup、resume/fork/subagent 等 publication 边界，必要 commit fence 调用点纳入补丁。governance 使用 U 不要求将所有既有原生 row 迁移；若上游选择让原生 row 也覆盖 flight 取消，其 owner disposer 须另行迁移 lease 并回归，不偷偷扩为所有宿主配置行替换。保留旧 register 兼容入口；不改无关工具/profile 行/全局服务。 |
| 本项目 native lifecycle/compat adapter | 日后仅通过当前 Loader context 消费被声明且实证的协议；own cleanup 调用 lease.close，不再等待未取得的 disposer。保留 source/overlay/guard 的其它门，不因新增 API 宣称全部旧失败已修。 |

最低回归先复用 G 的**同一 permit 后 payload barrier**，观察 close/owner dispose/closed、postcancel 新 resolve、此前已等待的 resolve/list/Agent create；这些全部必须在 barrier 保持时终结/拒收，之后才释放 barrier 并检查 drained。再测取消前后交错、已 ready 与 flight、重复 close、id 重用、取消后迟到激活/迟到 effect、旧 close 不伤新 record、发布 commit 竞争、普通 standard roster/会话不变。每条需要真实事件顺序及非零宿主校验，不能 fake registry、延长750ms、提前释放、只取消 harness wait 或仅最终 drain。

完成这一协议回归后，才恢复尚未执行的 seed/accepted 差异、broken/pending 拒收、复杂 isolate/!!js/地址保真、linked repo 无 host deps、热刷新与完整 current-web/技能/工具矩阵。上游源码+单元绿不等于本项目适配通过；这也是单独组件测试无法替代真实集成的原因。

### 15.6 当前项目仍可独立推进的范围与待裁决选项

以下只划清依赖，不作为自动解锁 S-B～F 的新授权；需对应任务已有授权/锁/独立审查。

| 可安全独立准备/验收 | 依赖 U/协议补齐后才能完成 |
|---|---|
| 当前 CI clean-checkout 修复及原生 Python/manifest/cross-reference 门；保全暂停 FIX-444/445 | native 初始登记、permit 后卸载/升级取消安全和支持声明 |
| CLI manifest/context 定位、probe oracle 路径、版本证据新鲜度；能力缺失/零校验/卸载状态的诚实诊断 | 在当前实际 profile 完成 register/compose/真实卸载和动态刷新全链 |
| persona/roots 纯策略、表达式保真 fixture、native/legacy 诊断分面及错误信息的设计/独立测试（不能借此接线） | SDK 取消协议消费、public publication fence、runtime current-web 兼容验收 |
| 0.99 release inventory、范围/暂停项/风险材料核对，已有独立修复的审查提交 | 将 DSH 适配标完成、据此关闭 FEAT-102、发布“已适配”版本及用户重新安装 |

**给 Coordinator 的具体选择**：
- 推荐：用户明确扩展授权后，在独立隔离上游 checkout 做 U 的最小补丁及回归；基线先固定当前 0.2.0-rc.2 的精确发布物以复现同一 R3-B1，若另选 0.2.1-rc.2 则完整隔离同代依赖。补丁经上游/API独立审查、真实集成通过后，再裁定正式依赖版本/分发来源；不混包、不修改用户当前 DSH，不擅自向上游发消息/提交 PR。
- 若不扩展上游范围：继续独立 CI/工具链工作，FEAT-102 保持实质未完成并列出阻塞依赖。用户另行决定 0.99 是否改范围/延期；本设计不替用户决定移除适配目标。
- 若考虑降低支持标准/接受 flight pending 风险：必须另列明确变更和用户决策，不能当成原门通过。此路不推荐，当前无风险接受或发布许可。

版本解耦的产品依赖边界仍是**运行宿主的公开能力协议**，不是将 registry/DSH 固定副本打包进本插件。版本号仅记录已测试矩阵；能力字段与终态语义需共同实证，不能凭 method arity/包版本字符串/存在 AbortController 推断支持。未知宿主只能明确拒收自己；这项安全行为不等于用户适配目标完成。

Proposed ADR 增量：R3-B1 已证明当前所有权协议不满足取消门；已检查官方 next 也未提供该能力。建议请求隔离上游 U 范围授权，补齐 caller-owned terminal-cancel-v1 后再独立复审；当前实现/发布权限 NONE。R4 审查不得因本提案文档完整而解除缺实现/缺证据的阻塞，后续验证须另行明确授权。
### 15.7 本轮外部只读命令审计

五条 shell 命令均 exit 0，UTC 来自当次打印；网络元数据与 tarball 在进程内存读取/校验，未落盘/执行/安装；唯一本轮写入是本设计。此前 web.open 对两个 registry latest URL 返回 Internal Error，工具没有提供该调用的 UTC/exit code，不补造，也不作为版本/API证据；后续 NET-01～03 是成功的独立 HTTP 读取。

```json
[
  {
    "id": "R4-RO-01",
    "started_utc": "2026-10-19T06:04:39.9618116Z",
    "cmd": "$r4Started=[DateTime]::UtcNow.ToString('o'); Write-Output $r4Started; $r4Sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$r4Sdk/dsh-agent-preset-registry/package.json\" | Select-Object -First 55; Get-Content -Encoding UTF8 \"$r4Sdk/dsh-agent-preset-registry/lib/types/index.d.ts\" | Select-Object -Skip 28 -First 75; Get-Content -Encoding UTF8 \"$r4Sdk/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 498 -First 104",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh"
    ],
    "impact_write": [],
    "access": "read-only installed manifest/SDK; no host/profile operation",
    "exit_semantics": "shell/process completion code"
  },
  {
    "id": "R4-NET-01",
    "started_utc": "2026-10-19T06:05:05.9650213Z",
    "cmd": "$r4Started=[DateTime]::UtcNow.ToString('o'); Write-Output $r4Started; $ErrorActionPreference='Stop'; foreach($r4Uri in @('https://registry.npmjs.org/@deepseek-ai%2fdsh-agent-preset-registry/latest','https://registry.npmjs.org/@deepseek-ai%2fdsh/latest')){ try { $r4Data=Invoke-RestMethod -Uri $r4Uri -TimeoutSec 20; [PSCustomObject]@{url=$r4Uri;status='READ';name=$r4Data.name;version=$r4Data.version;repository=$r4Data.repository;tarball=$r4Data.dist.tarball;integrity=$r4Data.dist.integrity} | ConvertTo-Json -Depth 5 -Compress } catch { [PSCustomObject]@{url=$r4Uri;status='UNAVAILABLE';error=$_.Exception.Message} | ConvertTo-Json -Compress } }",
    "exit_code": 0,
    "impact_read": [
      "https://registry.npmjs.org/@deepseek-ai%2fdsh-agent-preset-registry",
      "https://registry.npmjs.org/@deepseek-ai%2fdsh",
      "official tarball URLs emitted by metadata; memory-only"
    ],
    "impact_write": [],
    "access": "read-only HTTPS metadata/artifact; memory-only decode, no package execution/install/extraction to disk",
    "exit_semantics": "shell completion; per-URL READ/UNAVAILABLE separately printed"
  },
  {
    "id": "R4-NET-02",
    "started_utc": "2026-10-19T06:05:24.3691974Z",
    "cmd": "$r4Started=[DateTime]::UtcNow.ToString('o'); Write-Output $r4Started; $ErrorActionPreference='Stop'; $r4Uri='https://registry.npmjs.org/@deepseek-ai%2fdsh-agent-preset-registry'; $r4Data=Invoke-RestMethod -Uri $r4Uri -TimeoutSec 20; [PSCustomObject]@{url=$r4Uri;distTags=$r4Data.'dist-tags';versions=@($r4Data.versions.PSObject.Properties.Name);publicationTimes=$r4Data.time} | ConvertTo-Json -Depth 6 -Compress",
    "exit_code": 0,
    "impact_read": [
      "https://registry.npmjs.org/@deepseek-ai%2fdsh-agent-preset-registry",
      "https://registry.npmjs.org/@deepseek-ai%2fdsh",
      "official tarball URLs emitted by metadata; memory-only"
    ],
    "impact_write": [],
    "access": "read-only HTTPS metadata/artifact; memory-only decode, no package execution/install/extraction to disk",
    "exit_semantics": "shell/process completion code"
  },
  {
    "id": "R4-NET-03",
    "started_utc": "2026-10-19T06:05:46.0515459Z",
    "cmd": "$r4Started=[DateTime]::UtcNow.ToString('o'); Write-Output $r4Started; $r4Read=@'\nimport urllib.request,json,io,tarfile,hashlib,base64,re\nbase=\"https://registry.npmjs.org/@deepseek-ai%2fdsh-agent-preset-registry/\"\nfor version in [\"0.2.0-rc.2\",\"0.2.1-rc.2\"]:\n    meta=json.load(urllib.request.urlopen(base+version,timeout=20))\n    artifact=urllib.request.urlopen(meta[\"dist\"][\"tarball\"],timeout=20).read()\n    integrity=\"sha512-\"+base64.b64encode(hashlib.sha512(artifact).digest()).decode()\n    assert integrity==meta[\"dist\"][\"integrity\"]\n    print(json.dumps({\"version\":version,\"metadata_url\":base+version,\"tarball\":meta[\"dist\"][\"tarball\"],\"integrity_verified\":True,\"sha256\":hashlib.sha256(artifact).hexdigest(),\"dependencies\":meta.get(\"dependencies\"),\"peerDependencies\":meta.get(\"peerDependencies\")}))\n    with tarfile.open(fileobj=io.BytesIO(artifact),mode=\"r:gz\") as archive:\n        for file in [\"package/lib/types/index.d.ts\",\"package/lib/index.js\"]:\n            source=archive.extractfile(file).read().decode(\"utf-8\")\n            lines=source.splitlines()\n            wanted=set()\n            if file.endswith(\".d.ts\"):\n                wanted.update(range(len(lines)))\n            else:\n                for i,line in enumerate(lines):\n                    if re.search(r\"async register\\(|register\\(definition|async diagnostic\\(|async list\\(|async resolve\\(|AbortSignal|unregister|abort|cancel|record\\.ready\",line,re.I):\n                        wanted.update(range(max(0,i-4),min(len(lines),i+13)))\n            print(\"FILE \"+file+\" SHA256=\"+hashlib.sha256(source.encode()).hexdigest())\n            for i in sorted(wanted): print(str(i+1)+\": \"+lines[i])\n'@; $r4Read | python -X utf8 -; exit $LASTEXITCODE",
    "exit_code": 0,
    "impact_read": [
      "https://registry.npmjs.org/@deepseek-ai%2fdsh-agent-preset-registry",
      "https://registry.npmjs.org/@deepseek-ai%2fdsh",
      "official tarball URLs emitted by metadata; memory-only"
    ],
    "impact_write": [],
    "access": "read-only HTTPS metadata/artifact; memory-only decode, no package execution/install/extraction to disk",
    "exit_semantics": "shell/process completion code"
  },
  {
    "id": "R4-RO-02",
    "started_utc": "2026-10-19T06:08:18.2510979Z",
    "cmd": "$r4Started=[DateTime]::UtcNow.ToString('o'); Write-Output $r4Started; $r4Host='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh'; $r4Sdk=\"$r4Host/node_modules/@deepseek-ai\"; foreach($r4Manifest in @(\"$r4Host/package.json\",\"$r4Sdk/cordis/package.json\",\"$r4Sdk/cordis-plugin-loader/package.json\")){ $r4Meta=Get-Content -Encoding UTF8 -LiteralPath $r4Manifest | ConvertFrom-Json; [PSCustomObject]@{path=$r4Manifest;name=$r4Meta.name;version=$r4Meta.version} | ConvertTo-Json -Compress }; Get-FileHash -Algorithm SHA256 \"$r4Sdk/dsh-agent-preset-registry/lib/index.js\",\"$r4Sdk/dsh-agent-preset-registry/lib/types/index.d.ts\" | Format-List Path,Hash",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh"
    ],
    "impact_write": [],
    "access": "read-only installed manifest/SDK; no host/profile operation",
    "exit_semantics": "shell/process completion code"
  }
]
```

## 16. 2026-10-20：原生派生落地（S-B 首个可用切片）与隔离真机验收

**结论先行**：`lib/dsh-native/` 已实现并在隔离 `DSH_HOME` 的真实 dsh **0.2.1-rc.2** 上验收通过；运行时不再依赖 §5.1 的登记时序候选（M/L）、§14 的 G 或 §15 的 U 协议，因为本实现既不创建 guard/wrapper，也不在自身 activation 内等待 base/root/mount。

### 16.1 实际机制（取代 §14/§15 作为运行时路径）

1. `apply()` 先用契约声明判断宿主能力：组合树里是否有启用的 `@deepseek-ai/dsh-agent-preset-registry` row（`lib/dsh-native/source.js`）。有 → native；没有 → legacy 目录渲染；有但被禁用 → 明确拒收、不写目录。
2. native 通过 `ctx.inject(['agentPresets'], …)` 等公开服务（profile row 的 `apply()` 先于服务提供，这是服务依赖而非 sleep/排序猜测）；回调里读 `ctx.get('loader').entries()` 的 **declaration**（`options.config`）定位唯一启用的 `standard` 声明。
3. `lib/dsh-native/overlay.js` 纯函数派生：`structuredClone` 整份 plugins，只追加 persona.prefix（正文来自 `agent-presets/governance/persona.md.template`）与 `skill-filesystem.customSkillDirs` 的两个包内绝对根；其余行/group/isolate/`!!js`/顺序原样保留。
4. `agentPresets.register(definition)` 建立登记；row cleanup 只标记 disposed 并在 disposer 到达后撤回，**不等待** in-flight activation。

### 16.2 与原硬门的关系（诚实边界）

- **R3-B1 取消语义未消除**：registry 仍要等 activation 才交出 disposer。本实现让自身卸载不等待它，因此不形成等待环；但"卸载瞬间已进入 registry 的 pending record 会等到 mount 完成"这一窗口仍在。它不再阻塞运行时交付，作为**已知边界**登记，不声明 U 协议已实现。
- **raw vs accepted**：读取的是组合树 declaration（`options.config`）。若宿主后续出现"更新失败保留旧 fiber"的分叉，派生可能基于 raw 而非 accepted；0.2.1 的 preset 声明是静态 YAML + profile overlay，本轮未观测到分叉。不为此引入宿主包 import 或 schema 复核（那会重新引入版本耦合）。
- **热刷新未实现**：不监听 `app-boot/config-reload`；宿主升级/包路径变化要求重启（宿主既有语义）。相同 preset id 重复注册会同步拒收并 warn，不覆盖。
- **诊断面未同步**：`dsh_compat`/`doctor` 仍以 legacy 组合为主要校验对象；`launch.py --install` 仍是 legacy 渲染。0.1.x 的静态组合支持明确退役——legacy 模板只对齐当前 shelf。

### 16.3 验收证据（2026-10-20，Windows，隔离 DSH_HOME）

- 环境：真实 `dsh plugin --profile web add link:<repo>` 的隔离 profile；dsh 0.2.1-rc.2；`${DSH_HOME}` 重定向到仓库 `.governance/sandboxes/dsh021-baseline`，真实 `~/.dsh` 未读写。
- 观测：roster 含 `governance`（名称「治理协调器」，`broken=null`）；`resolve('governance')` 无 broken；`sessionController.create({agentPreset:'governance'})` 后 `composedPreset=governance`；治理会话 skill 目录含 `software-project-governance` 与 9 个命令 shim；`standard` 会话不含治理 skill（无泄漏）；`standard` 未被修改；`${DSH_HOME}/.agent-presets` **不存在**（native 不写目录）。
- 回归：`test_dsh_adapter` 77 pass、`test_dsh_boundary` 136 pass、`test_dsh_doctor` 92 pass、新增 `test_dsh_native_bridge` 7 pass；`test_dsh_contract` / `test_dsh_compat` 的少量失败与本改动无关（同一失败在 HEAD 干净 worktree 复现，见 §16.4）。
- 反例：重复 base → 不登记并 warn；registry row 被禁用 → 拒收；无 registry row → 走 legacy；`apply()` 在 native 宿主上不写任何文件。

### 16.4 仍未完成（不并入本次交付）

1. 诊断面适配（2026-10-20 已完成第一切片）：`check_dsh_preset_compat` 现在是**双平面**解析——profile 平面解析失败的行回退到 CLI 包自身 context（`dsh` 0.2 对宿主包真实使用的第二平面），报告披露 `rows_resolved_via_cli_fallback` 与实际锚点；真实环境由 FAIL 转 PASS（19/23 行校验、1 行经 CLI 回退、4 行 NO_SCHEMA 披露）。同时把 `FX-NO-SCHEMA-*` 从「宿主某包无 Config」的版本敏感前提改为**自带零 schema 模块**，消除宿主升级导致的断言翻转。剩余：native 派生行本身尚未纳入探针（当前仅校验 legacy 模板），`launch.py --install` 仍是 legacy 语义。
2. `launch.py --install` / `--smoke` 仍是 legacy 语义；0.2 宿主上应明确标注或改走 native 说明。
3. 取消协议（§15 U）与 publication fence：未实现、未验证，不声称已解决。
4. 多 profile / 桌面 / headless：本轮只验收 current-web；其余 NOT_RUN。

**状态更新**：FEAT-102 的运行时适配切片从 `BLOCKED` 变为 **native 路径已实现并隔离验收**；§5.1/§14/§15 的失败轨迹与提案原文保持不变，作为历史与未关闭边界保留。
