结论：**NEEDS_CHANGE** ｜ round=0 ｜ unresolved_blockers=1（P1-1）｜ 机录 round 建议 = `REVIEW-FIX-314-R1`

# Review — REVIEW-FIX-314-CODE-R0（review_record 唯一键扩展 `(task, round)` → `(task, round, reviewer)`）

- **基线**：HEAD `7bb102b`，工作树未提交改动 2 文件：`infra/review_record.py`（+89/−22）、`infra/tests/test_verify_workflow.py`（+366，`ReviewRecordReviewerKeyTests` 13 用例）；`verify_workflow.py`/`hooks/commit-msg`/`checks/review_domain.py` 经 `git diff HEAD --stat` 独立确认**零改动**
- **审查者**：Code Reviewer（独立复核，不转抄 Developer 声明）
- **方法**：逐行 diff 审查 + 定向套件/全量/archguard 独立复现（仓库根运行）+ HEAD 基线红身份对照（stash/pop）+ CLI 反相（%TEMP% 临时 project root，全程未触碰真实 `.governance/` 写面）+ hook 函数真提取 git-bash 实测 + Check 30c 双半面活体探针

---

## 一、硬门槛执行记录（独立复现证据）

| 门槛项 | 结果 | 证据 |
|---|---|---|
| 定向新类 | **13/13 OK** | `python -m unittest discover -s skills/software-project-governance/infra/tests -p test_verify_workflow.py -k ReviewRecordReviewerKeyTests -v` → `Ran 13 tests … OK`（含 2 个 CLI 子进程用例与 2 个 hook 真执行用例，非 skip） |
| test_review_record | **21/21 OK** | 同法 `-p test_review_record.py` → `Ran 21 tests … OK` |
| closure-legacy | **36/36 OK** | `-p test_review_closure_legacy.py` → `Ran 36 tests … OK` |
| test_verify_workflow 全量 | **838 total，3 红身份不变** | `Ran 838 tests in 241.325s — FAILED (failures=1, errors=2)`。3 红 = `FIX300DualCaliberAgreementTests`×2（1 FAIL+1 ERROR）+ `LoopRuntimeClaimAdapterTests.test_claim_command_emits_complete_pass_report`（ERROR）；`git stash push` 两文件后于 HEAD 基线复跑同 3 用例 → **同型失败逐一重合**，`stash pop` 干净还原 → 非本次引入 |
| archguard-ratchet | **PASS** | R1 主文件 24453 ≤ anchor 24453（零增行）；R5 cli keys 84/84 frozen；R7 regen deterministic；0 violations |
| CLI 反相（%TEMP%） | **15/17 checks** | 双连发双记录互不覆盖 ✓ / 三键全同 exit 2 ✓ / 大小写异写守卫（不覆写）✓ / 旧格式字节级不动（SHA256 前后等同，owner 有/无两态）✓ / namespaced NEEDS_CHANGE 带 `next_round` 字段 ✓ / slug 不可化 fail-closed ✓ / 首位审查方 canonical 落位 ✓ / **2 FAIL 见 P1-1 与 P3-1** |
| hook 兼容独立实测 | **五连吻合** | 从 hook 源码真提取 `has_approved_review_evidence`（复用既有 `_extract_function`），git-bash 执行：扩展 ID+APPROVED=**HIT**、+APPROVED_WITH_NOTES(unresolved_blockers=0)=**HIT**、+NEEDS_CHANGE=**MISS**、+BLOCKED=**MISS**、canonical ID+APPROVED=**HIT** |
| 30c 双半面活体探针 | **假 WARN 实证** | canonical(APPROVED)+namespaced(NEEDS_CHANGE) fixture → `check_review_machine_provenance` 判 WARN：`V8 … file review-FIX-314-R0.md lacks the field`，而 namespaced 文件**自身携带** `next_round: REVIEW-FIX-314-R1`（探针 assert True）；stats `files_unmatched=1, files_judged=1` → 见 P2-1 |

