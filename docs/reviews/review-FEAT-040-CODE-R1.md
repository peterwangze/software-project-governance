# 审查报告 — FEAT-040-CODE-R1（复审）

- **任务**: FEAT-040 — 多平台回归 + 灰度开关 + 回滚（切片 A 集成收尾）
- **Round**: **R1**（复审）
- **前轮引用**: `docs/reviews/review-FEAT-040-CODE-R0.md`（NEEDS_CHANGE；P0=0 / **P1×2（blocking）** / P2×3 / P3×4；`unresolved_blockers=2`）——本报告逐条比对全部 9 条 findings，标注「已修复/未修复/新引入」
- **审查者**: Code Reviewer Agent（只读审查；唯一写操作 = 本报告）
- **审查对象（R1 改动面）**:
  1. `skills/software-project-governance/infra/behavior_profile.py` — `_clip_value`（L179-192）/ `INVALID_VALUE_LIMIT`（L184）/ `INVALID_VALUE_ACTION`（L154-161）/ `resolve_behavior_profile` 的 invalid 记录（L258-265）
  2. `skills/software-project-governance/infra/bootstrap_aggregate.py` — `_next_actions` 尾部 invalid 插桩（L730-737）/ `_invalid_behavior_action()`（L740-752）
  3. `skills/software-project-governance/infra/tests/test_behavior_profile.py` — `_fixture_plan_text`（L92-102）/ `_payload` 注入（L331-338）/ 双臂参数化（L377-421）/ 新增 4 例（L423-506）/ census 无关
  4. `skills/software-project-governance/infra/tests/test_projection_legacy_snapshots.py` — `test_census_is_structural_not_a_disclosed_number`（L154-206）
- **方法与限制（事实依据红线声明）**: 审查者工具面 = Read/Grep/Glob。**未执行任何测试、未运行任何 CLI、未做 git 操作**——凡涉运行时（pytest 通过/失败计数、CLI 实测输出、变异测试翻红、resident token 计数）的结论一律标注「未实测」，不作为通过依据。所有阻塞/通过结论均指向文件:行号或 Grep 逐字命中。

---

## 一、前轮 findings 逐条比对（复审核心）

### 汇总表

| R0 编号 | 级别 | 位置 | R1 结论 | 关键证据 |
|---------|------|------|---------|----------|
| P1-1 | P1 blocking | test_behavior_profile.py:273-278 / :307-322 / :355-366 | ✅ **已修复**（聚合面；CLI 面仍为 env-only，见 P3-R1-1） | `test_plan_tracker_arm_reaches_the_aggregate_face`（:423-440）+ 双臂参数化（:400-421） |
| P1-2 | P1 blocking | bootstrap_aggregate.py:692-730 | ✅ **已修复** | `_next_actions` L730-737 + `_invalid_behavior_action` L740-752 + 测试 :465-499 |
| P2-1 | P2 | test_projection_legacy_snapshots.py:142-152 | ⚠️ **部分修复**——恒等式成立但与实现同构、非全划分的独立证明（残余 → P3-R1-2） | `_legacy_census` L354-365 与测试恒等式 :190-196 |
| P2-2 | P2 | test_behavior_profile.py:307-322 | ✅ **已修复**（去耦合彻底——`_payload` 全面注入 fixture） | `_payload` :331-338 + 全类改用 fixture :340-515 |
| P2-3 | P2 | behavior_profile.py:235-238 | ✅ **已修复**（`invalid` 通道；`env_value` 通道未同步——见 P3-R1-3） | `_clip_value` L187-192 + L261/L265 + 测试 :151-162 / :501-506 |
| P3-1 | P3 | behavior_profile.py:378-380 | ✅ 按申报转跟踪（未修，一致） | :405-406 无负例，如实标注 |
| P3-2 | P3 | behavior_profile.py:253-255 | ✅ 按申报转跟踪（未修，一致） | `env_value` 仍 `str(raw_env)` 未裁 |
| P3-3 | P3 | behavior_profile.py:299-301 | ✅ 按申报转跟踪（未修，一致） | `next_action_line` 仍硬编码 5 名 |
| P3-4 | P3 | version-projections.json:124-131 | ✅ 存量欠账，本批未动（一致） | 与 R0 记录同态 |

**零新增 P0 / P1。** 新增 3 条 P3（P3-R1-1~3），均为「R1 修复面的收口建议」，不构成阻塞。

---

### P1-1（R0）— plan-tracker 臂无聚合面/CLI 面证据 → ✅ 已修复

**R1 实现**：

1. `_fixture_plan_text(behavior_profile=None)`（test_behavior_profile.py:92-102）自造完整 plan-tracker 文本：`## 项目配置` 头 5 行（项目名称/当前阶段/工作流版本/触发模式/操作权限模式）+ 可选 `- **behavior_profile**: <v>` + `_FIXTURE_PLAN_SECTIONS`（`## 项目总览` 表行 + `## Gate 状态跟踪` G1/G2 行 + 2 条合成任务行）。
2. `_payload(self, env, plan_text=None)`（:331-338）经 `patch.object(ba, "_read_text", return_value=plan_text)` 注入——**这是真实代码路径**：`_build_payload` L620 `plan_text = _read_text(plan_path)` 正是活体读取点，注入后 plan_tracker 文本沿 L674-675 真实流入 `_behavior().behavior_face(plan_tracker_text=plan_text)`。
3. `test_plan_tracker_arm_reaches_the_aggregate_face`（:423-440）断言四件套：`profile=="legacy"`、`source=="plan-tracker"`、`reverted` 长度 == `len(LEGACY_REVERTS)`、`next_actions[0]` 含「灰度回退生效」——**逐项命中 R0 修复建议的字面要求**（R0 第 100 行：断言 profile/source/next_actions[0] 三件）。
4. 双臂参数化 `test_legacy_changes_only_the_declared_faces`（:377-421）：`arms = {"env": (env_var, modern_text, modern_text), "plan-tracker": ({}, legacy_text, modern_text)}`，每臂 `modern = self._payload({}, modern_text)` / `legacy = self._payload(env, plan_text)`，并显式断言**前提**：`modern["behavior"]["source"]=="default"`（:404）、`legacy["behavior"]["source"]==arm`（:407）、`baseline["behavior"]["source"]=="default"`（:390）。R0 P2-2 的「翻红原因被误读」风险被前提断言消解 ✓。

