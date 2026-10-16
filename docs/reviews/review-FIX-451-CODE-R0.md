# Review Report: FIX-451-CODE-R0 — hooks CRLF 根治

- **Task ID**: FIX-451（R0，独立代码审查）
- **审查对象**: staged 3 文件 delta（+169/−4）：`.gitattributes`（+11）、`skills/software-project-governance/infra/release/projection.py`（+52/−4）、`skills/software-project-governance/infra/tests/test_release_projection.py`（+110）
- **背景**: RISK-068/EVD-1717 移交链——autocrlf 环境 hooks CRLF → `$` 锚 transformed_text 匹配 0 次 → projection 全家 BLOCKED
- **审查者**: Code Reviewer Agent（独立审查，非自审）
- **日期**: 2026-10（审查会话当日）

## 结论

**APPROVED_WITH_NOTES** · unresolved_blockers=0

| P0 | P1 | P2 | P3 |
|----|----|----|----|
| 0  | 0  | 1  | 2  |

零阻塞。staged delta 正确修复 RISK-068 移交链根因，契约保全经实证，red-on-buggy 主张经独立复证成立。备注项均为边界披露，不阻塞合并。

---

## 审查方法与证据基础

- `git diff --cached` 通读全部 3 文件；承载文件（projection.py 全文 763 行、test_release_projection.py 全文 407 行、.gitattributes 全文、version-projections.json 全文 347 行）实读。
- 属性/EOL 实测：`git check-attr text eol`、`git ls-files --eol`。
- 引擎行为实测：`release-projection --write`、`check-projection-sync`、pytest（两文件 `-k "projection or SdIntegrity"`）。
- red-on-buggy 独立复证（非 stash）：%TEMP% 沙箱组装「HEAD 版 projection.py（cmd 字节级重定向提取，避免 pwsh 管道行尾污染）+ staged 版测试文件」，测试文件自带 `sys.path.insert(INFRA)` 导入，结构自洽；沙箱确认 HEAD 版无 `_crlf_tolerant_subn` 后跑测，跑毕删除。全程零仓库触碰，故无需 SHA256 恢复校验（方法披露：以沙箱隔离替代 stash 复证，成本更低且零风险）。
- 审查全程零写入（唯一写入面=本报告）、staged 状态前后一致（`git status --short` 首尾比对：staged 恒为 3 文件 +169/−4）。

## 审查清单逐项证据

### 1. 算法正确性（重点）— 通过

`_crlf_tolerant_subn`（projection.py L52-90）：

- **归一化视图匹配**：`normalized = text.replace("\r\n", "\n")` 后 `re.finditer(pattern, normalized, flags=re.MULTILINE)`——`$` 锚在 LF 视图上正常匹配行尾（CRLF 文件中 `\r` 不再夹在内容与行尾之间）。这是对根因（匹配 0 次）的直接修复，沙箱 HEAD 引擎复证确认修复前形态为 `ValueError: projection pattern count mismatch for 'hook'`。
- **原生偏移表**：`native_of` 逐位构造（L77-82）。归纳论证：扫描在 text 侧每次前进 1（普通字符）或 2（`text.startswith("\r\n", native)` 为真，对应 normalized 侧折叠出的一个 `\n`），与 `str.replace` 从左到右非重叠替换严格同步；孤立 `\r`（不跟 `\n`）走 else 分支保留，映射不破坏。终哨兵 `native_of[len(normalized)] = len(text)` 与扫描终点一致（消耗恰为 text 全部字符）。匹配 span（含 `match.end()==len(normalized)` 边界）翻译回原生偏移后拼接 `text[last_native:...]` + `match.expand(replacement)`——非匹配区字节逐字保留。
- **纯 LF 文件逐字节等价**：无 `\r\n` 时每步 native+=1，`native_of[i]==i`，恒等映射；拼接结果 = 原生 subn 结果。FIX-366 时代 7 个既有测试（含非锚 pattern `version=[0-9.]+`、带组引用 `\g<1>` 的 fixture-plan 同构面）全绿佐证。
- **count 语义严格等价**：新代码 `len(matches) < expected` → raise，`matches[:expected]` 替换前 expected 个；旧代码 `re.subn(count=expected)` 在匹配数 ≥ expected 时替换前 expected 个、匹配数 < expected 时 `count != expected` raise。两者在全部输入域上行为一致（含 expected=0 退化态：均返回原文不报错）。
- **bump 态只按文件自身行尾改写匹配区**：`(?m)` 下 `$` 匹配不消费行尾符，`match.end()` 止于内容字符；replacement 拼接后，紧随其后的原生字节（CRLF 文件的 `\r\n`）原样保留——`test_version_bump_on_crlf_hook_keeps_native_crlf` 断言 planned == `_hook_crlf(NEW_VERSION)`（全 CRLF）实证。
- **同步态恒零写入（工作树免疫）**：in-sync 时 replacement 展开与原文相同，拼接结果与输入 `text` 逐字节相同 → planned == current → `_projection_matches` True → `write_projections` 走 written=0 快路径（L668-669）。双实证：单测 `test_in_sync_crlf_hook_plans_to_its_own_bytes`（written=0 + 盘上字节不变断言）+ 真实仓库 `release-projection --write` PASS written=0（commit-msg 工作树 w/crlf、版本行 0.98.0 in-sync，实测未被动）。