## 二、Developer 声明逐项独立复核

| # | 声明 | 裁决 | 独立证据 |
|---|---|---|---|
| 1 | 键面设计 canonical-first + FIX-289⑤ 三键守卫 + fail-closed | **证实** | 探针实证首位审查方落 canonical（probe 9）、次位落 `-<slug>`（probe 1b）；owner 探针读 `- reviewer:` 字段——该字段行 HEAD L230 即存在，CLI 旧机录 round-trip 匹配成立；三键全同 exit 2（probe 2）；force 备份名 `review-FIX-314-R0-<slug>.pre-<ts>.md` + `force_overwrite` 标记 + canonical 不动（库内实测）；slug 不可化 error dict 且零写入（probe 8）；无 reviewer 写入 = 旧键面原样（`if reviewer:` 门控，probe/`test_reviewerless_write_still_guarded_by_canonical_file`） |
| 2 | TDD：GREEN 13/13（CLI 端到端两连发/守卫/旧格式字节等同/force 备份名） | **证实** | 13 用例独立复现全绿；CLI 端到端与守卫行为经我的独立 %TEMP% 探针吻合。RED 阶段系历史状态不可复验，采信声明——GREEN 断言面已覆盖声明所列四场景 |
| 3 | 四同步面 | **①③④证实；②部分证实（发现 P2-1）** | ① hook：静态推导 + git-bash 实测双确认（见上表）。② Check 30 **行通道** merge「最 terminal 胜」确为既有语义：`checks/review_domain.py` 零改动，duplicate-round merge（L1962-1990）与 REL-070 同轮碰撞先例均先于本改动（HEAD 对照）→ Developer 定位正确；但**30c 文件通道是声明未覆盖的第四同步面**（`_REVIEW_FILE_NAME_RE` L2632 / `_lookup_review_file` L2728 / `_collect_live_review_sequences` L2571 三处严格名形都不认 `-<slug>` 后缀）→ P2-1。③ 契约矩阵：`test_contract_matrix.py` 无任何 review-record 断言（grep 零命中）+ archguard R5 84/84 frozen → 无需同步成立。④ 既有当日记录读取面：canonical 行形态逐字节不变（`_evidence_row` 仅新增可选尾参）、旧格式文件字节级不动实测、closure-legacy 36/36 |
| 4 | 套件 838/3 红身份不变 + 21/21 + 36/36 + archguard PASS 24453 | **证实** | 见硬门槛表；3 红身份经 stash 后 HEAD 基线复跑逐一实证同型 |

## 三、发现列表（P0=0 ｜ P1=1 ｜ P2=2 ｜ P3=5）

### P1-1（阻塞）：canonical 记录非 UTF-8 字节 → `UnicodeDecodeError` 逃逸，违反「Never raises」与 CLI exit-2 契约
- **位置**：`infra/review_record.py` L120（`_read_record_reviewer` 的 `read_text(encoding="utf-8")`）+ L434（调用方仅 `except OSError`）；同型缺口 L466-467（force 读备份，HEAD 既有）
- **事实**：`UnicodeDecodeError` 是 `ValueError` 子类，**不是** `OSError`。`cmd_review_record`（verify_workflow.py L22102-22119）对 `write_review_record` **无任何异常捕获**。**实证**（%TEMP% 探针 7b）：GBK 字节 canonical 记录 + 带 reviewer 写入 → `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb1 …` traceback + **exit 1**（契约应为 error dict + exit 2）；零写入（fail-closed 的「不静默写」半面成立），但：
  1. 违反模块自身 API 契约 L387「Never raises」；
  2. 违反 CLI 契约（cmd_review_record docstring「exits 2 on a fail-closed input error」）——消费方 Coordinator agent 收到的是裸 traceback 而非结构化错误；
  3. **新暴露面**：owner 探针在「canonical 存在 + 带 reviewer 写入」的**常态路径**上运行（force 才触发的旧缺口被复制到热路径）；且探针先于 force 分支——GBK canonical 连 force 自救都不可达，该 task+round 对所有审查方写入瘫痪直至手工修复文件；
  4. 触发类现实性：本仓 AUDIT-147 D6 / AUDIT-148 §4.3 两度审计的 Windows GBK/ANSI 乱码族正是治理文件现实风险源；FIX-260 之前的手写 review 记录（ gradual WARN 名单内）是天然候选。