**接续点守卫强度（R0 P1-1 的核心风险）**：R0 的担忧是「`_build_payload` 丢失 `plan_tracker_text` 传参 → 守护网不翻红」。静态推演：若 L674-675 退回 `behavior_face()`（无参），则所有 plan-tracker 文本驱动的用例（:434-440 / :397-399 / :444-449 / :457-458）全部翻红——**该风险已被守卫**。CLI 子进程两例（:534-545）仍仅 env 臂，但 CLI 无 plan-tracker 注入通道（`--project-root` 才接活体文件），故非缺口而是覆盖面注记。

**残余（非阻塞，见 P3-R1-1）**：无「真实 plan-tracker 文件 → CLI 子进程 → behavior 面」的端到端一例。

**判定**：✅ 已修复（R0 修复建议逐项落实，守卫对目标回归形态有齿）。

---

### P1-2（R0）— 非法值未进入 `next_actions` → ✅ 已修复

**R1 实现**（bootstrap_aggregate.py:730-737）：

```python
rollback = _behavior().next_action_line(payload.get("behavior"))
if rollback:
    actions.insert(0, rollback)
if (payload.get("behavior") or {}).get("invalid"):
    actions.insert(1 if rollback else 0, _invalid_behavior_action())
return actions[:5]
```

**插入位置语义逐态推演（四种组合，全部正确）**：

| 态 | rollback | invalid | 结果 | 与设计意图对齐 |
|----|----------|---------|------|----------------|
| 双臂皆未触发 | None | 空 | 不变 | ✓ |
| env=legacy 生效 | 有 | 空 | `[rollback] + 原序` | ✓（R0 既有语义不变） |
| env=非法（如 `legacyy`） | None | 有 | `[invalid] + 原序` | ✓（R0 建议「或插入首位」；测试 :481-483 硬断言 `hints[0]==0`） |
| env=legacy + plan 非法 | 有 | 有 | `[rollback, invalid] + 原序` | ✓（R0 建议原文：「可放在回退行之后」；测试 :497-499 断言 `actions[0]` 回退 + `actions[1]==INVALID_VALUE_ACTION`） |

**单一事实源**：`INVALID_VALUE_ACTION` 定义在 `behavior_profile.py:158-161`（与 `next_action_line` 同模块，模块 docstring §4 L43-44 记 P2-3/P1-2 两处修复的归属），`bootstrap_aggregate._invalid_behavior_action()`（:740-752）只做转交 `return _behavior().INVALID_VALUE_ACTION` ——**无重复字面量**（Grep：该文案在 `infra/` 内仅出现于 behavior_profile.py:159-160 一处定义 + 测试经常量引用）。测试 :476 以 `action == bp.INVALID_VALUE_ACTION` 判等（而非子串），常量改名/改文时双向联动 ✓。

**与「5 条上限」的交互**：`[:5]` 在两次 insert 之后，两个提示都不可被上限吞掉 ✓。代价见 P3-R1-1（两提示同时在场时普通项被挤出）。

**残留观察（非缺陷）**：`test_invalid_env_value_is_disclosed_in_the_face`（:460-463）与 `test_invalid_env_value_also_reaches_next_actions`（:465-485）是两条独立用例，重复了 env=legacyy 的构造——可维护性上是轻微冗余，非问题。

**判定**：✅ 已修复（语义正确、位置与 R0 建议一致、单一事实源成立）。

---

### P2-1（R0）— census 数字为纯披露、无钉子 → ⚠️ 部分修复

**R1 实现**（test_projection_legacy_snapshots.py:154-206）：

```python
self.assertEqual(census["inventory"], len(vw._projection_source_files(ROOT)))
self.assertEqual(census["inventory"], len(rp._mirror_inventory(ROOT)))
projected = (census["inventory"] - census["absent"]
             - census["identical"] - census["divergent"])
self.assertGreaterEqual(projected, 0, census)
self.assertEqual(census["inventory"],
                 census["absent"] + census["identical"] + census["divergent"]
                 + projected, census)
... declared <= divergent / undeclared_in_scope 无重复且 <= divergent / 六计数非负 int
```

**恒等式数学评估（R0 修复建议的「结构性钉子」是否名副其实）**：

`release/projection.py::_legacy_census` 的循环体（L354-365）是**严格四分类**，且靠 `continue` 保证互斥：

```
if rel in projected: continue                 # projected 桶（不落任何计数）
if not fixture.is_file(): absent += 1; continue
if fixture.read_bytes() == canonical: identical += 1; continue
divergent += 1                                 # 兜底 = divergent
```