### 2. 契约保全 — 通过

- **FIX-366 F-1 守卫**：`test_crlf_transformed_content_stays_byte_faithful`（test_release_projection.py L155-178）在 32 passed 内（pytest 实测），绿。
- **byte_copy 镜像恒等**：两阶段 plan 中 byte_copy source ∈ resolved 时消费 resolved 内容（projection.py L300，FIX-366 架构未动）；`CrlfHookProjectionTests` 两测均断言 `writes["hook.mirror"].content` 与 transformed 目标逐字节相等。引擎改动点位于 pass 1 的 resolve 内部，输出仍是「目标文件自身字节的最小改写」，mirror 语义不破坏。
- **governance-init.md 链抽验**：registry（version-projections.json L119-131）确认 `canonical-bootstrap-version`（transformed_text，governance-init.md，count=3，pattern 无 `$` 锚、无捕获组）的 target 同时是 `fixture-command-governance-init`（byte_copy）的 source——与 dev 声明的链一致。该链同构于测试 pin 的 hook→hook.mirror（LF 态恒等映射 + resolved 消费）；`check-projection-sync` PASSED（27 镜像 0 issue）实证该链当前同步。归一化视图匹配对该链无破坏。

### 3. .gitattributes 面 — 通过

- **glob 实测只盖 hooks 四文件**：`git check-attr text eol` 实测 pre-commit/post-commit/prepare-commit-msg/commit-msg 四文件均 `text: set, eol: lf`（新锚生效）；对照面 AGENTS.md/CLAUDE.md 均 `unspecified`（未越界；verify_workflow.py/projection.py/test_hooks.py 的属性来自既有 `*.py` 规则，非本次新增）。glob `infra/hooks/*` 与目录实际内容（glob 实测恰 4 文件、无子目录）一致。
- **index EOL 前提**：`git ls-files --eol` 实测四文件全部 `i/lf`——注记「index 已 100% LF，无需 renormalize」的声明属实。commit-msg 工作树 `w/crlf` 与「FIX-445 CRLF 工作树仍在」一致；git 警告「CRLF will be replaced by LF the next time Git touches it」是 eol=lf 属性的自然结果，与注记预期（新 checkout LF 化、当前工作树不动）一致。
- **renormalize 禁令红线自洽**：unstaged diff 实测 commit-msg 带 745 行 FIX-445 WIP + 版本行 0.97.0→0.98.0——`git add --renormalize` 会将该工作树内容 stage 入 index，禁令注记的事实前提成立。
- **dsh AGENTS.md.template 边界披露**：`dsh-agents-bootstrap-version`（registry L111-117）确为 `$` 锚 pattern（`^> @bootstrap-version: x.y.z$`），其 target `adapters/dsh/AGENTS.md.template` 不在锚 glob 覆盖内；实测本 clone 该文件纯 LF（37 LF / 0 CRLF），风险仅在 autocrlf=true 的其他 clone，由引擎路径 B（本次 `_crlf_tolerant_subn` 对所有 transformed_text 生效）兜底——披露准确、兜底真实。

