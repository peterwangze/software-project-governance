# Code Review 报告 — FIX-440（R0 初审）

## 报告头

- **round**: 0（FIX-440 票内初审，无前轮；承接依据 = `docs/reviews/review-FIX-439-CODE-R0.md` F-1/F-2/F-3/F-6 行）
- **审查对象**: 工作树 staged 变更（未 commit；基线 HEAD `f884829`），以仓库当前文件态实读为审查面
- **审查面声明**: 本 Reviewer 无命令通道（Bash 禁止），**全部结论基于文件态逐行实读 + 逻辑推演**；开发者声称的全部运行结果不可复跑，逐项列入「未验证项清单」，不作为通过依据
- **实读文件**: `adapters/dsh/launch.py`（write_bootstrap 全函数 L1681-1796 + `_read_text`/`_read_text_with_newline_mode` 读侧面）、`skills/software-project-governance/infra/sync_entry_projection.py`（全文 739 行）、`skills/software-project-governance/infra/tests/test_dsh_adapter.py`（L1-80 helpers + L2040-2357 两个测试类全文）、`skills/software-project-governance/infra/tests/test_verify_workflow.py`（L25002-25120 全类 + 全文件 `governance-store-ops` 残留 grep）、`skills/software-project-governance/infra/governance_store.py`（上下文核验：L221-226 正则 / L591-592 `_ledger_path` / L1021-1150 build+content 校验 / L1157-1301 append 时序）、`adapters/dsh/AGENTS.md.template`（全文 37 行）

## 逐文件实读核验

### 1. `adapters/dsh/launch.py` — `write_bootstrap()`

| 声称落点 | 实读结果 |
|---|---|
| ① F-1 读侧 `newline=""` | ✅ L1715-1717 `target.open("r", encoding="utf-8", errors="replace", newline="")`——仅 newline 维度移动，`errors="replace"` 原样保留（注释 L1709-1714 明示维度隔离）。**组合语义核验**：`errors` 只作用于解码失败字节（→ U+FFFD），newline 翻译是独立的 TextIOWrapper 层；`\r`(0x0D)/`\n`(0x0A) 是合法 ASCII，永不进入 replace 路径——**replace 面不吞 `\r`，无交互**。读出的 `existing` 保留原始 `\r\n`，经 splice 后 `write_text(new_text, newline="")`（L1787）原字节落盘——F-1 缺陷链（读归一 → 写 LF → 全文翻转）在读侧断开 |
| ② F-3 guard 前置于 dry-run | ✅ 结构实读：L1753 `replace_bootstrap_section` → L1762 `bootstrap_h2_singleton_violations` → 违规时 L1765-1780 **dry-run 与实跑分岔仅在措辞**（dry-run 打印「the real run would be REFUSED (exit 1) with the original … left unchanged」），**共同 `return 1`，且位于两处 `write_text`（L1787/L1794）之前——违规 dry-run 零写入**；干净路径 dry-run（L1781-1786）行为与措辞不变（"planned write" + exit 0）。与 `apply_entry_projection` 的 guard-before-dry_run 口径（sync 侧 L549-566）对齐，分叉消除 |
| `--force`+无段沿旧措辞 | ✅ L1788-1794 else 分支未动（R0 F-5 范围外语义保持） |

**dry-run exit 1 对既有调用方影响推演**：无段且非 force 的拒绝对 dry-run **本来就** return 1（L1729-1735 早于一切 dry-run 分岔，FIX-439 前即如此）——「dry-run 预演拒绝并以 1 退出」是既有语义，本次只是把 guard 拒绝并入同一契约；不存在把 dry-run rc==1 当成功的老调用方能安全存活的世界，Scenario C A 步（先 dry-run 后实跑）感知分叉反而闭合。

### 2. `skills/software-project-governance/infra/sync_entry_projection.py`