- `inventory` 恰在循环首行自增（L355）→ `census["inventory"] == len(_mirror_inventory(root))` 是**逐元素计数的直接后承**，非巧合 ✓；
- 四个桶互斥由 `continue` 结构保证（`projected` 先于其余判断，其余三分支也各自 `continue`）✓；
- 测试把 `projected` 定义为**差值**（:190-191），因此 `inventory == absent+identical+divergent+projected` 是**该定义的算术恒等**，即在任何实现下都成立——它不能证伪「分类是否真的完备」。

**因此**：该测试的**净增量**是三条真实约束——(a) census 的 inventory 与两个独立读者集合长相等（见下）；(b) `declared ≤ divergent`、`undeclared_in_scope` 去重且 ≤ `divergent`；(c) 六计数为非负 int。R0 P2-1 的诉求「给 census 加结构性钉子，使树变化时叙述失效可被捕获」**已被机械满足**（docstring 亦如实降级为「writing time 观测快照」，:157-163）。

**但两处口径夸大应在下一轮收口**：
1. **「全划分」不是被证明的，是被结构保证的**——恒等式因 `projected` 由差值反推而同构于实现。若要**独立**证明互斥完备，需要可证伪的旁路断言，例如 `census["divergent"] == 0 or not (declared 与 projected 交集非空)` 形态的探针，或直接断言 `projected == len({t for t in 投影目标} ∩ inventory)`（由 registry 独立求交，而非由 census 自己减出来）。当前形态会在「某文件既被投影又被计为 divergent」的实现退化下**沉默通过**。
2. **注释措辞「two independent readers」（:182-183）过强**——`rp._mirror_inventory`（release/projection.py:376-407）与 `vw._projection_source_files`（verify_workflow.py:6740-6752）是**逐字同构的两份拷贝**（同一 12 条模式、同一 `__pycache__`/`.pyc` 过滤、同一 `sorted(set(...))`）。独立的是**模式的取得方式**（后者 AST 解析字面量 tuple；前者被 engine import），二者仅在「运行时 tuple 被动态篡改」这一形态下才分叉。两份拷贝同时被改错（如过滤条件一起改）时该断言不会翻红。**这不是缺陷**（运行期 tuple 才是权威，AST 复算确有防漂移价值），但注释把「同构拷贝」说成「两个独立读者」会让后人高估其力。

**判定**：⚠️ 部分修复——P2-1 的机械诉求达成（有钉子、docstring 已降级），但钉子的证明力弱于其自述（恒等式同构 + 「独立读者」实为同构拷贝）。残余登记为 **P3-R1-2**（非阻塞；R0 P2-1 本身即「建议」级，且 R0 明确「不要求钉死绝对数」）。

---

### P2-2（R0）— 非干扰测试对活体 plan-tracker 耦合 → ✅ 已修复

**R1 实现**：`_payload`（:331-338）默认 `plan_text = _fixture_plan_text()`，并经 `patch.object(ba, "_read_text", return_value=plan_text)` 注入；`AggregateFaceTests` 全类（:340-515，共 15 例）改经该方法，**无一处读取活体 `.governance/plan-tracker.md`**。

**去耦合彻底性检查（是否还有活体读取残留）**：
- `AggregateFaceTests` 内 `_build_payload` 的 4 个文件读取点全部经 `ba._read_text`：plan（L620）、risk（L653）、decision（L662）——均被 `patch.object(ba, "_read_text")` 覆盖 ✓。
- `setUpClass`（:326-329）仍走真实 `resolve_entry.resolve_host_root(str(ROOT))` + `resolve(...)`——**这是有意的**（docstring :321-323 自陈：resolve envelope 与宿主根保持真实，以便 fail-closed 权威与非干扰断言都有实存面）。`resolve` 面读 `.governance/` 的**存在性/新鲜度**元数据，不读 `behavior_profile` 键 → 该耦合对 P2-2 的目标（活体键改变测试前提）无影响 ✓。
- `CliSmokeTests`（:518-545）仍走活体 CLI：它断言 `profile=="modern"`（:538）——**若活体 plan-tracker 被设为 `behavior_profile: legacy`，该用例会翻红**（副作用：`_run` 只 pop env 变量，不隔离活体文件）。已核验当前活体 `.governance/plan-tracker.md` **无 `behavior_profile` 键**（Grep 命中仅 FEAT-034/036/037/038/040 任务行，无该键）→ 现状不红。**这是与 R0 P2-2 同类残留，但对象是 CLI 冒烟例而非非干扰例，且 R0 的原始论证（「翻红原因被误读为非干扰破坏」）不再适用**——CLI 例翻红时的语义是「活体已开项目级 legacy，而本用例断言默认 modern」，误导性低。登记为 P3-R1-1 的一部分，不另开编号。
- 其余类：`ResolutionTests` 全用自造文本 ✓；`BoundaryContractTests` 用注入 patch ✓；`PublicationTests` 读协议文本（内容守护，非活体配置耦合）✓；`FailClosedUnaffectedTests` 读源码 AST ✓。

**判定**：✅ 已修复（R0 P2-2 所指的「活体键翻转测试前提」已消除；残余为 CLI 冒烟例的同类耦合，语义无害）。

---

### P2-3（R0）— `invalid` 值无上界 → ✅ 已修复（`invalid` 通道）