### 4. 回归测试质量 — 通过

- **red-on-buggy 独立复证**（方法=沙箱组装，见「审查方法」）：HEAD 引擎 + staged 测试 → `2 failed, 7 passed`，两红均为 `ValueError: projection pattern count mismatch for 'hook'`（pytest 标签 FAILED，异常驱动红，docstring 所称 ERROR 为 unittest 习惯措辞，语义一致）；修复后引擎单文件全量 `9 passed`。与 dev 声明（HEAD 上 2 红、修复后 9/9 绿）完全一致。
- **关键断言实读**：`test_in_sync_crlf_hook_plans_to_its_own_bytes` 断言链完整（plan 字节==原字节 → mirror 恒等 → check PASS → written=0 → 盘上字节不变）；`test_version_bump_on_crlf_hook_keeps_native_crlf` 断言 planned/盘上/mirror 三面 CRLF 保留 + 收敛后二次 write written=0。审查清单点名的边界（纯 LF 等价、count 语义、bump 原生行尾、同步零写）中，后两者被直接断言，前两者由 7 个既有绿测 + 等价性推演覆盖。
- fixture 的 pattern 取自 registry 真实家族（`(?m)^# @version: [0-9]+\.[0-9]+\.[0-9]+$`，与 4 个 hook 条目逐字一致），非缩水的替身 pattern。

### 5. 验证复核 — 全部符合预期

| 命令 | 预期 | 实测 |
|------|------|------|
| `verify_workflow.py release-projection --write` | PASS written=0 | **PASS，written=0**，sd_integrity scanned=27 unreadable=0（exit 0） |
| `verify_workflow.py check-projection-sync` | PASSED 0 issue | **PASSED**，27 mirrored files 0 issue；bootstrap sync 面 PASSED（exit 0） |
| `pytest …test_release_projection.py …test_verify_workflow.py -q -k "projection or SdIntegrity"` | 全绿 | **32 passed, 1114 deselected**（含 FIX-366 F-1 守卫） |
| `git status --short` | staged=3；FIX-445 两文件未 staged | staged=3（+169/−4）；commit-msg、test_hooks.py 未 staged ✓；**另有 AGENTS.md 1 行 unstaged**（标题去 `/ Chrys`，预存工作树修改，非 FIX-451 面且非 FIX-445 面——见 P3-2 披露） |

### 6. 越权检查 — 通过

- staged diff 仅含 3 个声明文件；`version-projections.json` 零改动（staged 与 unstaged 均无该文件条目）。
- `.governance/` 零触碰（git status 无任何 `.governance` 条目）。
- FIX-445 保全文件（hooks/commit-msg、tests/test_hooks.py）staged 零触碰；其 unstaged 修改为 FIX-445 WIP 本体（commit-msg +745 行引擎与版本行、test_hooks.py +857 行），diff 内容审读确认与 FIX-451 的引擎/属性/测试面无交集。

---

## 5 维度结论

| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | 通过 | 偏移表归纳论证（清单 1）+ 沙箱红测 + 真实仓库 written=0 双实证；边界（纯 LF 恒等、count 等价、孤立 `\r`、`$` 不消费行尾、终哨兵）逐项推演无缺口 |
| 安全性 | 通过 | 无新输入面（pattern/replacement 仍来自受治理 registry）；`_safe_repo_path` 路径防护未动；无敏感数据、无注入面变化 |
| 可维护性 | 通过 | 函数单一职责、docstring 完备（动机/机制/契约后果三段）；调用点注释指向实现；P2-1 为未来 registry 演进的边界注记 |
| 性能 | 通过 | `native_of` O(n) 时间/空间 + 每位 O(1) 的 `startswith` 探测；transformed_text 目标均为 KB 级文件（最大 governance-init.md），开销可忽略；无循环内 I/O |
| 测试覆盖 | 通过 | in-sync 与 bump 两核心路径 + 红测复证 + 真实仓库面实证；组引用 expand 边界未 pin（并入 P2-1，非当前 registry 形态） |