- **修复建议**：两处读点改 `except (OSError, UnicodeDecodeError)`（或 ValueError）返回既有 error dict 形态；补 GBK fixture 回归用例（记录读取面失败 → error dict + exit 2 + 零写入）。
- **定级理由**：任务审查重点明列「canonical 读失败 fail-closed」为验收面；代码注释自称「the caller fails closed」而实现只覆盖 OSError 半面——声明的 fail-closed 处理不完整 + 双重文档契约违反 + 常态热路径暴露 = 边界条件未处理（P1）。

### P2-1（非阻塞，必须注册 follow-up）：30c 文件通道对 namespaced 记录三点盲区 + V8 系统 性假 WARN
- **位置**：`checks/review_domain.py` L2632（`_REVIEW_FILE_NAME_RE` 严格名形）、L2728-2745（`_lookup_review_file` 仅 canonical 候选）、L2571（序列构建文件扫描同名形）——**本 task 范围外文件，零改动决定本身正确**（行通道与 V1~V6 全部经行 ID canonical 前缀工作，实证无回归）
- **实证后果**（30c 探针）：
  a. **V8 假 WARN**：第二半面 NEEDS_CHANGE 行 → `_next_round_discharged` 未命中 → `_lookup_review_file` 借查 canonical **兄弟文件**（APPROVED 半面，无该字段）→ 报「file review-FIX-314-R0.md lacks the field」——而 namespaced 文件**自身带** `next_round` 字段。即每个合规的第二半面 NEEDS_CHANGE 记录在复审（R+1）落地前必然产生一条假「复审必达义务不可机读」WARN——恰是 Coordinator 需要信号的窗口期，且属 FIX-291 专门治理过的「新记录形态 → WARN 噪音增长」病复发；
  b. namespaced 文件永不进入文件级 V7/V8 判定（`files_unmatched` 计数吸收，实证=1）：文件级 provenance 断言对新形态半面记录失明（行通道的机器行 marker 仍兜底 V7 行级）；
  c. 反向不对称：第一半面 NEEDS_CHANGE + 第二半面 APPROVED 时 V8 无假 WARN；双 NEEDS_CHANGE 时第二半面**借**第一半面字段意外通过（错误归因的假阴性）。
- **裁定**：测试 docstring（test L18801-18803）已记载「namespaced FILES intentionally outside the 30c file-scan name shape」——排除本身是有意设计且已披露；**未披露的是 a 的假 WARN 系统性后果**。因 30c 现为 WARN-only（升级路径已注册未激活）、无数据/闸门风险 → P2 非阻塞。**但 WARN→FAIL 升级一旦激活，本项即转阻塞**——修复（三处名形/查找接受从扩展行 ID 派生的 `-(slug)` 后缀候选）必须在升级激活前落地，建议以独立 FIX 入池并与 Developer 遗留观察 1（merge 口径 DEC）同批收口。

### P2-2（非阻塞）：Check 30 merge 口径 = 既有语义，非本改动回归——同意 Developer「遗留观察/DEC 候选」定位
- 同轮双半面一 APPROVED 一 NEEDS_CHANGE → 任务级轮次视图显示最 terminal（APPROVED）——HEAD 对照实证该 merge 语义先于 FIX-314 存在（duplicate-round merge 旧代码 + REL-070 真实碰撞先例 + review_domain.py 零改动）。半面级 NEEDS_CHANGE 义务仍由 loop wiring（CODE→G6/RELEASE→G9）与 V8 行通道承接，非 Check 30 职责。**不应升 P 级**。建议后续 DEC 一并收口：commit-msg gate 的任务级 OR 粒度（一半 APPROVED 即满足过闸，兄弟半 NEEDS_CHANGE 不阻 commit）——同为既有粒度，本改动使该场景从「不可达」变「可达」，应在 DEC 中显式接受或加闸。

