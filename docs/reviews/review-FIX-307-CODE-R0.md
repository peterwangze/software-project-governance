# Code Review 报告 — FIX-307（dsh 0.1.5-rc.2 接入兼容性修复）

- **Task**: FIX-307（R0）——cordis.patch.yml skill-filesystem UPDATE 行 `disabled: false` + dsh 边界历史 0.1.5-rc.2 核实段 + README 恢复接入子段 + 守卫测试
- **Reviewer**: Code Reviewer Agent（只读审查；不修改产品代码、不与用户交互）
- **Round**: R0（首次审查）
- **Date**: 2026-09-11
- **Machine record**: `.governance/review-FIX-307-R0.md`（review-record CLI 机录，REVIEW-FIX-307-R0）；本文件为报告全文入库
- **审查对象**: 工作树未提交改动（Coordinator 核实 `git diff`：3 文件 +99/−4）——`cordis.patch.yml`、`adapters/dsh/README.md`、`skills/software-project-governance/infra/tests/test_dsh_adapter.py`
- **审查方法**: 逐行读三文件全部改动 + 对照只读外部事实源（安装态 dsh 0.1.5-rc.2）：`dsh-web-app/cordis.patch.yml`、`dsh-app-boot/lib/index.js`（applyEntryPatches/composeEntries/loadProfile）、`dsh/lib/profile-boot-Dk-7KqJc.js`（composeProfile/homePatchPath/allPatches）、`dsh-agent-presets/lib/index.js`（Config schema/scanRoot/writableRoot/deleteComposition）及 `presets/standard/agent.cordis.yml`、`dsh-skill-filesystem/lib/index.js`、`dsh-home-paths/lib/index.js`。测试执行结果为 Developer 自报 + 本审查静态推演佐证（逐项标注）。

---

## 一、注释技术断言逐条核实矩阵（15 项，本次审查重点）

| # | 断言 | 核实 | 证据（安装态源） |
|---|---|---|---|
| 1 | dsh-web-app 自有 patch 在 web profile 禁用 host `skill-filesystem` 行（`- id: skill-filesystem`/`disabled: true`，注释 "presets own local discovery"） | **属实** | dsh-web-app/cordis.patch.yml L402-403（行）、L399（注释）、L393-400（机制段） |
| 2 | applyEntryPatches 对非 insert patch 逐键覆盖 target 行（`disabled` 是普通可覆盖键） | **属实** | dsh-app-boot/lib/index.js L102-105：`for (const [key, value] of Object.entries(overrides)) { if (key === "id") continue; target[key] = value; }` |
| 3 | 非 insert patch 的 `config` 整体替换 | **属实** | 同上——`config` 仅是 overrides 之一，`target.config = value` 整体赋值 |
| 4 | 无 target 行的 UPDATE 仅 warn 跳过（base-only 无害） | **属实** | 同文件 L93-97 |
| 5 | 层序 bundles → profile layer → home layer → overlays → telemetry；`$DSH_HOME/cordis.patch.yml` 为新 home 层、应用于本 bundle 之后 | **属实** | profile-boot-Dk-7KqJc.js L116-118（homePatchPath）、L213-220（allPatches 顺序）、L249-250（telemetry 最后）、L232-257（composeProfile） |
| 6 | composeProfile 无 roots-forcing overlay（0.1.1-rc.2 bug 仍处修复态） | **属实** | composeProfile 仅堆叠 patch 层，无覆盖 agent-presets roots 的终局 overlay（L232-257） |
| 7 | agent-presets Config schema：`default`/`roots[].path`+`trust`/`includeUserRoot`/`includeShippedRoot` 均有效 | **属实** | dsh-agent-presets/lib/index.js L1240-1248 |
| 8 | `dshHomePath(...)` 通用 join、不校验键名，`dshHomePath('profiles')` 仍可解析 | **属实** | dsh-home-paths/lib/index.js L82-84 |
| 9 | dsh-skill-filesystem Config schemastery 可选（无 .required()），customSkillDirs-only config 合法 | **属实** | dsh-skill-filesystem/lib/index.js L6（import）、L31-44 |
| 10 | base-only profile 上 host 行本就启用，`disabled: false` 幂等无害 | **属实** | dsh-web-app patch L354-356（"The base keeps them for the TUI"）+ 断言 2 语义 |
| 11 | 恢复层序：本 bundle 经 plugin add 追加在 dsh-web-app 之后 → 后层胜出 → 行恢复启用 | **属实**（机制层） | loadProfileDirectory 按 `dsh.profile.bundles` 顺序映射 layers（dsh-app-boot L843-860）+ composeEntries 按序扁平应用 + 断言 2 |
| 12 | 引文归属 "the shipped `standard` preset's own comment"（原稿） | **误引**（→F1） | 逐字出处是 dsh-web-app/cordis.patch.yml L394-396；standard preset 实际注释（L79-83）语义支持但措辞不同 |
| 13 | "preset plane merges the host-plane registry; standard composition, skill-filesystem row comment" 引证 | **属实** | standard preset L79-83 |
| 14 | README 恢复命令与 0.1.5 机制一致（plugin add = pnpm 前转 + bundles reconcile；boot-time 重启） | **属实** | dsh-app-boot L890（命令形状错误文案）、L843-894（manifest 机制）；`link:` 协议依 Coordinator 基线 + 本仓库 FIX-290 已核实先例 |
| 15 | 新测试注释全部断言 | **属实** | 同断言 1-3、10 |

