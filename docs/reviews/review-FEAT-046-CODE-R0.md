# REVIEW-FEAT-046-CODE-R0 — 独立代码审查（governance_store 写入器族，批 1 票 2）

- **Task**: FEAT-046（locks-extend/amend + evidence-append/decision-append 同管道族）
- **Round**: R0（首轮独立审查；Reviewer 与 Developer 物理隔离，未复用 Developer 任何验证结论作为依据）
- **审查对象**（工作树未提交，两新文件）:
  - `skills/software-project-governance/infra/governance_store.py`（新建，1,812 行）
  - `skills/software-project-governance/infra/tests/test_governance_store.py`（新建，938 行 / 68 测试）
- **语义基准**（逐一实际读取，非转述）: `infra/contracts.py`（m0-r1 冻结面 face 1/3/4/5）；`docs/planning/0.86.0-arch-consult-round2-external.md` §3/§5；`docs/planning/0.86.0-architecture-evolution.md` §4（DoD 0–9）；`docs/planning/version-plan-0.86.0.md` §2 批 1 FEAT-046 行；`docs/planning/0.86.0-boundary-audit.md` B-2/B-3/B-5；`verify_workflow.py`（Check 13/16/26、`_split_markdown_table_row`、`_split_governance_table_row`、`parse_impact_analysis_entries`、`parse_recent_decisions`、`acquire_dispatch_locks`）。
- **范围纪律**: 其余 M/?? 态文件（版本 bump、并行票 task_row_update 等）出范围。verify 全量未复跑（任务已预警 FEAT-053 bump 在途中间态可能 FAILED——AGENTS.md stale 已知项），归因区分如下：本报告全部结论仅锚定本票两文件 + 基准文档 + 隔离环境实跑。

---

## 总结论

## **NEEDS_CHANGE** — P0=1 · P1=0 · P2=4 · P3=10 · **unresolved_blockers=1**

一句话：交付质量整体高（骨架机检/幂等恢复/原子写/引用五类型/×415 政策逐项成立，68 套件独立实跑通过，dry-run 真表复演字节级零写入实证），但 **locks 族幂等冲突腿存在一处违反 face 5 冻结不变量的必崩逻辑错误（P0-1）**，且该腿恰好没有测试——这是本票核心验收面（DoD 2）上的真实缺口，须修复后复审（R1）。

---

## P0 findings（阻塞合并）

### P0-1 locks 族 `operation_id_conflict` 腿抛未捕获 `ContractViolation`，违反 face 5 冻结不变量与本模块自身结构化拒绝契约

- **位置**: `governance_store.py` L1378-1382（`_locks_execute` 内）
- **事实链**（每步可复查）:
  1. contracts.py L1132-1136（m0-r1 冻结）：`WriterResult` 不变量——conflict 类 code **必须**携带 `observed_revision`，缺失即 `_fail`（`ContractViolation`）。
  2. `_locks_execute` 冲突分支：`_refuse(_error_result(op_id, "operation_id_conflict", "…mint a new operation id"))`——**未传 `observed_revision`**；`_error_result`（L290-302）在构造 `WriterResult` 时即抛 `ContractViolation`，`_refuse` 永不执行。
  3. `ContractViolation` 是 `ValueError` 不是 `StoreError`：`_returns_payload`（L320-338）与 CLI `_run`（L1669-1673）都只捕 `StoreError` → 异常穿透到调用方/终端。
  4. **红相复现**（隔离临时目录，零仓库写入，本审查实跑）：
     ```
     UNCAUGHT ContractViolation: WriterResult: conflict code 'operation_id_conflict'
     requires observed_revision (CAS 冲突返回当前状态与冲突原因，由调用方重判 — arch round-2 §1)
     ```
  5. 对照组：append 族同一分支（L1019-1024 / L1177-1181）正确传 `observed_revision=len(original)`，且有测试 `test_same_operation_different_payload_conflicts` 守护——**locks 族既缺正确实现也缺测试**（`LocksExtendTests`/`LocksAmendTests` 只有 replay/resume/drift，无 conflict 用例；这正是 68/68 全绿仍漏网的原因）。