**R1 实现**：`INVALID_VALUE_LIMIT = 64`（behavior_profile.py:184）+ `_clip_value`（:187-192，超限 `text[:limit] + "…"`，docstring「never a silent trim」）+ 两处调用点 `L261`（env 臂）/ `L265`（plan-tracker 臂）。限定符注释（:179-183）与 `bootstrap_aggregate._clip` 的披露口径对齐 ✓。

**截断边界核算（是否 off-by-one）**：`len(text) <= 64` 原样返回；`len > 64` → `64 + 1 = 65`。R0 P2-3 未指定「截断后 ≤64」还是「64+省略号」，且本模块既有先例 `_clip`（bootstrap_aggregate.py:147-149）为「截断后超限」（`0..limit-1` + `"…"`）——**两处实现并不一致**（`_clip` 得 81 字符 vs `_clip_value` 得 65 字符），但**都在调用侧被披露**（各自 docstring 声明），测试 :156 与 :505 均以 `INVALID_VALUE_LIMIT + 1` 显式编码该口径 → **有意披露，非 off-by-one**。建议（P3-R1-3）：仓内两个裁剪器口径不一致，宜在 `_clip_value` docstring 点明与 `_clip` 的差异，或统一为「结果 ≤ limit」（`text[:limit-1] + "…"`）。

**`env_value` 通道**（R0 P3-2 同族）：`resolve_behavior_profile` 的 `env_value`（:280）仍为 `str(raw_env)` **未裁剪**——与 `invalid[].value` 现在受 64 限形成不对称。**但该字段不进入 `behavior_face`**（:299-307 只投影 profile/source/env_var/plan_tracker_key/reverted/invariants/invalid）→ JSON 聚合面不受影响，故非放大面，**不构成新引入缺陷**，仅登记（P3-R1-3）。

**判定**：✅ 已修复（目标通道 64+…，双向测试：超长截断 + 短值逐字不变 :160-162；R0 申报「CLI 实测 200 字符→len=65」**静态核验与实现一致、未实测**）。

---

### P3-1 ~ P3-4（R0）— 未修，与申报一致

| 编号 | 位置 | 状态核实 |
|------|------|----------|
| P3-1 | behavior_profile.py:405-406 | ✅ 未修（一致）：规则④「duplicate safety invariant id」分支仍无负例；`:226-235` 只注入 duplicate surface + markerless |
| P3-2 | behavior_profile.py:280 | ✅ 未修（一致）：`env_value` 仍原值回显；聚合面无该字段（见 P2-3 判定） |
| P3-3 | behavior_profile.py:326-328 | ✅ 未修（一致）：`next_action_line` 仍硬编码「升级确认门/异常不隐藏/fail-closed/真实环境防护/复审必达」五名，与 `SAFETY_INVARIANTS`（:121-152）双源；**逐字核对仍一致** ✓ |
| P3-4 | version-projections.json:124-131 | ✅ 存量欠账，本批未触碰（一致） |

**判定**：✅ 申报属实（「转跟踪未修」四字与文件状态逐条相符，无虚报修复）。

---

## 二、本轮复审要点逐项回答

### 要点 1：P1-1 修复核实（文本构造 + 参数化 + 变异可信度）

- **plan-tracker 文本是否匹配解析面**：`_fixture_plan_text` 的键行形 `- **行为键**: 值` 与 `_CONFIG_LINE_RE`（behavior_profile.py:177）逐字匹配 ✓；与 `parse_project_config`（bootstrap_aggregate.py:235 的 `- \*\*(.+?)\*\*:\s*(.+)`）同形 ✓。节界正确：`## 项目配置` 之后紧跟另一 `## ` 标题即截断（`plan_tracker_value` L228-229）✓。`:174-177` 的负例另证明「后节同键不被读取」。
- **双臂参数化实现**：`arms` dict 三元素元组（env / engaged plan_text / modern control text）语义自洽；env 臂的 modern control 与 engaged 仅差变量，plan 臂仅差单元格 ✓。9 面比较集（:416-417）与 R0 相同，未借机缩窄——**R0 报告第 35 行称「10 个面」并列了 9 名称，属 R0 的措辞溢出**（`behavior` + `next_actions` 已单独断言），本处无遗漏。
- **变异申报可信度（静态评估）**：申报「改 `None`→3 例翻红后还原」。静态核对：若把 `_payload` 的 `plan_text=None` 默认改为不做 fixture 注入，或把 `use_plan_tracker` 参数删掉，则 :434-440（profile/source 双断言）、:404（modern 腿 source 须为 default）、:457-458（text 面 source=plan-tracker）必然翻红——**测试结构确有齿** ✓。变异测试本身**未实测**（无 pytest 面），但「有齿」这一属性可由断言内容静态证实。
- **一处诚实性核对**：`_payload(self, env, plan_text=None)` 里 `if not env: os.environ.pop(bp.ENV_VAR, None)`（:334-335）依赖「空 dict 即代表未设置 env 臂」的约定。该约定与 `patch.dict(os.environ, {}, clear=False)` 的无操作语义一致 ✓；但对「调用方想注入空值 env」这一形态不可表达（不影响现有用例，仅契约注记）。

### 要点 2：P1-2 修复核实（插入位置 + 5 条上限交互 + 单一事实源）

见上文 P1-2 段落：四态推演全部正确；两提示均在 `[:5]` 之内；`INVALID_VALUE_ACTION` 单一事实源成立（定义处 behavior_profile.py:158-161，消费处仅转交）。