## 二、正确性重点核验

- **YAML 缩进/层级**：`disabled: false` 位于顶层 UPDATE 行 2 空格缩进、与 `name`/`config` 同级（行成员键）。经断言 2 语义推演：解析为 `{id, name, disabled: false, config}` → 逐键覆盖到 target 行——**放置正确**。若误放 config 下（4 空格缩进）将不被覆盖 disabled，新测试的精确 2 空格锚定恰好拒绝该错误形态（fail-closed）。
- **README 恢复命令**：见矩阵断言 14——与 0.1.5 机制一致。
- **测试正则假阳/假阴**（对照文件实际内容逐字符核验）：仅读 `_REPO_ROOT / "cordis.patch.yml"`——`adapters/dsh/agent.cordis.yml.template` 与 `presets/governance/agent.cordis.yml` 的同名行不在读取范围，无法造成假阳/假阴；`^- id: skill-filesystem[ \t]*$` 全文件唯一列 0 出现（注释均以 `#` 起）；行块起点/截断算术正确；双重假阳防护（块起点在行首锚 + 注释行 `#` 起始永不匹配缩进锚）；删键即 FAIL（假阴防护）；`agent-presets` 行块无 disabled 键且在锚点之前不参与匹配。

## 三、5 维度结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 1 正确性 | **通过** | 矩阵断言 1-11、14-15 全部核实；缩进/层序/覆盖语义/正则锚定均正确；修复方向与上游 by-design 路径一致（恢复而非对抗 dsh-web-app L393-396 明示的设计） |
| 2 安全性 | **通过** | 注释 + 1 YAML 布尔 + 测试新增；无秘钥/注入/权限面变化；`trust: system` 未触碰；重新启用的是本部署自带 provider |
| 3 可维护性 | **通过（有备注）** | 注释遵循 FIX-290 版本戳/日期/源引证纪律；测试就地分组、注释质量高；1 处引文误归属（F1）+ 2 处措辞（F2/F4） |
| 4 性能 | **通过（无影响）** | 1 键零运行时成本；测试对 ~7KB 文件两遍正则可忽略 |
| 5 测试覆盖 | **通过** | 守卫正中回归类（键丢失=静默失效）；红→绿 + FAIL-on-buggy 双证；字符串/正则惯例与 FIX-290 先例一致 |

## 四、AI 代码专项 5 项

mock 残留=**无**（新测试零 mock）；硬编码=**无不当**（行 id/name/缩进即被守护的不变量）；幻觉 API=**无**（被引 dsh 内部符号逐一实证存在；F1 为真实引文的出处误归属，非编造）；未实现 TODO=**无**；过度实现=**无**（最小变更）。

## 五、设计一致性（FIX-290 纪律 / trust:system）