- **违反的验收面**: DoD 2（「同 ID 不同输入拒绝」——拒绝必须是结构化 refusal，不是 traceback）；模块 docstring「refusals carry the closed code + disposition」；`main()` 退出码契约（0/2/3——本腿实际 exit 1 + 非 JSON traceback）；acquire 管道「Never raises」同族约定（change_triage.py L825）。
- **影响**: 现实可达——操作者带同一 `--operation-id` 重试但修改了任一载荷参数（如改 `--reason` 错字）即触发。无数据损坏（冲突检查先于任何 mutate/apply，fail 方向仍关闭），但重试协议的 conflict 腿完全失效且以最不结构化的方式失败。
- **修复建议**（一行 + 一测试）: 该分支补 `observed_revision`——`path` 已在 L1374 加载，传 `len(_read_bytes(path))` 即可（与 append 族口径一致）；补 locks 双命令的 same-op-different-payload 负控测试各一（断言结构化 `operation_id_conflict` + `observed_revision` 非空 + 世界无变化）。

---

## P1 findings

无。

---

## P2 findings（建议本轮修改，不单独阻塞；随 P0-1 一并复审）

### P2-1 dry-run 未执行 ID 碰撞校验——dry-run PASS 不能预测实写拒绝，DoD 5「完整校验结果」在该腿不成立

- **位置**: `_dry_run_append`（L725-742）用 `_peek_next_id`（无碰撞检查）；实写用 `_next_row_id`（L631-646，含热∪archive 碰撞拒绝）。
- **事实**: 在 `test_id_collision_with_archive_refused` 同型 fixture 下，dry-run 会返回成功预览（next_id=EVD-903），实写则 `cross_record_violation`。现有 `test_dry_run_writes_nothing_anywhere` 用无 archive fixture，未覆盖此分歧。
- **方向安全**（实写仍拒绝，无数据风险），但 DoD 5「renders … the full validation result」声明在该腿不真实。建议：dry-run 复用 `_next_row_id` 的碰撞判定（只读，不写），或输出中显式披露「碰撞校验未在 dry-run 执行」。

### P2-2 账本条目缺 `input_fingerprint` 形校验——外部损坏账本可致 locks 双重施加

- **位置**: `_load_ledger`（L505-532）只校验 `status ∈ {ok, pending}`；`decide_operation_replay` 对 `stored_fingerprint=None` 返回 `"execute"`（contracts.py L729-730）。
- **事实**: 一条被手工编辑/外部截断的 `status=ok` 且无指纹的 locks 条目 → decision=execute → 走正常施加腿 → TTL 二次延长（append 族有世界 marker 兜底，locks 族 execute 腿无世界比对）。触发前提是机器文件被带外改写，概率低但后果是静默双施加。
- **建议**: `_load_ledger` 对每条目补 `require_input_fingerprint`（face 1 已有 API）——非法即 `manual_intervention` fail-closed，与该函数既有 malformed 拒绝口径一致。

### P2-3 `--files` 帮助文本宣称「semicolon/comma-separated」，实际仅按逗号分割

- **位置**: `build_parser` L1698-1699（help 文本）vs `main()` L1773 `_split_cli_list(args.files, ",")`。
- **事实**: 按帮助文本用分号传参 → 单个字面 `"a;b"` 键 → `cross_record_violation`（「file a;b is not locked」）。fail-closed 但文档承诺的形态静默失效。二者取一：改 help 只说 comma，或 `main` 先按 `;` 再按 `,` 分割。

### P2-4 空目标文件 + `expected_revision` 冲突 → 结构化拒绝不可构造（`observed_revision=0` 违反正整数不变量）→ 同型未捕获崩溃

- **位置**: L1004-1010 / L1162-1168：空文件 `len(original)=0`，`expected_revision≥1` 必不等 → `_error_result(..., observed_revision=0)` → `WriterResult._require_positive_int` 抛 `ContractViolation`。
- **触发前提**: 热文件为空（init 模板非空，罕见）。与 P0-1 同根（error_result 腿的 invariant 死角），建议一并处理：`observed_revision` 为 0 时改报 `manual_intervention`（世界态无法满足 CAS 通道）。

---

## P3 findings（记录/后续批，不阻塞）

