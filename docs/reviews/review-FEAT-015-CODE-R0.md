# FEAT-015 Code Review R0 — RISK-049 关闭标准②：preset 会话 live 冒烟门禁（隔离环境）

## 元信息

| 项 | 值 |
|----|----|
| Task | FEAT-015（RISK-049 关闭标准②；plan-tracker.md L281；P1，0.79.0） |
| Round | R0（首轮独立审查，工作树未提交、无 REVIEW 记录） |
| 基线 | HEAD `f473ace247f70dd641c32da7d6bef4a210f497b9`；审查对象 = 工作树 diff（`git status`：M `adapters/dsh/launch.py`、M `skills/software-project-governance/infra/verify_workflow.py`、M `skills/software-project-governance/infra/tests/test_dsh_adapter.py`，+935/-1） |
| 范围 | launch.py（+436/-1：`--smoke` 隔离冒烟门禁）；verify_workflow.py（+156：`check-dsh-preset-smoke` 子命令 + Check 28u 接线）；test_dsh_adapter.py（+344：13 新用例，26→39） |
| Reviewer | Code Reviewer Agent（只读审查；除本报告外未创建/修改任何产品或治理文件；全部验证操作只读或在 %TEMP% 隔离/decoy 目录下执行） |
| 审查依据 | `agents/code-reviewer.md` + `skills/code-review/SKILL.md`（已加载并遵循）；执行包 `.governance/execution-packets.json#packets.FEAT-015`；RISK-049 行（`.governance/risk-log.md` L49，关闭标准(2) 原文）；M7.7 R4 命令日志 `.governance/incidents/FEAT-015-isolation-smoke-20260909.log`（18 条） |
| Date | 2026-09-09 |

## 终态结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`

P0 = 0（无阻塞项）。P1×1 / P2×2 / P3×4 全部为非阻塞发现。唯一 P1（F-1）不是代码缺陷而是**治理收口条件**：RISK-049 关闭标准(2) 的字面范围（"headless 或受控真实会话"的 live 冒烟）宽于本交付的验证等级（隔离环境 + 加载面解析，live session面 NOT_RUN 如实标注）——实现本身与执行包操作契约完全一致且 no-overclaim 纪律到位，但**关闭该标准时的归因措辞必须限定等级**并登记 live/headless 会话面后续项（先例：FEAT-014 R0 F-3 对关闭标准(1) 的同构处置）。满足 code-review SKILL「循环角色」段通过终态契约：无未解决 BLOCKING finding，含独立结构字段 `unresolved_blockers=0`。

## 发现计数

| P0 | P1 | P2 | P3 |
|----|----|----|----|
| 0 | 1 | 2 | 4 |

## 5 维度逐项结论表