**上限交互的代价（已实测的可推演部分）**：`_next_actions` 普通项最多 6 类（scenario / migration / 逾期风险 / deferred 健康 / 候选或空原因 / hooks），`[:5]` 本就可能丢尾项；两个提示同时在场时**必然**丢一个普通项——静态推演最坏组合下被挤出的是**候选行**（`从候选开始：<task_id>（<priority>）`，即 DEC-143「完成必推荐」的机器投影）。这是一个真实（但可接受）的取舍：R0 的三条设计意图（回退必达 + 非法值必达 + 5 条上限）三者不可同时满足。登记为 **P3-R1-1**，建议在 `_next_actions` 的注释里显式声明「who gets dropped」，避免后人误以为三条意图同时被满足。

**文案长度与兜底裁剪**：`INVALID_VALUE_ACTION` 实测字符数（静态）约 61；`_EMERGENCY_CLIP=120`（:767）高于它 → 第 ④ 级兜底不会吞掉该提示 ✓；`test_face_with_both_hints_still_fits_the_output_budget`（:512-515）另证两提示齐备时仍 ≤8KB ✓。

### 要点 3：P2-1 恒等式数学

见上文 P2-1 段落：**四类互斥完备性由 `_legacy_census` 的 `continue` 结构保证**（构造性）；测试恒等式因 `projected` 由差值反推而与之同构，**不能独立证伪分类完备性**；「two independent readers」实为同构拷贝。结论：机械诉求达成，证明力弱于自述 → P3-R1-2。

### 要点 4：P2-2 去耦合彻底性

见上文 P2-2 段落：`_read_text` 三个调用点（L620/L653/L662）全被覆盖，**无活体配置读取残留**；仅 `CliSmokeTests`（:534-545）保留活体耦合（无害，见该段）。另核验活体 `.governance/plan-tracker.md` 当前无 `behavior_profile` 键（Grep 零命中）→ 全批测试现状不红。**去耦合在 `AggregateFaceTests` 内是彻底的。**

### 要点 5：P2-3 截断边界

见上文 P2-3 段落：`64 + "…" = 65` **有意披露**（两处测试均以 `INVALID_VALUE_LIMIT + 1` 显式编码），非 off-by-one；但与本仓既有裁剪器 `_clip`（「截断后 ≤ limit」得 81）**口径不一致**——登记 P3-R1-3。

### 要点 6：新引入检查 + 通过面不回退（R0 十一条独立证实强项的复核）

R0 报告第七节列出的十一项强项，逐项复核**是否被 R1 改动破坏**：

| # | R0 强项 | R1 状态 | 复核依据 |
|---|---------|---------|----------|
| 1 | 层 1 数据层：`ALLOWED_REVERT_CLASSES={performance}` + FEAT 交集判 FAIL | ✅ 不回退 | behavior_profile.py:83 / :388-393 / :410-415 未改；`:213-224` 注入负例未改 |
| 2 | FEAT-035 只在 `SAFETY_INVARIANTS`、不在 `LEGACY_REVERTS` | ✅ 不回退 | :87-116（feats=034/034/036/038）与 :123（FEAT-035）未改；`:198-205` 双向断言未改 |
| 3 | 层 2 文本层：5 不变量 marker + 6 面 `行为灰度开关` | ✅ 不回退 | :121-152 marker 未改；`PROTOCOL_SURFACES` 6 面未改；本批 6 处协议面文字改动**未删任何 token**（Grep 复核 6 面仍含全部 marker） |
| 4 | 层 3 非干扰契约（10 面相等 + health 双态 deferred + 不借绿） | ✅ **增强** | :416-421 保持，且新增双臂 + 前提断言（:386-408） |
| 5 | 注入式负例证明 checker 会红（非自证循环） | ✅ 不回退 | :213-235 未改；新增无削弱 |
| 6 | 6 面 marker 逐字在位 | ✅ 不回退 | Grep 复核：governance-init.md:219/:861 等 4 模板 + governance.md:99 + bootstrap.md:33/:42 + SKILL.md:74/:81 + TOOLS.md:596-605 |
| 7 | 路由层 11,934B/12,288B（余量 354B） | ✅ 不回退（静态） | 本批未改 `commands/governance.md`；守护 `:304-307` 未改；字节数未重测 |
| 8 | fixture router 与 canonical 逐字节相等 + registry/manifest 双边登记 | ✅ 不回退 | `:46-61` 未改；R1 未触碰 registry/manifest |
| 9 | 三条 legacy 声明 FAIL 路径各有可证伪负例 | ✅ 不回退 | test_projection_legacy_snapshots.py:235-267 未改 |
| 10 | `--ttfa-acceptance` 阈值入码 / PENDING 不借绿 / 成对 TTW | ✅ 不回退 | R1 未触碰 governance_cost.py（本批改动面不含该文件） |
| 11 | R6 Δ0（惰性 import + 冻结计数 199） | ✅ 不回退（静态） | `_behavior()` 仍函数内 import（bootstrap_aggregate.py:100）；Grep 全 `infra/*.py`：`import behavior_profile` **仅** :100 与测试 :47 两处 → Δ0 结构仍成立（未重测计数） |

**新引入检查**：五维度复查 R1 改动面（见第三节）——**未发现新引入缺陷**。特别核对的三个「新代码可能踩到旧契约」点：
- `_next_actions` 的 `payload` 在插入前已含 `behavior`（:674-676 调用顺序）→ `payload.get("behavior")` 不会因顺序问题取空 ✓；
- 新提示是常量（不含由环境值拼装的变长片段）→ 不会被 `_clamp_strings` 的 120 上限静默改写 ✓；
- `test_bootstrap_aggregate.py` 既有的 `next_actions` 断言（:387-391 / :621-625）均无「无效 env」前提 → 新插桩在既有用例中惰性不触发，**不产生既有测试回退** ✓。