| 声称落点 | 实读结果 |
|---|---|
| F-1 `_read_text` 显式 `newline=""` | ✅ L426-435，docstring 论证与 launch 侧同构（`Path.read_text` 3.13 前无 newline 参）；strict UTF-8 解码语义与改前 `read_text(encoding="utf-8")` 一致（非维度移动） |
| `_match_newlines` 复活 | ✅ L247-264。**复活论证逐支柱核验**：(a) 分隔符 `nl`（L313）与 append 空行检测（L319 `base.endswith(nl*2)`）确实已承诺全文 CRLF 启发式——只移除段体适配半边会铸造「LF 段体 + CRLF 分隔符」段界缝隙并扰动 append 路径，论证成立；(b) **LF 模板 + CRLF 宿主 ⇒ 段体 EOL = CRLF**：两处模板读入（launch `_read_text` L231 / sync `load_canonical_templates` L190）均走 universal newlines ⇒ section 恒为纯 LF ⇒ `"\r\n" not in section` 恒真 ⇒ 宿主含任一 CRLF 即全文转换，`replace_bootstrap_section` L311-312 拼接的是模板字节经 EOL 适配后的文本（非原样字节）；(c) **混合 EOL 终态 + 二次 splice 幂等**：启发式为纯函数（全文任一 `\r\n` ⇒ CRLF 段体+分隔符），终态确定 ⇒ 二次 splice 复现同字节；(d) **下游 `\r` 容忍逐面实读**：`_norm`（L664）在 `_normalized_content`（L496-503）入口归一——sticky（L483-488）、classify/report（L616-640）全部经 `_section_content`/`_normalized_content` 比较，`validate_thin_pointer` 收到的是归一后内容（byte 预算不受 CRLF 膨胀误伤）；singleton guard 行锚 `(?m)^…[ \t]*\r?$`（L341）显式容 `\r`；span 三 regex（`_SECTION_START_RE`/`_H2_LINE_RE`/`_H1_LINE_RE` 的 `[^\n]*\n` 天然吞 `\r`，`_HR_LINE_RE` 显式 `\r?`，L222-223/L44-45）+ `_h2_titles` 的 `strip()` 剥尾 `\r`（L227）——**下游面 EOL 不敏感声称全部文件态证实** |

**LF 世界不变性（文件态推演）**：纯 LF 宿主下 raw 读 == 归一读（恒等），`_match_newlines` 条件假（no-op），`nl="\n"`——与修复前行为逐字节同构。`check-entry-bootstrap-sync`（经 `build_sync_report`）在 CRLF checkout 世界 verdict 不变（regex 容忍 + `_norm` 归一双重保障）。

### 3. `tests/test_dsh_adapter.py` — `BootstrapCrlfEolFIX440Tests`（4 条）+ FIX-439 类 2 条 dry-run

- ✅ **断言强度核验**（任务提出的「无裸 LF 断言是否会误伤合法 LF 段体」）：`assertNotIn(b"\n", after.replace(b"\r\n", b""))`（L2297/L2349）在 CRLF 路径上**不可能误伤**——段体恒被 `_match_newlines` 转 CRLF（模板恒纯 LF + 宿主含 CRLF ⇒ 必转换），若 splice 留下 LF 段体该断言必红，而这正是缺陷本身——断言方向正确、与夹具对合闭合。`after[after.index(b"---"):]==before[before.index(b"---"):]` 的锚点有效性经模板实读证实（37 行全文无 `---` 子串、无 `|---|` 表格、六 H2、单一尾换行）——首锚必为宿主分隔符；`startswith(rendered.replace("\n","\r\n").encode())`（L2300-2301）钉死段体 = 模板内容的 CRLF 形态。
- ✅ **夹具设计**：`_host_project(td, section_crlf, tail_crlf)` 参数化两独立 EOL 面（Windows=双 True / 混合=LF+CRLF），`write_text(..., newline="")` 落盘保真；旧版本号由模板 header 派生（L2258-2261，FIX-352/353 纪律保持）；全部写入限于 `_sandbox_td()` 系统临时目录（L56-67），零真实宿主写入。
- ✅ dry-run 双向钉住：干净路径 rc==0 + "planned write" + 字节不变（L2182-2196）；违规路径 rc==1 + `assertNotIn("planned write")` + 字节不变 + stderr 锚点（L2198-2218）——F-3 的两侧不变量都有守。
- ✅ sync 侧第 4 用例：append 路径（无段 CRLF 宿主）前缀字节保留 + 全 CRLF + 二次 `unchanged`（L2331-2353）——F-1 第二读位点独立覆盖。
- ✅ 测试数对合：FIX-439 类 4 + 本票 +2（dry-run）= 6；CRLF 类 4 → 本票共 +6，与「dsh 族 59→65」声称自洽。

### 4. `tests/test_verify_workflow.py` — F-2 +1 / F-6×4