| # | 位置 | 说明 |
|---|------|------|
| P3-1 | L1482/L1549 | locks 两命令未调 `SCHEMA_WINDOW.require_supported`（append 两命令有）——一致性 nit |
| P3-2 | L475-486/`__exit__` | stale lockfile 600s 接管链：A 持锁 >600s → B 接管 → A 结束时 `__exit__` 会 unlink B 的活跃锁文件，瞬时互斥侵蚀（需 A 病态慢才可达）。**接管语义未写入 docstring、`_stale()` 无负控测试**（见 DoD 7 行） |
| P3-3 | L828-853 | `governance_id` 热文件检索是全文 mention 级（`\bDEC-221\b`），非行锚定——与 ID 分配的行锚定 `_hot_id_numbers` 不对称；typo 引用即可判 resolvable。resolvability-only 语义下可接受，建议 docstring 披露或行锚定 |
| P3-4 | L786-789 | `repo_file` 未做根内包含检查：绝对路径/`..` 前缀可逃逸 `repo_root`（只读 `is_file`，无写入面，但「路径合法」未落实）。建议 `resolve()` 包含性检查 |
| P3-5 | L1240-1243 | bool `ttl_seconds` 穿透 Check 26 镜像（`isinstance(True,(int,float))`=True）——**引擎 Check 26 同源同洞（L17707），镜像忠实**；写入器侧可独立收紧而不构成第二 schema |
| P3-6 | L719-722 | 空目标文件追加会产生前导空行（`b""` 不以 `\n` 结尾 → 补 `\n`）——纯外观 |
| P3-7 | `_atomic_write_bytes` | 文件 fsync 有、目录 fsync 无（POSIX 崩溃持久性 nicety；Windows 无影响） |
| P3-8 | 模块 docstring L47 | 「DoD nine items」实际枚举 0–9 十条——措辞 nit |
| P3-9 | 模块 docstring L182-185 | 「a row accepted here cannot add engine findings」**今日成立但属间接成立**：引擎 `parse_impact_analysis_entries`（L12426-12433）对现行 10 列形存在既有错位（`parts[4]`＝description 被当 type、`parts[5]`＝basis 被当 description；live 行 EVD-1106/1107/1108 实证 parts[3]=type/parts[4]=desc/parts[5]=basis），Check 16 选择面当前对这些行为空/偶然排除。写入器的骨架正则与 Check 16 逐字一致（L12502/L12697 vs L185-188 实证），但**单元格定位口径并未对齐**；引擎侧修正索引后本票行反而正确通过（description 届时被正确读取且已含 ≥30 目标对齐）。建议 docstring 把该声明收敛到「正则逐字镜像」层面。引擎错位系既有问题，**出本票范围**，建议另行入账 |
| P3-10 | `main` L1676-1680 | retryable→exit 3 分支无 CLI 级测试（API 级 `test_lock_contention_is_retryable` 已覆盖 disposition） |

---

## 十项审查重点逐项结论