### 要点 7：AI 专项 5 项（本轮改动面）

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | ✅ 无 | 新增 mock 用法 `patch.object(ba, "_read_text", return_value=...)`（:336）是**注入真实读取点**（非替身被测逻辑）；`patch.dict(os.environ)`（:333）与 R0 同。无 MagicMock 自证、无 `assert_called` 类空转断言 |
| 2 | 硬编码返回值 | ✅ 无 | `INVALID_VALUE_LIMIT+1`（:156/:505）是**口径编码**而非桩值；`_fixture_plan_text` 是夹具；新提示文案是产品常量（有单一事实源）而非测试侧期望写死 |
| 3 | 幻觉 API 调用 | ✅ 无 | 新增仅用现有 API：`patch.object`/`ba._build_payload`/`ba.format_text`/`ba._enforce_projection_budget`/`ba._payload_bytes`/`vw._projection_source_files`/`rp._mirror_inventory`/`rp.FIXTURE_PREFIX`——逐一 Grep 存在于对应模块（verify_workflow.py:6740、release/projection.py:376/:28）|
| 4 | 未实现 TODO | ✅ 无 | R1 改动面无 TODO/FIXME/pass 占位；`_invalid_behavior_action` 是完整实现（转交常量） |
| 5 | 过度实现 | ✅ 无 | 修 P1-2 未新增 CLI 面/配置项；`_clip_value` 单一职责；「变异测试」未落成常驻测试（无过度基建）；R1 未顺手扩面（P3×4 如实转跟踪） |

---

## 三、五维度审查（针对 R1 改动面）

### 维度 1：正确性

- `_next_actions` 插入顺序（:727-737）四态推演正确（见 P1-2 表）；`[:5]` 位置正确。
- `_invalid_behavior_action()` 定义在调用点之后（:740 vs :735）——Python 运行期解析，无问题；但**可读性**上把 helper 与调用点相邻反而更好（现状 helper 紧邻调用函数之后，可接受）。
- `_clip_value`：`str(value or "")` 对 `None`/`""` 安全（不会 `len(None)`）✓；`limit` 参数化便于复用 ✓。
- `resolve_behavior_profile` 的两处 invalid 记录（:258-265）不改变落臂判定（`env_status=="invalid"` 时 `env_profile is None`，故 `env_status != "set"` 继续落下一臂）——**裁剪动作与判定解耦，未引入行为变化** ✓。
- 边界条件：`invalid` 列表最多 2 条（每臂 1 条），无上界问题的残留（R0 P2-3 建议的「或对 invalid 条数设上限」无需实施——条数天然封顶）✓。

### 维度 2：安全性

- 本次改动**只增加披露**（把已被静默落臂的非法值提升为动作行），未放宽任何判定；`resolved_root_ok` 权威面未触碰（fail-closed 结构不变）✓。
- 数据流入：`_clip_value` 收窄了唯一「外部可控变长串进入聚合面」的通道（64+…），**方向正确**；`env_value`（:280）未裁剪但**不出现在聚合面**（:299-307 无该键）→ 无放大面（见 P3-R1-3）✓。
- 无注入/密钥/权限面变化；测试夹具无凭据。

### 维度 3：可维护性

- 单一事实源纪律在本轮**加强**：文案入 `behavior_profile`，聚合侧只转交（:740-752）——与 `next_action_line` 同款纪律 ✓。
- docstring 质量：新增测试 docstring 均带 R0 编号溯源（:380-384 / :424-432 / :466-472 / :155-163），后人可追溯「为什么有这条断言」——**本轮最显著的可维护性收益** ✓。
- 轻微冗余：:460-463 与 :465-485 重复构造 env=legacyy（P3-R1-3 附带）。
- 函数长度：`_next_actions` 由 39 行增至 46 行（:692-737），仍 <50；`_fixture_plan_text`/`_plan_tracker_text` 双夹具并存（:55-67 与 :92-102）——**两个夹具语义不同**（前者专测解析器节界，后者供聚合面），命名未区分（都叫 `_plan_tracker_text` / `_fixture_plan_text`）→ 可读性可改进，非缺陷。

### 维度 4：性能

- `_next_actions` 新增成本 = 一次 dict 取值 + 一次常量插入，O(1) ✓；无新 I/O、无新循环。
- `_clip_value` 仅在 invalid 时调用（每臂至多一次），O(1) 切片 ✓。
- 冷启动面 Δ0 不回退（Grep 复核唯一 import 点仍为 :100）✓。
- 输出预算：新增一条常量提示最多 +约 61 字符，且仅在 invalid 时出现；两提示齐备的预算用例已在册（:512-515）✓。

### 维度 5：测试覆盖