| 维度 | 结论 | 关键事实（可复查） |
|------|------|---------|
| 正确性 | ✅ 通过（附 F-3 P2、F-5 P3 非阻塞发现） | 守卫语义逐行核对（launch.py L533-572）：未设 DSH_HOME 拒绝（消息 L549，实测 exit 2）；相等/包含双向拒绝（`_is_within(isolated, home) or _is_within(home, isolated)` L556-557，消息 L559，实测 exit 2）；**两段拒绝均先于首个写操作 `isolated.mkdir`（L572）**。绕过向量 5 探针实证（decoy USERPROFILE 下）：真实 home 位于隔离目录内 / 隔离目录位于真实 home 内 / 大小写翻转 / junction 指向 / 相对路径解析到真实 home → 全部 exit 2，decoy 完整性校验 sentinel 完好、零 `.agent-presets` 生成。双面断言正确：installed 面（绝对路径代换形态）+ shipped 面（`!!js` baseUrl 自定位形态——FIX-290 回归面）；`_resolve_skill_entry` 的 URL 数学（`urljoin(preset_uri + "/", rel)`，L381-387）与 Node `new URL(rel, baseUrl)` 对"composition 所在目录"基准语义等价（`presets/governance/` + `../../skills/` → `<repo>/skills/`，实测输出双面各 2 roots 全 ok）。负路径失败信息指明缺失项（"no customSkillDirs root contains software-project-governance/SKILL.md" / "/governance projection skill missing: …" / 字面相对路径 FIX-290 告警，test L793/813/829 断言）。环境变量恢复 finally 正确（L575-584）；exit 0/1/2 语义经 main() 直通（L726-728），与 --install/--uninstall/--dry-run 互斥（L720-724） |
| 安全性 | ✅ 通过 | 真实 home 防护双层：结构性守卫（写前拒绝，见上）+ 检测网（witness 前后比对 L568/L597-607，实测 `real-home writes: 0 (witness unchanged)`）。指纹仅 lstat 元数据（`_home_fingerprint` L283-307；`_real_home_witness` L309-345）——不读文件内容，凭据不触碰（docstring 明示 + incidents 日志 L6 口径一致）。M7.7 三选一 = (a) 隔离环境（env 重定向）：launch.py L546-572、check L6944-6948（`tempfile.mkdtemp` + finally `rmtree`，实测临时 home 已删除）。无注入面：subprocess 列表 argv（verify_workflow L6951-6959）、无 shell 拼接、正则仅作用于仓内可信文件；无密钥/凭据打印。假阴性分析：适配器在真实 home 的唯一写面 = `preset_dir()`（install 仅写 target 下、uninstall 仅 rmtree target、bootstrap 写项目目录——全部核对），witness 对 `.agent-presets` 递归覆盖 → 无逃逸路径 |
| 可维护性 | ✅ 通过（附 F-4 P3） | 数据驱动断言常量（`SMOKE_CATALOG_SKILL`/`SMOKE_GESTURE_NAME`/`SMOKE_GESTURE_TARGET`，L248-250）；单一冒烟入口被 CLI 检查复用（check-dsh-preset-smoke 以子进程运行同一 `launch.py --smoke`，进程隔离而非 import—— deliberate，L6938-6948 注释）；docstring 记录设计依据与实测事实（witness 口径的宿主并发写实证，L317-334）。Check 28u 接线对称应用 FEAT-014 R0 F-2 教训：`_product_gate_active` 守卫 + skip 分支（L15948-15963）+ `_PLUGIN_PRODUCT_CHECK_IDS` 登记（L14253）+ `_PRODUCT_GATE_LABELS`（L14309）。不足：`verify_preset_loading`（L414-515，约 102 行）与 `smoke_preset`（L533-624，约 92 行）超 SKILL 50 行建议（F-4） |
| 性能 | ✅ 通过 | 实测：pytest 39 passed in 10.52s；隔离冒烟单次秒级（含 preset 生成 + 双面解析 + witness 两次，本审查实测明显 <60s 预算）；witness 作用域 = `.agent-presets` 递归（80 entries，9-18ms，incidents 日志 L38）+ 顶层 iterdir——刻意避开非确定性全 home 遍历（O(受控子树)）；check 子命令 timeout=120s 兜底（L6938）。无 N+1 / 无重复 I/O（composition 一次读取复用） |
| 测试覆盖 | ✅ 通过（附 F-2 P2） | 13 新用例（test L709-976）覆盖：正路径 CLI（L730，含独立 oracle 前后比对——**测试侧 oracle 与被测代码无共享实现** L74-95）；拒绝路径 CLI×2（未设 L754 / 等于真实 home L767，均 decoy 化——真实 home 不在爆炸半径）+ in-process 拒绝（L780）；验证器负路径×3（目录缺失 L793 / 投影缺失 L813 / 字面相对路径 L829）；witness 作用域 4 场景（宿主子树容忍 / 写面检出 / 顶层文件改动检出 / 顶层新增检出，L852）；witness 变化防御纵深（L898，断言恰两次 witness 且 FAIL）；dsh CLI 缺失诚实标注（L922）；检查子命令 PASS+清理（L939）与 fail-closed（L953，伪 launcher 注入）。缺口：守卫包含/case/junction 向量无自动化用例（F-2） |

## 发现列表