| # | 重点 | 结论 | 关键证据 |
|---|------|------|---------|
| ① | 三命令语义正确性 | **基本正确，一处 P0** | locks-extend/amend 复用 Check 26 schema 属实（store `_validate_locks_schema` L1218-1248 与引擎 L17670-17720 逐字段一致，无第二 schema）；acquire 键规范化一致（change_triage L713 ≡ store `_normalize_path`，正斜杠/不小写）；真 acquire 管道一致性风险即 P0-1 所在 conflict 腿（append 族对齐、locks 族不对齐）。evidence-append 骨架校验 **严于** Check 13/16 口径（10 列全非空 + 目标对齐≥30 写时强制；更严方向安全 ✓）。decision-append 5 列 live 形处置正确：live 实证 DEC-213/214/217~221 均 5 列（历史 DEC-215 9 列），5 列漂移早于本票；`parse_recent_decisions` 按表头名映射非固定位置，5 列行可解析（topic 归因降级为引擎既有行为，非本票引入） |
| ② | 五类型引用机检 | **逐行成立** | 对照 arch round2 §3 表：repo_file 存在性 ✓（P3-4 根内包含缺口）；git_object 表单校验（L191 `^[0-9a-f]{7,40}$|^HEAD~N$`）后 argv-list `git rev-parse --verify`（L795-798，无 shell、timeout 15s、git 不可用→not_yet_verifiable ✓）；governance_id 热+archive 检索 ✓（P3-3 mention 级注记）；URL 仅语法不抓取 ✓（test_url_alias_syntax_valid_not_fetched）；human_observation 恒 not_yet_verifiable ✓。reference_validation≠verdict ✓：三态闭枚举、无充分性推导、resolvable 不写「通过」字样 |
| ③ | 幂等与恢复 | **架构正确，conflict 腿 P0** | effect-based：append 世界 marker 恢复（L1028-1037）+ 锁内 pending 台账（target+baseline 快照）→ world==target 完成 / world==baseline 重放确定性 mutator / 双不匹配 manual_intervention（L1372-1399），与 FEAT-051 同型的 effect_present_without_receipt 窗口（行已落账本未记）由 marker 恢复腿正确闭合（test_world_recovery 实证）。receipt-without-effect 方向不可达（写序：目标先、账本后 + 原子替换）。P2-2 为带外损坏账本的残余窗口 |
| ④ | 原子写细节 | **成立** | 同目录 temp + `os.replace` + fsync（L367-383）；`.encode("utf-8")` 无 BOM（test_crlf_preserved_and_no_bom 断言首字节非 EF BB BF）；行尾按文件尾字节判定保持（CRLF 测试）；追加严格字节前缀保持（prefix 比较 L694-701）；写后自检异常只披露不回滚（arch round2 §5「恢复受版本检查保护」✓） |
| ⑤ | DoD 0–9 逐项 | **0/1/3/4/6/8/9 全过；2、5 带 finding；7 带 gap** | 0 ✓（类型/形状检查、git_object 先验表单、URL 不抓取、管道/换行拒绝）；1 ✓（候选行锁内先建全验后写）；2 **P0-1**（conflict 腿）；3 ✓；4 ✓（同一 validator 复用，test_row_validation_and_postwrite_share_one_validator 断言 is 同一函数）；5 **P2-1**（dry-run 碰撞腿）+ 结构化四分类 ✓（exit 2/3）；6 ✓（无手改半成品：pending 台账可重入）；7 基本 ✓（键碰撞/GBK/缺行/重放/并发/崩溃/特殊字符/legacy 八类各有负控；**缺**：locks-conflict 腿〔P0-1 之因〕、stale 接管〔P3-2〕）；8 ✓（模块自承载 opt-in，引擎零路由，回退=既有通道）；9 ✓（basis 格 `机器写入：governance-store <cmd> <op-id>；schema v1` + actor 格 `governance-store`） |
| ⑥ | 新 .governance 工件 | **工件成立、披露不足（P3-2 并入）** | `governance-store-ops.json` / `.governance-store-locks/` 实装且引擎零引用（grep 实证 verify_workflow 无任何读取）——与「渐进启用、批 2.0 集成」口径自洽；但「无 check 覆盖」与「600s 接管」两点均未在 docstring/风险面披露。账本无界增长已有 BT-4（evolution §5）登记承接，建议本票 docstring 互链 |
| ⑦ | 68 测试质量 | **红相五类齐、两处缺口** | 列形 ✓（管道/换行/inline-code）引用 ✓（5 kind×正反+枚举+三态）重放 ✓（append/decision/locks 三族）并发 ✓（8 线程 Barrier，本审查单跑通过）崩溃 ✓（双族 world recovery）。缺口：locks conflict 腿零覆盖（P0-1 之因）；`test_resume_applies_once_from_baseline` 断言 `assertIn(source,("apply","resume"))` 过弱（无法区分走哪条腿）；stale 接管无负控 |
| ⑧ | dry-run 复演 | **实证通过** | 本审查真表复演：`next_id=EVD-1109`（动态编号，live max=EVD-1108）、`governance_id:DEC-221=resolvable`、`repo_file:…governance_store.py=resolvable`、**evidence-log.md 与 decision-log.md SHA256 前后一致、ledger 未创建**——与 Developer 申报（EVD-1108 时点动态编号+零写入）同口径复现。P2-1 为预览完整性缺口，不影响零写入承诺 |
| ⑨ | 自承载组合根 | **合理且合规** | version-plan §2 批 1 明文裁定「`infra/governance_store.py` 新建独立文件」；引擎 87 键冻结 dispatch 面零增长（grep：除本票测试外无任何文件引用 governance_store）；`cleanup.py`/`archive.py`/（并行票）`task_row_update.py` 同款直调先例；engine-dispatch 接线显式留给集成切片——**非规避，是规划内行为** |
| ⑩ | AI 专项 5 项 | **全部干净** | mock 残留：产品码零 mock（测试内 `mock.patch` 为合法 test double：git 不可用注入/写后自检 spy）；硬编码返回值：无（G11/✅ 完成 为文档化 CLI 默认参数）；幻觉 API：contracts 面 11 个消费符号逐一对照 contracts.py 存在且签名一致；未实现 TODO：grep 零 TODO/FIXME/NotImplemented/placeholder；过度实现：无（locks-release 正确出批 1 范围；无投机功能） |