- **静态计数（本报告独立复算，与 R0 的计数口径不同，故并列出）**：`test_behavior_profile.py` = **45 个 `def test_`**（Grep 逐行计数：ResolutionTests 9 / BoundaryContractTests 6 / PublicationTests 6 / AggregateFaceTests 15 / CliSmokeTests 2 / FailClosedUnaffectedTests 4 + `test_engine_exports_the_surface_census_used_by_guards` 归入最后 5 = 45）+ **43 个 `subTest` 子执行**（词表 12 + 空白 3 + 四模板 4 + 双臂 2 + 引擎面 5 + 计数非负 6 + resolver 五形 5 + 节界… 逐站实计 43）；`test_projection_legacy_snapshots.py` = **15 个 `def test_`**（与 R0 一致）+ 6 个 subTest。
- **口径差异披露（重要）**：Developer 申报「两文件 59 passed / 32 subtests」，R0 申报「34 用例 / 33 子测试」为「静态计数」——**三次计数互不相同，且本报告的静态法（45+15=60 个函数；43+6=49 个子执行）与二者均不吻合**。三者差异来源无法在无 pytest 面下判定（可能分别为「用例数/含子测试的运行计数/过滤后的通过数」）。**结论：申报的「59 passed / 32 subtests」既无法证实也无法证伪（未实测），且与静态可复算值不一致 → 登记 P3-R1-4，建议下轮由 Coordinator 以一条 `pytest -q` 输出原样入证据，避免同型口径歧义（FEAT-039 R0 的度量教训同族）。**
- **新增覆盖的实质**：P1-1（聚合面 plan-tracker 臂）、P1-2（JSON+文本双面动作信号）、P2-2（去活体耦合）、P2-3（裁剪边界双向）**均有对应可翻红用例**；缺口见 P3-R1-1（CLI plan-tracker 端到端）。
- **既有覆盖未回退**：R0 已证实的负例（注入 smuggled/duplicate/markerless、三条 FAIL 路径、AST 冻结面）全部在位且未被本批改动触碰。

---

## 四、发现列表（R1）

### P3-R1-1（建议/讨论）— 两个开关提示占满配额时，可操作项（候选行）会被挤出；CLI 冒烟例保留活体耦合

- **位置**：`bootstrap_aggregate.py:730-737`（两次 insert 后 `[:5]`）；`test_behavior_profile.py:534-545`（`CliSmokeTests._run` 仅 pop env 变量）
- **事实依据**：普通项最多 6 类（scenario / migration / 逾期风险 / deferred 健康 / 候选或空原因 / hooks，:694-723）；两提示齐备（env=legacy + plan=非法）时 `[:5]` 必然丢 1 项，静态推演最坏组合下被挤出的是候选行（DEC-143「完成必推荐」的机器投影）。CLI 两例断言 `profile=="modern"`（:538），仅 `pop` env 变量、不隔离活体 plan-tracker；已核验活体当前无该键（安全）。
- **影响**：非功能性缺陷——「回退必达 + 非法值必达」优先级高于「候选可读」，且候选行丢失仅表示本轮聚合未给推荐（用户仍可从 tasks 面看到未阻塞数）。风险在于**契约未声明**：后人可能以为三者兼得。
- **建议**：（a）在 :730-737 注释里显式写明丢弃顺序（哪个普通项会被挤出）；（b）可选：把 CLI 冒烟例改为临时 host tree（fixture plan-tracker + `--project-root`），顺带补齐「真实文件 → CLI → behavior 面」的 plan-tracker 端到端一例（R0 P1-1 的最后一寸覆盖面）。（b）非阻塞。

### P3-R1-2（建议）— census 钉子的证明力弱于其自述（恒等式同构 + 「independent readers」实为同构拷贝）

- **位置**：`test_projection_legacy_snapshots.py:182-196`（注释 + 恒等式）；对照 `infra/release/projection.py:354-365`（`_legacy_census`）与 `infra/verify_workflow.py:6740-6752`（`_projection_source_files`）
- **事实依据**：`projected` 由差值反推（:190-191）→ 恒等式 `inventory == absent+identical+divergent+projected` 在每个实现下都成立；四类互斥完备性实际由 `_legacy_census` 的 `continue` 结构（L357-365）保证，**未被测试独立证明**。`_mirror_inventory` 与 `_projection_source_files` 逐字同构（同一 12 模式 / 同一 `__pycache__`+`.pyc` 过滤 / 同一 `sorted(set)`），「two independent readers」的措辞过强（真正独立的是模式取得方式：AST 字面量 vs 运行时 import）。
- **影响**：非缺陷。R0 P2-1 的诉求（可证伪的结构性钉子、绝对数从 docstring 降级）**已达成**——docstring 已如实写「writing time 观测快照」（:157-163）。残余是后人可能高估该钉子的力。
- **建议**：把 `projected` 改为由 registry 投影目标独立求交（`{t for t in 声明目标 if t in inventory}`）再断言与差值相等——一行改动即可让「全划分」成为可证伪命题；并把注释改为「same pattern source via two access paths (AST literal vs runtime import)」。

### P3-R1-3（建议/讨论）— 仓内两个裁剪器口径不一致（64+… vs 结果 ≤limit）；`invalid` 测试轻微冗余

- **位置**：`behavior_profile.py:184-192`（`INVALID_VALUE_LIMIT=64`，结果 65 字符）vs `bootstrap_aggregate.py:137-149`（`CLIP_LIMIT=80`，结果 ≤80 字符）
- **事实依据**：`_clip_value` 返回 `text[:64] + "…"` = 65；`_clip` 返回 `text[:79] + "…"` = ≤80（先判 `len<=limit` 再 `[:limit-1]`，:147-149 静态读出）。两处均披露，故**非 off-by-one**；两处测试分别以 `INVALID_VALUE_LIMIT+1`（:156/:505）与既有口径各自编码。
- **影响**：无功能影响；跨模块一致性（后人复用哪个裁剪器）有轻微歧义。
- **建议**：统一为「结果 ≤ limit」或在对齐注释中点明差异；附：`:460-463` 与 `:465-485` 重复构造 env=legacyy，可合并为一条用例的两个断言段。