- ✅ **F-2 穿透性三层推演**（任务要求实读核验）：输入 `description="目标对齐：太短"`——① L1188 入口镜像 `_validate_user_impact_passage`：无 `用户影响[:：]` passage → 直接 return（L1104-1105），**no-op 证实**；② `_build_evidence_row`（L1021-1039）：仅 `_cells_no_newline` + `_validate_row_shape` 纯 shape，内容不查——**穿透证实**；③ L1284 `_evidence_row_validator` → `_validate_evidence_content`：`_GOAL_ALIGNMENT_RE` 命中、`len("太短")=2 < 30` → refuse（L1055-1060）——**唯一拦截点证实**。红态结构推演：L1284 禁用 ⇒ build 通过 ⇒ L1286 写入 ⇒ L1287 post-write 同 validator 拒绝 ⇒ 「schema_violation + 行已持久化」= incident §5 缺陷形态必红。运行时红绿实录不可复跑，列入未验证项。
- ✅ **F-6 完整性**：4 处零台账断言（L25052/25074/25093/25116）全部改 `gs._ledger_path(gov).exists()`；`_ledger_path` 实存（governance_store L591-592，与写入侧同一派生）；**全文件 grep `governance-store-ops` 零命中**——无任何残留硬编码（超出声称的 4 处口径，全文件干净）。断言语义真实：L1284 拒绝在 `_atomic_write_bytes`/`_ledger_transaction` 之前 → 台账必不存在，`exists()` 为真实检查。

## 5 维度逐项结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | **通过**（1 项 P3 docstring 精度） | F-1 读侧两处 `newline=""` 落点实存且语义正确（errors/newline 正交性核验）；`_match_newlines` 复活论证四支柱（启发式一致性/段体 EOL 归宿/幂等闭合/下游容忍）逐项文件态证实；F-3 guard 前置 + 双路 return 1 零写入；LF 世界恒等推演成立；F-2 用例三层穿透 + L1284 唯一拦截点推演闭合 |
| 安全性 | **通过** | 无新增攻击面；用户数据保护**增强**（CRLF 宿主非段字节不再被改写——F-1 正是数据保护缺陷的修复）；`re.escape` 既有；测试全隔离于系统临时目录，零真实宿主/真实 DSH_HOME 写入；拒绝路径零写零台账既有语义未动 |
| 可维护性 | **通过**（2 项 P3） | 注释全部锚定 FIX-440/review-FIX-439-R0 编号可追溯；维度隔离（仅 newline 移动）在注释中明示；夹具版本派生纪律保持；`_match_newlines` docstring 承载复活论证（优于无注释死代码）。小疵：docstring 一句措辞过宽（N-1）、测试类跨类借用 helper（N-3） |
| 性能 | **通过** | `_match_newlines` 复活引入一次 O(段长) `replace`（原为死分支，代价可忽略）；无新循环/IO；读侧 open 参数变化零开销 |
| 测试覆盖 | **通过** | 4+2 用例覆盖 F-1 核心路径（首写字节保留/幂等/混合/append 面）+ F-3 双向（干净/拒绝）；断言字节级（`read_bytes`/`b"\r\n"` 显式/无裸 LF）；F-2 补齐 R0 指出的独立红绿缺口；F-6 消除断言与实现解耦。CRLF+`--force` 整文件覆盖世界无用例——属 R0 F-5 范围外语义，不构成本票缺口 |

## 发现列表

| # | 文件:行号 | 级别 | 问题 | 依据 | 修复建议 |
|---|------|------|------|------|---------|
| N-1 | `skills/software-project-governance/infra/sync_entry_projection.py:255-256` | **P3** | `_match_newlines` docstring「a mixed file converges to the tail's form」是对启发式的方向性过宽概括：实际规则是「全文任一 `\r\n` ⇒ 段体+分隔符 CRLF」——CRLF 段体 + LF 尾部的混合世界（外部可构造）中段体收敛到 CRLF 而非尾部 LF 形态。行为本身确定/幂等/宿主字节保留（无功能缺陷），纯文档精度 | 启发式条件 `"\r\n" in target_text`（L262）与该句的推演差 | docstring 该句改为「a mixed file converges the section to CRLF whenever any `\r\n` survives anywhere in the host」口径 |
| N-2 | `adapters/dsh/launch.py:1715-1716` | **P3** | `errors="replace"` 字节保留缺口：非 UTF-8 宿主 AGENTS.md 的坏字节读为 U+FFFD，splice 落盘即固化 mojibake——与 F-1 同族（读写不对称破坏字节保留），但为**既有维度、本票设计性范围外**（注释明示仅 newline 移动；sync 侧 `_read_text` 为 strict 拒绝，两读侧语义本就分叉） | errors 语义 + splice 写路径推演 | 独立小票评估：launch 读侧对齐 strict 拒绝（fail-closed）或检测到替换时拒绝写回；不建议本票顺带改 |
| N-3 | `skills/software-project-governance/infra/tests/test_dsh_adapter.py:2247` | **P3** | FIX440 测试类跨类引用 `BootstrapSpliceFIX439Tests._rendered_template(cls.launch)`——测试组织耦合（FIX-439 类重构/改名会波及 FIX440 类），模块级 helper 更解耦 | 类依赖实读 | 后续将 `_rendered_template` 提为模块级函数（两类共用），非阻塞 |