### P3（观察，均不阻塞）
- **P3-1**：CLI `review-record` **无 `--force` 旗标**（L24232 的 `--force` 属 task-priority 子命令；实证 argparse usage 拒绝）——FIX-289⑤ force 覆盖仅库内可达。既有面，但双半面工作流使「CLI 级对半面记录合规重录」成为现实需求，建议 follow-up 补旗标转发 `force=`。
- **P3-2**：owner 匹配大小写敏感（L438）而 slug 大小写折叠 → 同审查方异大小写名 → slug 碰撞同名文件 → 守卫 fail-closed 拒绝（无覆写、无损坏，仅 DX 困惑）。同意 Developer 观察 4 定位。
- **P3-3**：reviewer 原文入证据行 cell（含 `|`/换行可破表格形状）——既有面本 diff 未扩大（行格式逐字节不变），新证据 ID 已 slug 消毒而 cell 未消毒；建议未来消毒 pass（strip `[|\r\n]`）。
- **P3-4**：字面 `--reviewer unknown` 可认领无主记录（记录文本对 None 写 `- reviewer: unknown`，探针比对命中）。病态输入，备注。
- **P3-5**：canonical 缺失 + namespaced 存在（手工删除 canonical 才可达）→ 下次写入重占 canonical，namespaced 记录成孤儿（守卫只护 resolved 文件）。备注。

## 四、五维度 + AI 专项裁决

| 维度 | 裁决 | 依据 |
|---|---|---|
| 正确性 | **△（P1-1 一处）** | 键面解析/守卫/备份/行 ID 推导逻辑逐行核验正确；唯一例外 = 非 UTF-8 读失败路径 |
| 安全性 | ✓ | 无注入/敏感数据/权限面；文件名仅 `[a-z0-9-]`；task_id 白名单正则；P3-3 为既有面备注 |
| 可维护性 | ✓ | 模块/函数 docstring 与实现同步更新且准确（除 L387 一句被 P1-1 证伪）；`_reviewer_slug`/`_read_record_reviewer` 职责单一；键面决策注释含契约理由 |
| 性能 | ✓ | 探针仅 +1 次小文件读 + O(n) 正则，仅 canonical 存在且带 reviewer 时触发 |
| 测试覆盖 | ✓（两缺口注明） | 13 用例断言非自证：守卫用例断言文件字节不变 + 证据行计数；CLI 用例 `--project-root` 真 subprocess 临时隔离；hook 用例真提取真 bash 执行非重抄；Check 30 用例驱动真扫描器（patch 仅限路径注入）。缺口：①P1-1 非 UTF-8 用例缺失；②双半面 fixture × Check 30c 交互用例缺失（P2-1 因此漏网） |

**AI 专项 5 项**：mock 残留 无（`write_review_record` 全程零 patch）｜硬编码返回 无｜幻觉 API 无（全量绿跑佐证）｜未实现 TODO 无｜过度实现 无（改动收敛于键面扩展 + `_evidence_row` 可选尾参 + summary 增 `reviewer` 键；`verify_workflow.py` 零改动裁决正确）。

## 五、结论

**NEEDS_CHANGE**（P1-1 单项阻塞；P0=0，unresolved_blockers=1）。修复面极小（两处异常捕获 + 一条回归用例），不触及键面设计——键面/守卫/备份/hook 兼容/历史不可变性经多维独立实证全部成立。复审时须逐条比对：P1-1 已修复（GBK 探针复跑应得 error dict + exit 2 + 零写入）、P2-1 已注册 follow-up（或当轮一并修复 30c 三处名形）、P2-2/P3 按遗留计划。