| # | 级别 | 位置 | 事实依据 | 影响 | 修复建议 | 处置 |
|---|------|------|---------|------|---------|------|
| F-1 | P1 | `.governance/risk-log.md` L49（关闭标准(2) 原文）；launch.py L610-613（NOT_RUN 输出）；执行包 `goal` vs `scenario/done_definition` | 标准(2) 原文要求「preset 会话 **live** 冒烟门禁落地（**headless 或受控真实会话**，验证 skill 目录加载 + /governance 手势）」；交付物验证等级 = 隔离环境下 preset 生成 + 加载面解析（skill catalog 根 + 手势投影 + 投影目标，installed 与 shipped 双面），LLM 会话面显式 `NOT_RUN`（L610-613，含 "no session behavior is claimed"）。实现与执行包操作契约（scenario/success_metrics/done_definition/non_goals「不冒充真实用户会话验证」）完全一致 | 代码无缺陷、无过度宣示；但若以本证据**整体**关闭标准(2)，关闭记录将声称 live 冒烟已落地而实际为 isolation 级——构成 RISK-049 自身定义的宣示-验证等级缺口（元层复现；同构先例：FEAT-014 R0 F-3 对标准(1) 的"dsh 面 vs 适配器面"处置，EVD-955/DEC-179 已按限定口径收口） | 关闭标准(2) 时二选一：(a) 关闭记录显式限定「isolation 级加载面门禁已落地；live/headless 会话面登记为后续候选任务（RISK-049 复评窗 2026-09-30 或 0.79.x 入槽评估）」；(b) 经 decision-log 修订标准(2) 措辞后再关闭。不得以无限定措辞整体关闭 | Coordinator 决策项（关闭该风险/标准前 MUST 执行） |
| F-2 | P2 | test_dsh_adapter.py L754-790（现有拒绝用例仅覆盖未设+等值） | 验收标准(1) 要求「DSH_HOME 未设/等于真实 home/**解析到真实 home 周边**三种情形 MUST 拒绝…不得存在绕过路径（如**符号链接、相对路径、大小写差异**）」。套件覆盖：未设（L754）、等于（L767 CLI + L780 in-process）；**包含双向、大小写、junction/符号链接、相对路径解析到真实 home 均无自动化用例**。行为本身正确——本审查 5 探针实证全 exit 2 + 零写入，但该正确性当前仅由 `_is_within`/`_normcase_path` 实现细节（L266-281）隐式保证，未来重构（如改用字符串前缀比较、丢失 `resolve()`）可能静默回归 | 验收标准(1) 的核心安全语义存在无回归网钉住的窗口（fail-open 方向的覆盖缺口） | 按 `_decoy_home_env` 模式补 2 条用例：① DSH_HOME=<decoy-home>（真实 home 在内）与 <decoy>\.dsh\sub（在内）双方向断言 exit≠0 且 decoy 零写入；② 大小写翻转 + junction 指向（Windows Junction 无需特权）断言 exit≠0 | 遗留候选（不阻塞；建议随本任务 commit 前或下一波次补齐） |
| F-3 | P2 | launch.py L540-543（仅 `sys.stdout.reconfigure`） | stderr 未 reconfigure。实测证据：本审查拒绝路径运行中，stdout 的 REFUSED 行 em-dash 正常（`— refusing`），**stderr 的同一消息 em-dash 乱码**（`?? refusing`，GBK 控制台管道）；FAIL issue 诊断行同样走 stderr（L624-626） | 诊断通道编码劣化：非 ASCII 路径（如含中文的用户名）出现在 stderr 诊断时，传统控制台编码下可能产生乱码甚至 UnicodeEncodeError（traceback 替代清晰诊断；REFUSED 出口 2 在极端情形可能退化为 traceback 出口 1）。stdout 已防护、stderr 未防护的不对称是明确疏漏 | 在 L541 旁补 `sys.stderr.reconfigure(encoding="utf-8", errors="replace")`（同样 try/except 包裹），1-2 行 | 遗留候选（不阻塞；低成本） |
| F-4 | P3 | launch.py L414-515（`verify_preset_loading`，约 102 行）；L533-624（`smoke_preset`，约 92 行） | 两函数超 code-review SKILL 维度 3 检查项 2「单个函数 >50 行建议拆分」；均为线性验证流水线/CLI 编排，职责单一、可读性尚可。顺带 cosmetic：冒烟运行中 `install_preset` 尾部打印 "Next: start a dsh session…"（L180-184）——对即将被调用方删除的隔离 home 的会话指引构成输出噪音 | 可维护性建议项；非缺陷 | 可选：`verify_preset_loading` 按解析阶段拆私有助手（entries 解析 / catalog / gesture / target）；冒烟路径可静默 install 的 "Next:" 段（如 install_preset 加 quiet 参数） | 遗留候选（讨论级） |
| F-5 | P3 | launch.py L603-607（witness 变化消息）；L317-334（docstring 口径） | witness 含顶层**文件**的 size/mtime_ns（L322-333）；宿主在冒烟窗口（秒级）内改写顶层文件（如 settings.yaml）会触发 `WITNESS CHANGED` → FAIL，消息定性 "the isolation guarantee is broken"——将宿主活动误归因为隔离破坏 | 仅假阳性方向（fail-closed，无假阴性风险）；概率低（秒级窗口 + 顶层文件低频变更）；但措辞可能误导排查 | 消息补一句限定："witness changed (adapter write OR concurrent host activity on top-level files / .agent-presets)"，把两种可能都列出 | 遗留候选（讨论级） |
| F-6 | P3 | verify_workflow.py L6990-6996（`not in (0, None)` 宽容）；L20726-20729（cmd 打印） | `real_home_writes` 正则未命中时为 None，被接受为 PASS 要件（`not in (0, None)`）；该行当前由 launcher 无条件打印（L599-601），None 仅在输出异常截断时出现。另：launcher 缺失早退（L6944-6946）时 cmd 打印 "temp DSH_HOME: None (removed)"——"removed" 对未创建的目录轻微误导 | 宽容度小缺口（理论 fail-open 方向，需输出同时异常截断 + exit 0 才触发）；cosmetic | 可选收紧：PASS 要求 `real_home_writes == 0`（None → FAIL 并注明 witness 行缺失）；早退分支不打印 "(removed)" | 遗留候选（讨论级） |
| F-7 | P3 | `.governance/incidents/FEAT-015-isolation-smoke-20260909.log` L17/L30（Developer 实测 121）；本审查两次实测 119（summary-only 与全量，全量输出 L1158-1160 + "Result: ISSUES FOUND — 119 issue(s)"） | 回归事实复核：39 passed ✓ / Ran 764 OK ✓ / check-governance **121 → 119**（-2，方向为变少）。归因事实链：① 本 diff 对 check-governance 的唯一作用面 = 产品检查，唯一新增检查 28u 在两次运行中均 PASS（0 issue，全量输出实证）；② 其余检查读 `.governance/` 数据——Developer 测量（09-09 08:5x）之后有 EVD-956 机写追加（其内容记录 Coordinator 复跑，时序上后于 Developer）；③ 执行包 `generated_at=2026-09-08T12:49:02` 早于两者，非漂移源。**-2 的逐检查机制未复演**（需回放 Developer 时点治理状态，本审查不修改 .governance 无法安全回放） | 无代码影响（diff 贡献 issue 数 = 0 在两次测量中均成立——Developer 前后 121=121 亦印证）；漂移若不记录，后续基线比对会误归因 | 任务收口（evidence 回写）时以本审查实测 **119** 为新基线记录，注明与 121 的差异及归因链 | Coordinator 收口动作（记录级） |

## AI 代码专项 5 项

| 检查项 | 结论 | 事实依据 |
|--------|------|---------|
| Mock 残留 | ✅ 无 | 产品代码（launch.py/verify_workflow.py 新增段）零 mock/桩；测试的 `patch.dict`/`patch.object`/`redirect_stdout` 全部在 `with` 块内即用即释（test L780-791、L898-917、L922-937）；diff 增量 grep `TODO\|FIXME\|XXX\|HACK\|mock\|Mock` 零命中（实测） |
| 硬编码返回值 | ✅ 无 | 判定全部由执行结果驱动：`smoke_preset` 返回值来自 issues 聚合（L619-624）；`check_dsh_preset_smoke` verdict 来自子进程 exit code + 输出正则（L6984-6996），无硬编码 PASS/FAIL 路径；`_resolve_skill_entry` 返回由 entry 文本形态驱动 |
| 幻觉 API | ✅ 无 | 逐引用核实均为真实 stdlib：`urllib.parse.urljoin/urlparse`、`urllib.request.url2pathname`（launch.py L68/L381-387）、`subprocess.run(capture_output/text/encoding/errors/timeout)`（verify_workflow L6951-6959）、`shutil.which`（L609-611）、`sys.stdout.reconfigure`（L541，3.7+）、`tempfile.mkdtemp`（L6944）、`os.walk(followlinks=False)`（L294）——全部存在且签名正确（实测运行通过即证） |
| 未实现 TODO | ✅ 无 | diff 三文件无 TODO/FIXME/XXX/NotImplemented/placeholder（grep 实测零命中）；无占位分支——所有分支有实现与对应测试 |
| 过度实现 | ✅ 无 | 变更严格限于执行包 `allowed_change_scope` 3 文件（git status 实证无越界）；无未使用符号（`SMOKE_*` 常量、全部 helper 均有调用方）；`root` 测试缝（verify_workflow L6940）被 test L953 行使；check 子进程复用而非重复实现冒烟逻辑——反过度实现的结构选择 |

## 硬门槛裁决

| 门槛 | 阈值 | 裁决 |
|------|------|------|
| P0 阻塞问题数 | = 0 | ✅（0 条） |
| 5 维度全覆盖 | = 100% | ✅（正确性/安全性/可维护性/性能/测试覆盖逐一有结论） |
| 每条发现标注级别 | = 100% | ✅（7 条：P1×1 / P2×2 / P3×4，每条含位置 + 事实依据 + 影响 + 修复建议） |
| 设计一致性 | 已完成 | ✅ 逐条比对完成（见下节）；1 项偏差（F-1，治理收口级，非代码缺陷） |
| AI 代码专项 5 项检查 | 全部完成 | ✅（5 项逐一有结论） |
| 事实依据红线 | 遵守 | ✅ 每条结论指向文件:行号 / 代码 / 测试断言 / 命令输出；无法验证项见「未验证项声明」 |

## 设计一致性比对（逐条）

| 比对项 | 结论 | 事实依据 |
|--------|------|---------|
| RISK-049 关闭标准(2) 原文（risk-log L49） | ⚠️ 机制落地 / 等级收窄 | 「验证 skill 目录加载 + /governance 手势」的机器门禁 ✓（一条命令、双面、可重复、fail-closed）；「live（headless 或受控真实会话）」面未执行且如实 NOT_RUN → 见 F-1（关闭归因必须限定等级） |
| M7.7 R1（三选一 = 隔离环境） | ✅ 一致 | 冒烟一切写在重定向 DSH_HOME（launch.py L546-572）；check 子命令自建 mkdtemp 并 finally 清理（L6944-6968）；本审查复核操作同样全隔离（见「复核操作披露」） |
| M7.7 R4（真实环境逐条上报） | ✅ 一致 | incidents 日志 18 条命令表（命令/时间/退出码/影响路径）；真实 home 仅只读元数据指纹（L6 明示不读内容）；EVD-956 机写留痕 |
| FIX-271（隔离协议先例） | ✅ 一致并强化 | FEAT-010 事故后的隔离协议（守卫 + 拒绝 + 见证）在本门禁中固化为**结构性代码**（REFUSED exit 2 独立于 FAIL exit 1；witness 前后比对），比 FIX-271 的流程约束更进一步 |
| FIX-290（baseUrl 自定位回归面） | ✅ 覆盖 | 冒烟第二面专门断言 shipped preset 的 `!!js` baseUrl 形态解析（实测 `[baseUrl]` 2 roots ok）；验证器显式拒绝字面相对路径并引用 FIX-290 语义（L377-382；test L829）——FIX-290 缺陷类自此有执行级回归网 |
| `--dry-run`/`--uninstall` 对称风格 | ✅ 一致 | standalone 子动作 + argparse 互斥（L720-724）；模块 docstring 模式清单同步（L28-46）；exit 语义显式文档化；`--mode link\|copy` 复用为生成模式（L46） |
| FEAT-014 R0 F-2 教训（产品检查守卫） | ✅ 已应用 | Check 28u 带 `_product_gate_active` 守卫 + skip 分支（L15948-15963）+ 双登记（L14253/L14309）——与 28t 当时的缺口形成对照，新检查未重蹈 |
| 未声明能力宣称 | ✅ 无 | README 本 diff 未触碰（git status）；CLI help/docstring/输出全部限定 "loading surface"/"resolution-level"/NOT_RUN；门禁措辞「隔离环境安装冒烟（环境变量重定向至临时目录）通过」与 EVD-956 一致 |

## 验收标准逐条核实

| # | 验收标准 | 裁决 | 事实依据 |
|---|---------|------|---------|
| 1 | 守卫语义：未设/等于真实/解析到真实周边三种情形写前拒绝（exit 2），无绕过路径（符号链接/相对路径/大小写） | ✅ 满足 | 实测 7 场景全 exit 2：未设（实测）、等于（实测 ×2）；包含双向/case/junction/相对 5 探针（decoy env，本审查）；写前拒绝锚点：拒绝消息 L549/L559 < 首写 `isolated.mkdir` L572；decoy 完整性零写入。**套件级钉住仅前两种（F-2）** |
| 2 | installed 与 shipped 双面断言（catalog 根 + /governance 投影 + 投影目标存在）；负路径失败信息指明缺失项 | ✅ 满足 | 隔离冒烟实测输出：双面各 2 skill roots（absolute/baseUrl 形态）ok + skill catalog + gesture shim + gesture target（`commands/governance.md`）全解析、双 verdict PASS；负路径消息命名缺失项（test L793/L813/L829 断言 "SKILL.md"/"/governance"/"relative"） |
| 3 | 真实 home 零写入证据链：witness 口径（顶层 + .agent-presets 递归）前后比对；全 home 非确定性处理如实披露且无假阴性风险 | ✅ 满足 | witness 实现 L309-345（口径=docstring 实测披露宿主并发写）；实测 `real-home writes: 0 (witness unchanged)`；测试侧**独立 oracle**（L74-95，与被测实现零共享）前后比对（L730）；非确定性披露：incidents L35-38 + docstring L317-334 + test L852 四场景；假阴性排除：适配器真实 home 唯一写面 `preset_dir()` 被 witness 递归覆盖（install/uninstall/bootstrap 全部代码路径核对） |
| 4 | no-overclaim：NOT_RUN 措辞防过度解读；README/输出/命名无超范围声明 | ✅ 满足 | NOT_RUN 行含完整边界说明 + "no session behavior is claimed"（L610-613，test L922 锁定 dsh CLI 缺失时也不静默）；README 未触碰（git status）；CLI help/docstring/Result 措辞均为 "loading surface"/"resolution-level"（L28-40/L621）；命名 `--smoke`/`check-dsh-preset-smoke` 无 "live"/"session-verified" 字样。**RISK-049 字面差距为关闭归因问题（F-1），非实现宣示问题** |
| 5 | 5 维度逐一结论；每条发现 P0~P3 + 位置 + 事实 + 影响 + 修复建议 | ✅ 满足 | 见 5 维度表与发现列表（7 条全带五要素） |
| 6 | 回归事实复核：39 passed / 764 OK / check-governance 121 与提供事实一致（可自行复跑） | ✅ 满足（含 1 项如实差异披露） | 39 passed in 10.52s ✓；`Ran 764 tests in 138.677s / OK` ✓；check-governance = **119**（两次实测）vs 报告 121——差异 -2、方向变少、本 diff 贡献 issue=0（28u PASS 实证）、归因链与未复演声明见 F-7 |
| 7 | 结论为四值之一；APPROVED_WITH_NOTES 须含 `unresolved_blockers=0` 且无未解决 BLOCKING finding | ✅ 满足 | 本报告 = APPROVED_WITH_NOTES，独立字段 `unresolved_blockers=0`，P0=0 |

## 回归事实复核（命令与输出摘要）

| 命令 | 结果 | 与提供事实比对 |
|------|------|---------------|
| `python -m pytest skills/software-project-governance/infra/tests/test_dsh_adapter.py -q` | `39 passed in 10.52s`（exit 0） | ✅ 一致（Coordinator：39/10.9s） |
| `DSH_HOME=%TEMP%\feat015-review-smoke-* python adapters/dsh/launch.py --smoke` | `Result: PASS` / exit 0；双面全解析；`real-home writes: 0 (witness unchanged)`；`live session面: NOT_RUN` | ✅ 一致（隔离目录用后已清理） |
| 同上（DSH_HOME 未设） | `[REFUSED]` / exit 2 | ✅ 一致 |
| 同上（DSH_HOME=真实 `~/.dsh`） | `[REFUSED]` / exit 2 | ✅ 一致 |
| 守卫 5 探针（包含双向/case/junction/相对，decoy USERPROFILE） | 5/5 exit 2；decoy sentinel 完好、零 `.agent-presets`、无新增子目录 | 新增事实（验收(1) 绕过向量实证） |
| `python skills/software-project-governance/infra/verify_workflow.py check-dsh-preset-smoke` | `Result: PASSED`，exit 0，temp home `(removed)` | ✅ 一致 |
| `python -m unittest discover -p "test_verify_workflow.py"` | `Ran 764 tests in 138.677s / OK` | ✅ 一致（Developer：Ran 764 OK） |
| `check-governance --summary-only`（×2，含全量 1 次） | `共 119 issues` / `Result: ISSUES FOUND — 119 issue(s)`；Check 28u 段 `[PASS]`（全量输出 L1158-1160） | ⚠️ 121→119 差异披露（F-7：-2、方向变少、diff 贡献 0、逐项机制未复演） |

## 复核操作披露（M7.7 合规声明）

本审查全部操作为只读或隔离：`git rev-parse/status/diff`、文件读取、grep（只读）；pytest / unittest（只读 + tempfile 自清理）；隔离冒烟（`DSH_HOME=%TEMP%\feat015-review-*`，用后删除）；两条拒绝路径（守卫写前拒绝，零写入）；5 探针（decoy `USERPROFILE`/`HOME` 指向 %TEMP% decoy，零真实 home 接触，decoy 用后删除）；check-dsh-preset-smoke / check-governance（只读 + 自建临时 DSH_HOME 并清理）。**未对真实 `~/.dsh` 执行任何写操作；未修改任何产品/治理文件（唯一产出物 = 本报告，新建文件）。**

## 未验证项声明

| 项 | 状态 | 说明 |
|----|------|------|
| live LLM 会话行为（预设会话内 skill 实际挂载 + /governance 实际触发） | 未验证（by design NOT_RUN） | 与交付物口径一致——本门禁不宣称该面；关闭标准(2) 的 live 面处置见 F-1 |
| shipped preset 在**已安装包内**（node_modules 挂载点）的 dsh 进程内解析 | 未验证（isolation 级推断） | 门禁验证的是仓内 `presets/governance/` 原文 + URL 数学等价性（baseUrl 相对解析与位置无关，随包移动仍成立——推理已文档化于 composition 注释 L34-40）；dsh 进程内实际挂载未执行 |
| check-governance 121→119 的逐检查归因 | 未逐项复演 | 需回放 Developer 时点治理状态（会修改 .governance，越 reviewer 权限）；归因链与方向分析见 F-7 |
| copy 模式 CLI 冒烟 | 未单独复跑（代码面已核） | incidents L10 记录 Developer 实测 exit 0；本审查核对了 copy 模式下 gesture target 解析依赖 `skill-root.txt`（install_preset L171-173 两种模式均写）→ 逻辑成立；如需可由 Coordinator 补一条 copy 模式复跑 |

## 遗留项表

| # | 内容 | 责任 | 截止 |
|---|------|------|------|
| F-1 | 关闭 RISK-049 标准(2) 时限定验证等级（isolation 加载面）+ 登记 live/headless 会话面后续候选 | Coordinator | 关闭该标准/风险前（MUST） |
| F-2 | 守卫包含双向/case/junction 的 decoy 回归用例（沿用 `_decoy_home_env` 模式） | Developer（下一波次） | 0.79.0 周期内 |
| F-3 | `sys.stderr.reconfigure`（对称 stdout） | Developer（遗留候选） | 下一波次 |
| F-4/F-5/F-6 | 函数拆分建议 / witness 消息措辞 / real_home_writes 严格化（均为可选增强） | Developer（讨论级） | 择机 |
| F-7 | 收口时记录 check-governance 新基线 119（注明与 121 差异归因链） | Coordinator | 本任务 evidence 回写时 |