**R0 遗留项状态对账**：F-4（guard 窄缝隙）/F-5（`--force` 丢弃面措辞）不在本票承接范围（DEC-323(3) 裁定承载 F-1+F-2/F-3/F-6），文件态确认未回归、未被本票改动；维持 R0 遗留建议，不计入本票发现。

## AI 代码专项 5 项结论

1. **mock 残留**：无——新增 6+1 用例零 mock，直调真实模块（`launch.write_bootstrap`/`sync_entry_projection.apply_entry_projection`/`gs.evidence_append`）+ 真实临时目录 ✅
2. **硬编码返回值**：无——全部断言对真实计算产物（`read_bytes`/result payload）✅
3. **幻觉 API**：无——`write_bootstrap(dry_run=)`（签名 L1681 实存）、`_ledger_path`（L591）、`bootstrap_boundary_titles`/`bootstrap_h2_singleton_violations`/`apply_entry_projection` 逐一实存；`BootstrapSpliceFIX439Tests._rendered_template` 为 @staticmethod（L2066）可类访问 ✅
4. **未实现 TODO**：无——修改面 grep 无 TODO/FIXME 残留 ✅
5. **过度实现**：无——6 测试用例 ↔ 验收标准①③⑤逐条对映，F-2/F-6 各 1:1；`_match_newlines` 选择复活而非重写更重的 EOL 适配器，恰是最小充分解 ✅

## 蓝军挑战（对抗性推演）

- **「全文无裸 LF」断言误伤风险**：CRLF 路径段体必被转换（模板恒 LF + 宿主持 CRLF ⇒ `_match_newlines` 必触发），合法 LF 段体在该断言世界不存在——若实现退化留 LF，断言必红且应当红 ✅
- **`after.index(b"---")` 锚点漂移**：模板 37 行实读无任何 `---` 字节（含 `|---|`），新旧段体均不含 ⇒ before/after 首锚同为宿主分隔符 ✅（splice 在 `---` 前插入的 `nl` 分隔位于比较区之外，不影响断言）
- **混合 EOL 反向世界**（CRLF 段 + LF 尾）：启发式取「任一 CRLF」⇒ 段体保持 CRLF、尾部 LF 原样——确定且幂等，宿主字节保留不破 ✅（即 N-1 措辞问题的实体）
- **二次 splice 幂等闭合**：启发式纯函数 + 段体重建确定 + `after = nl + after_body` 确定性 ⇒ `new_text` 复现同字节；launch 侧无条件重写同字节、sync 侧判 unchanged——两形态都被字节级测试钉住 ✅
- **`errors="replace"` 吞 `\r` 质疑**：解码错误与 newline 翻译是 TextIOWrapper 两个正交维度，`\r\n` 恒合法解码永不入 replace 路径 ✅（任务点名疑问，核验无交互）
- **CRLF checkout 自举世界**（本仓 CLAUDE.md/AGENTS.md 为 CRLF）：`check-entry-bootstrap-sync` 在 raw 读下经 regex `\r` 容忍 + `_norm` 归一，verdict 与旧归一读一致，零回归 ✅
- **lone-`\r` 退化文件**（pre-OSX Mac 形态）：raw 读不再归一 `\r`→`\n`，span 可能 None → append 路径，不崩溃不丢数据，fail-safe 方向；git checkout 不可产生该形态，dismissed ✅
- **F-2 输入提前被拦风险**：三层逐一实读——镜像无 passage 即 no-op（L1104-1105）、build 纯 shape（L1035-1038）、L1284 唯一内容防线——「仅该层可拦」声称文件态证实 ✅
- **dry-run 调用方破坏风险**：无段拒绝的 dry-run rc==1 为既有语义（L1729 先于一切分岔），guard 拒绝并入同一契约而非新语义 ✅

## 硬门槛裁决表