---

## 独立复验表（Reviewer 自跑，未采信 Developer 任何运行结论）

| # | 复验项 | 命令/方法 | 结果 |
|---|--------|----------|------|
| V1 | 68 套件实跑 | `python -m pytest skills/.../test_governance_store.py -q` | **68 passed in 1.46s** |
| V2 | 并发测试单跑 | `pytest -k concurrent` | **1 passed**（8 线程零丢行、ID 唯一） |
| V3 | dry-run 真表复演 | CLI `evidence-append --dry-run`（真 `.governance`，只读） | 动态编号 EVD-1109；refs 双类型 resolvable；**两表 SHA256 前后一致；ledger 未创建** |
| V4 | P0-1 红相复现 | 隔离临时目录：种子账本同 ID 异指纹 → `locks_extend` 重试 | **UNCAUGHT ContractViolation**（与 finding 逐字一致） |
| V5 | 引擎镜像 parity（只读 diff） | splitter/Check 26/Check 16 正则逐字比对 | `_split_row` ≡ `_split_markdown_table_row`（L351-373）；`_validate_locks_schema` ≡ Check 26 条目校验（L17670-17720）；两骨架正则 ≡ L12502/L12697 |
| V6 | 组合根隔离 | 全仓 grep `governance_store` | 引擎/注册面零引用（仅本票测试 + m0 manifest 消费声明 + baseline_metadata docstring 提及） |
| V7 | 未复跑项 | archguard 全量 / verify 全量 | Developer 申报未受本审查挑战（分层读证：governance_store 仅 import contracts，L0-only ✓）；verify 全量因 FEAT-053 bump 在途不具归因条件，未采信亦未否证 |

---

## Developer 申报独立复核对照

| 申报 | 复核结果 |
|------|---------|
| 68/68 四轮复跑无 flake | 本审查 1 轮实跑通过（68/68）；「四轮」不复现，无反证 |
| verify 全量 PASSED（当时点） | 不具当时点复现条件；未采信未否证（范围纪律） |
| cross-refs/manifest PASS | m0 manifest 确将 governance_store 列为 face 1+3+4+5 消费者（manifest.json L67），与代码一致 |
| archguard 本票文件零违规 | 未复跑；分层静读支持（仅 L0 import） |
| dry-run 真表演示零写入 | **复现**（V3） |
| 8 线程并发不丢行 | **复现**（V2） |
| ×415 legacy 行零触碰 | 代码路径只追加不改写（`_append_row_bytes` 纯前缀拼接）+ `test_legacy_x415_rows_untouched_after_append` ✓；Check 14 ×415 WARN 基线政策（arch round2 §3「存量 legacy 批次只检读取安全」）执行方式正确 |
| Check 13/16 口径对齐（含更严方向） | 正则级逐字对齐 ✓ + 更严方向（全列非空/写时强制）✓；**单元格定位口径未对齐**（P3-9，引擎侧既有错位，本票行两种世界下均不产生新 finding，但声明措辞过强） |

---

## 复审指引（R1 必查）

1. P0-1 修复diff：`_locks_execute` conflict 腿携带 `observed_revision`；locks 双命令 conflict 负控测试各一（结构化 code + observed_revision 非空 + 世界字节不变 + CLI exit 2）。
2. P2-1~P2-4 处置声明（修复或附遗留计划与批次）。
3. 前轮 findings 逐条「已修复/未修复/新引入」比对（M7.4 step 4.6）。

## 遗留建议（不阻塞，供 Developer/Coordinator 排期）

- P3-2 的接管语义与两工件「无 check 覆盖」披露写入模块 docstring（或 risk-log 补一行）；
- P3-9 的引擎 `parse_impact_analysis_entries` 列位错位**另行入账**（独立 ticket/audit，勿在本票顺手修——修改纯粹性 D4）；
- 账本轮转与 archive.py 对 `governance-store-ops.json` 的感知留给批 2.0 集成切片（BT-4 已登记）。

---

*Reviewer: 独立 Code Reviewer（FEAT-046-CODE-R0）。只读审查 + 本报告写入 `docs/reviews/`，未触碰代码与 `.governance/`；V4 复现运行于系统临时目录。*