## AI 代码专项 5 项检查

| 检查项 | 结论 |
|--------|------|
| mock 残留 | 无——staged delta 不含 mock/patch（既有 WriteThenProbeTests 的 patch 为历史代码） |
| 硬编码返回值 | 无——所有输出由输入推导 |
| 幻觉 API 调用 | 无——`re.finditer`/`match.expand`/`str.startswith(s, pos)`/`str.replace` 均为真实标准库行为且用法正确（`startswith` 带起点参数不越界） |
| 未实现 TODO | 无 |
| 过度实现 | 无——改动严格限于 transformed_text 路径的 subn 替换点 + 两测 + 属性锚，无越界功能 |

## 发现列表

### P2-1（建议）：组引用 replacement 在归一化视图上展开——跨行捕获组的潜在 EOL 偏差未设防

- **位置**: projection.py L87（`match.expand(replacement)`）
- **事实**: 组内容从 normalized 视图展开：若未来 registry 新增「捕获组内容含行尾」的 pattern（如跨行捕获 `\r\n`），展开结果会以 LF 形态拼回 CRLF 原生字节，与旧引擎（原生文本上 expand）行为相异。当前 registry 8 个 transformed_text 中唯一组引用 `fixture-plan`（`\g<1>` → `**工作流版本:\s*` 行内前缀）不含行尾，无实际影响；测试未 pin 此边界。
- **建议**: 在 `_crlf_tolerant_subn` docstring 或 registry 变更纪律中记一条约束（组内容不得跨行尾，或 expand 后需 EOL 回写），即可关闭。不阻塞本轮。

### P3-1（讨论）：`.gitattributes` glob `infra/hooks/*` 不覆盖未来子目录

- **事实**: gitattributes 的 `*` 不跨 `/`；当前目录恰 4 文件无子目录，注记「four infra hooks files」准确。若未来 hooks/ 下出现子目录文件（如 lib/x.sh），不会被此锚覆盖（引擎路径 B 仍兜底匹配，但 CRLF 源头治理会有缺口）。
- **处置**: 知识记录，无需改动。

### P3-2（信息披露）：工作树存在任务书未提及的第三处 unstaged 修改

- **事实**: `git status` 实测 unstaged 3 文件：commit-msg、test_hooks.py（FIX-445 WIP，与任务书「FIX-445 两文件未 staged」一致）+ **AGENTS.md 1 行标题修改**（`Codex / Chrys 项目指引` → `Codex 项目指引`，预存、与 FIX-451 无关）。
- **处置**: 向 Coordinator 披露该工作树事实，供其决定 AGENTS.md 的归属处置；不影响本审查结论。

## 硬门槛裁决

| 门槛 | 阈值 | 实测 |
|------|------|------|
| P0 阻塞数 | = 0 | **0** ✓ |
| 5 维度全覆盖 | 100% | 5/5 逐一有结论 ✓ |
| 每条发现标注级别 | 100% | 3 条发现均带 P2/P3 标签 ✓ |
| 设计一致性检查 | 已完成 | 与 FIX-366 两阶段 resolve 架构一致（改动点在 pass 1 内部，resolved 语义不变）；与 RISK-068 根因对症（CRLF→匹配 0→BLOCKED 双路径根治：属性锚断源头 + 引擎容差兜底）✓ |
| AI 代码专项 5 项 | 全部完成 | 5/5 有结论 ✓ |

## 结论重申

**APPROVED_WITH_NOTES** · unresolved_blockers=0 · P0=0 / P1=0 / P2=1 / P3=2

APPROVED 只表示硬门槛通过，不替代测试或发布审查。P2-1 建议在后续 registry 演进时闭环；P3-2 的工作树事实移交 Coordinator 知悉。