- boundary-history 段式（版本戳 + 复核日期 + 源文件/函数引证 + "unchanged" 声明）延续到位；旧结论全部重述核实。
- `trust: system` 模型未触碰；恢复 host 行不改变预设只读边界。
- 唯一纪律缺口即 F1（引证出处错误）——恰是该纪律要防的失效模式。

## 六、发现列表

| # | 位置 | 级别 | 事实依据 | 影响 | 修复建议 |
|---|---|---|---|---|---|
| F1 | cordis.patch.yml:147-150 | **P2** | 引文 "deployment-level providers — repository plugins, a host skill-filesystem row — register into its global layer" 被归属为 "the shipped `standard` preset's own comment"；逐字出处是 dsh-web-app/cordis.patch.yml L394-396 | 未来按引证复核者会在 standard preset 中找不到该句——审计链完整性受损；语义双源为真，无行为影响 | 引文改标 dsh-web-app patch 出处（含文件+行号） |
| F2 | cordis.patch.yml:61-62/145-146；README.md:35 | **P3** | "every preset session" 过宽：governance 预设会话经自带 preset 层行仍保有目录；用户根预设亦存活 | 措辞精度 | 加限定（non-governance preset session / global layer） |
| F3 | test_dsh_adapter.py:447/461 | **P3** | 锚 `[ \t]*$` 不容忍 CRLF；姊妹守卫用 `\s*$` | CRLF 工作树 fail-closed 报警（方向安全） | 改 `[ \t\r]*$` 或归一化换行 |
| F4 | test_dsh_adapter.py:8-26 | **P3** | 模块 docstring "Covers:" 未纳入新守卫 | 文档完整性小缺口 | docstring 增补 |

**P0=0，P1=0，P2=1，P3=3。**

## 七、硬门槛裁决

| 门槛 | 裁决 |
|---|---|
| 5 维度全覆盖 | ✅ |
| 每条结论可复查事实（文件/行/源码） | ✅（矩阵 15 项带安装态源行号） |
| 未验证项如实标注 | ✅（测试为 Developer 自报 + 静态复核一致未复跑；`link:` 协议依 Coordinator 基线 + FIX-290 先例 + 命令形状直接核实；diff 范围以 Coordinator `git diff` 为权威） |
| Reviewer 只读 | ✅ |
| P0 = 0 / P1 = 0 | ✅ |
| P2 有遗留记录 | ✅（F1） |

## 八、最终结论

**APPROVED_WITH_NOTES（unresolved_blockers=0）**

修复机制经安装态 0.1.5-rc.2 源码逐条实证正确：`disabled: false` 的行成员键放置、逐键覆盖语义、层序（本 bundle 后于 dsh-web-app 应用）、base-only 幂等性、README 恢复指引、守卫测试的锚定隔离与假阳/假阴防护全部成立。修复与上游 by-design 路径（repository plugins 经 host 行注册全局层）同向。遗留：F1（P2，建议本轮修正）；F2-F4（P3）。

---

## 附录：Coordinator 处置（2026-09-11，提交前微补——FIX-304 G-1 先例）

- **F1（P2）已修复**：两处归属改为 dsh-web-app patch 注释，含精确引证（"dsh-web-app cordis.patch.yml L394-396"）；grep 复核无残留误归属。
- **F2（P3）已修复**：三处限定口径——头注/disabled 段注改 "every non-governance preset session"（段注补 governance 预设经自带 preset 层行保有目录）；README 改"非治理预设会话中 /governance 手势失效；bundle-only 安装时治理预设亦从预设选择器消失（用户根预设不受影响）"。
- **F3（P3）已修复**：两处锚 `[ \t]*$` → `[ \t\r]*$` + 守卫注释补记容忍口径；修复后重证 FAIL-on-buggy（删键→1 failed 0.09s→恢复绿，容忍仅行尾 CR 不弱化 fail-closed）。
- **F4（P3）已修复**：docstring `Covers:` 增补 FIX-307 bundle patch 守卫行。
- **处置后验证**：`test_dsh_adapter.py` **40/40 passed**；`git diff --check` 干净；`check-dsh-skills-manifest` PASSED（35/35）。