| 门槛项 | 阈值 | 裁决 |
|---|------|------|
| P0 阻塞问题数 | = 0 | ✅ **0** |
| 5 维度全覆盖 | = 100% | ✅ 逐项有结论（上表） |
| 每条发现标注级别 | = 100% | ✅ N-1~N-3 全部标注（P3×3；P0/P1/P2 = 0） |
| 设计一致性检查 | 已完成 | ✅ R0 F-1/F-2/F-3/F-6 修复建议逐条落地对合；DEC-323 行为契约（首写段外字节保留/二次写字节不变/LF 世界不变/dry-run 与 sync 侧 guard 口径一致）零回归；`_match_newlines` 复活论证四支柱核验成立；F-4/F-5 范围外未回归 |
| AI 代码专项 5 项 | 全部完成 | ✅ 逐项有结论 |

## 未验证项清单（无命令通道，如实披露——不作为通过依据）

1. 开发者全部运行声称：verify 主命令 PASS、check-cross-references/check-manifest-consistency/check-entry-bootstrap-sync PASS、dsh 族 59→65、`test_verify_workflow` Ran 1061 failures=2（pristine stash 对照同 2 预存）、FIX-439 七用例全绿、LF 世界逐字节不变的运行时实录、F-1/F-3 红绿对照实录、F-2 L1284 临时禁用实证必红 + git diff 还原机证——**均不可复跑**（F-2 红绿已用三层穿透 + 时序结构推演替代验证；LF 不变性已用恒等推演替代验证）
2. **数字一致性疑问**：R0 报告基线为「1059 passed + 2 failed = Ran 1061」，本票净增 1 条用例（无删除）⇒ 预期 Ran 1062；本票声称「Ran 1061」与 R0 基线差 1——两数字均为开发者声称、均不可复跑，无法裁决孰误；不影响文件态结论，提请 Coordinator 在 evidence 留痕时核对实际 unittest 输出
3. 工作树 staged diff 边界（对 HEAD `f884829` 的逐行 diff）——无 git 通道；以当前文件态为审查面（派发声明口径），修改文件清单以派发为准；`governance_store.py` 未列入修改面，本票所读 L1284/L1188 等结构按 FIX-439 既有面处理

## 最终结论

# APPROVED_WITH_NOTES（unresolved_blockers = 0）

**理由**：四个修改文件全部逐行实读——FIX-440 的三个 rider 与主修复在文件态全部成立：①F-1 读侧双点 `newline=""` 落点正确、errors/newline 正交无交互，`_match_newlines` 复活论证（启发式一致性、LF 模板+CRLF 宿主 ⇒ 段体 CRLF、混合世界幂等、下游 `_norm`/行锚/regex 容忍）四支柱逐项证实，CRLF 宿主段外字节保留由字节级断言钉住且「无裸 LF」断言无误伤路径；②F-3 guard 前置后违规 dry-run 预演拒绝 exit 1 零写入、干净路径不变，与 sync 侧口径对齐且不破坏既有 dry-run 拒绝语义；③F-2 用例经三层校验实读穿透推演为「仅 L1284 可拦」的独立红绿（运行时实录不可复跑已披露）；④F-6 四处断言经 `_ledger_path` 派生且全文件零硬编码残留。P0=0、P1=0、P2=0；P3×3（docstring 措辞精度/既有 errors 维度范围外记录/测试 helper 组织）均不阻塞。验收标准①~⑤中运行时面（全套件零退化）依赖开发者声称，已如实标注，通过依据独立于该声称。

**遗留建议**（不阻塞）：N-1（docstring 一句口径修正，下次触碰该文件时顺带）> N-2（独立小票评估读侧 strict 化）> N-3（helper 提模块级）；R0 F-4/F-5 维持原遗留轨道。

---

## Coordinator 后置核验注记（2026-10-06，审查报告落盘后追加）

未验证项 2（数字一致性疑问）已由 Coordinator 实跑定谳（独立复跑，非转述开发者声称）：

- `python -m unittest test_verify_workflow`（infra/tests 下）→ **`Ran 1061 tests in 476.980s` / `FAILED (failures=2)`**（exit 1）——与本票开发者声称一致；failures=2 为既有披露集（ContractTierBudget / Feat039InjectionBudget-strict 预存族）。数字疑问根源 = FIX-439 时点返回中「1059 passed」为 passed/total 混写口径（该时点实为 Ran 1060/1058 passed），本票 +1 用例后 Ran 1061 自洽，**非缺陷**。
- `python -m unittest test_dsh_adapter` → **`Ran 65 tests in 14.990s` / `OK`**（exit 0）——与「dsh 族 59→65」声称一致。

以上实跑输出为本报告的 Coordinator 侧闭合证据，随 EVD-1338 机录。