### P3-R1-4（建议）— 申报测试计数（59 passed / 32 subtests）无法用静态面复算，且与 R0 自身计数不一致

- **位置**：Developer R1 申报；对照 `test_behavior_profile.py`（45 个 `def test_` / 43 个 subTest 子执行）与 `test_projection_legacy_snapshots.py`（15 / 6）
- **事实依据**：本报告 Grep 静态复算 = 60 个用例函数、49 个子执行；R0 报告静态复算 = 34 / 33（其当时文件为 432 行，本批已扩至 610 行，故 R0 数值不应直接比对）；R1 申报 59 / 32。三套数字互不吻合，差异来源在无 pytest 面下不可判定。「59」可能是过滤后的通过数（如剔除 2 例 CLI 冒烟），但**未见任何标注**。
- **影响**：非功能缺陷，但属**度量可信度**问题——与 FEAT-039 R0「度量夸大 29%」同类教训。本轮结论不依赖该数字。
- **建议**：由 Coordinator 以一条原样 `pytest -q` 输出（含收集数）入证据行，并统一口径（「用例函数数 / 运行计数（含子测试）/ 通过数」三者分别标注）。

---

## 五、硬门槛裁决

| 门槛项 | 阈值 | 实测 | 判定 |
|--------|------|------|------|
| P0 阻塞问题数 | = 0 | **0** | ✅ |
| 5 维度全覆盖 | = 100% | 正确性/安全性/可维护性/性能/测试覆盖 逐维度有结论（第三节） | ✅ |
| 每条发现标注级别 | = 100% | 9 条 R0 findings + 4 条 R1 新发现全部带级别与位置 | ✅ |
| 设计一致性检查 | 已完成 | 两条 blocking 的修复与 R0 建议逐条对齐；三条设计意图张力已在 P3-R1-1 显式化；FEAT-035 边界、六面 marker、R6 Δ0 均未回退 | ✅ |
| AI 代码专项 5 项 | 全部完成 | 见要点 7，5/5 | ✅ |

**P0 = 0；P1 = 0；P2 = 0（R0 两条 P1 均已修复，P2 三条均已处置）；P3 = 4（R1 新增，全部非阻塞）。**

---

## 六、结论

**APPROVED_WITH_NOTES**

**unresolved_blockers=0**

**理由**：R0 的两条 blocking 均已按建议修好且**修得对**——

1. **P1-1**：plan-tracker 臂不再无证据。`_fixture_plan_text` + `patch.object(ba, "_read_text")` 是**打在真实接续点上**的正解（`_build_payload` L620 的活体读取点 → L674-675 的传参点），新用例断言 profile/source/reverted/next_actions[0] 四件套，双臂参数化把非干扰契约扩到项目级臂并补齐「前提断言」（modern 腿必须 `source=="default"`），R0 P2-2 的「翻红原因被误读」风险随之消解。
2. **P1-2**：`next_actions` 的非法值信号落在正确位置（无回退提示时居首；有回退提示时紧随其后），两种路径都有硬断言（`hints[0]==0` / `actions[1]==INVALID_VALUE_ACTION`），文案单一事实源由 `behavior_profile.INVALID_VALUE_ACTION` 承载、聚合侧只转交——与 `next_action_line` 同款纪律。
3. **P2-1/P2-2/P2-3** 均已处置（census 有结构性钉子且绝对数从 docstring 降级；非干扰测试全面去活体耦合、活体无该键可独立核实；invalid 通道 64+… 双向测试）。
4. **R0 十一条独立证实的强项零回退**——数据层 `ALLOWED_REVERT_CLASSES={performance}` + FEAT 交集判、FEAT-035 只在 `SAFETY_INVARIANTS`、6 面 marker 逐字在位、三层安全边界、注入式负例、三条 FAIL 路径负例、R6 Δ0（唯一 import 点仍为 `_behavior()` 函数内）全部静态复核不变。
5. **AI 专项 5 项全过**；未发现新引入缺陷。

**遗留（非阻塞，登记 4 条 P3）**：P3-R1-1（两提示占满配额时的丢弃顺序未声明；CLI 冒烟例保留活体耦合——顺带建议补 plan-tracker 端到端一例）、P3-R1-2（census 恒等式与实现同构、「two independent readers」措辞过强）、P3-R1-3（两个裁剪器口径不一致 + invalid 测试轻微冗余）、P3-R1-4（申报测试计数无法静态复算，建议以原样 pytest 输出入证据）。四条均为「下一轮收口」性质，不阻塞本任务终态。

**本报告的事实边界（不做的事实声明）**：未运行任何测试或 CLI（无 pytest 实测、无 `governance-bootstrap` 实测、无变异测试实测、无 `git status`）；Developer R1 申报中的「59 passed / 32 subtests / 全量 30F-3443P / resident 4,957 不增 / archguard R6 199 Δ0 / 变异翻红 / CLI 实测 200→65」**七项均按未实测处理**，本报告的通过结论不依赖其中任何一项；凡本报告给出为事实者，均指向文件:行号或 Grep 逐字命中（含：唯一 import 点、四态插入推演、`_legacy_census` 四分类结构、活体 plan-tracker 无 `behavior_profile` 键、45+15 用例函数静态计数）。
