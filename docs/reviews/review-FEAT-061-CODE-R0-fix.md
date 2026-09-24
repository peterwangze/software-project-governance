# REVIEW-FEAT-061-CODE-R0 修复说明（Developer → R1 复审输入）

> 性质：修复说明文档（非审查报告——R1 由同席 Reviewer 撰写）。
> 依据：REVIEW-FEAT-061-CODE-R0 = NEEDS_CHANGE（unresolved_blockers=2，P0×2 活体复现实证 + P1×2 同批验收钉 + P2/P3 同批建议）。
> 修复范围：P0-F1 / P0-F2 / P1-F3 / P1-F4 全部 + P2 三项全做 + P3 四项全做。

## F-1（P0）epoch fencing 端到端缺口 — 已修复

**审查复现场景**：写入者通过 entry 的 `load_authority`（无锁、无 expected_epoch）后被调度间隙跨越 cutover 线性化点 → 进入 md 腿锁临界区直接追加 → 记录仅落投影面 → 下一笔投影销毁。

**修复**（`governance_store.py`）：

1. 新增 `_revalidate_authority_in_lock(governance_dir, entry_authority, timeout_seconds)` 共享助手：
   - `load_authority(expected_epoch=entry_epoch)` —— 任一线性化（freeze/activate/rollback）推高 epoch → `revision_conflict`（携带 observed_epoch），调用方回到新世界重新裁决；
   - frozen 状态重检（entry 后才开始的冻结 → `illegal_transition`，C1-ARCH-02 写拒绝语义在锁内同样成立）；
   - backend 重检（后端翻转 → `revision_conflict`，拒绝本腿执行）。
2. md 腿（`decision_append` 的 `_TargetLock(target)` 临界区首语句）与 json 腿（`_decision_append_json` 的 `_TargetLock(json_target)` 临界区首语句）均插入同一重校验。

**闭合性论证（审查方向的落实）**：entry 检查无锁 → 窗口存在；目标锁与迁移控制器全部状态转移所获锁为**同一互斥体**（`_TargetLock` 同一路径锁文件）——锁在握期间权威标记不可能再变化，故「锁内一次 fenced 重读」在两腿分别完备闭合。dry-run 路径不写任何文件，不入锁、不做重校验（维持预测语义）。

**验收钉（P1-F4）**：
- `test_case_11_entry_epoch_interleaves_linearization_md_leg`——seam 在 `_TargetLock.__enter__` 触发（写者**持锁前**被去调度的真实时序；dmig/drepo 持未打补丁的锁引用，嵌套 cutover 干净穿透）：entry（MD_ACTIVE）→ 完整 cutover（epoch 0→2）→ 锁内重校验 → `revision_conflict` + observed_epoch=2 + md 字节不变（记录从未落盘）+ 终态 JSON_ACTIVE。
- `test_case_12_same_scenario_normal_path_and_json_leg`——(a) 同 seam 正常路径回归：世界不动 → append ok（seam 活跃性以 `calls >= 1` 断言）；(b) json 腿对称交错：JSON_ACTIVE 下 entry 后完整 rollback 线性化 → json 腿锁内重校验拒绝 + 回退导出 md 原样 + 终态 MD_ACTIVE。

## F-2（P0）duplicate_acceptances 丢失 → 热文件砖化 — 已修复

**审查复现场景**：`_decision_append_json` 以四键字面量重建 `new_store` → 合法可选键 `duplicate_acceptances`（勘正对接受注记，持久化于 store 内）丢失 → 落盘后 post-write reread 的 `load_json_store` 立即 `cross_record_violation`，但 store 已写入 → 砖化。

**修复**：`new_store = dict(store)` 后仅覆盖 `records`/`items` 两键——任意合法可选顶层键随载入的 store 原样存活。

**验收钉**：`test_append_preserves_store_top_level_keys`——store 带 `duplicate_acceptances`（DEC-194 勘正对）经 cutover 后 append：顶层键集不变（`set(after) == set(before)`）、acceptance 值不变、store 保持可载入（无自致砖化）、投影 fresh、新记录 DEC-238 正确落位。

## F-3（P1）rollback_activate 摘要复检不对称 — 已修复

- `rollback_begin`：在 json 目标锁内钉住当前 store 摘要 → 权威标记 frozen 载荷新增 `frozen_store_digest`（返回值同步携带）。
- `rollback_activate`：json 锁内对当前 store 摘要与 `frozen.frozen_store_digest` 对称复检（activate 的 frozen→current 门的回退侧镜像）——不一致 → `manual_intervention`（回退窗完整性失败，世界保持冻结，重启回退）；缺失字段（前 P1-F3 时代的冻结记录）→ 拒绝并提示重跑 rollback-begin。

## P2（同批完成，非阻塞项）

1. **投影失败类别完整化**：`_decision_append_json` 投影尝试捕获 `(StoreError, OSError, ValueError, UnicodeDecodeError)`——非 StoreError 不再穿透 `@_returns_payload`，「已提交、投影待修复 + exit 0」承诺对所有失败类别成立（checkpoint `last_error` 按类型记录）。
2. **权威标记未知键白名单**：`_validate_authority_document` 增加 `_AUTHORITY_TOP_KEYS` 白名单——未知键 = 畸形/被篡改标记 → `manual_intervention` 拒绝（权威标记是唯一权威源，未校验的额外键不得静默携带）。
3. **rollback_begin 取 json 锁**：store 摘要读取在 `_TargetLock(json_target)` 内完成（与 append/activate 同一互斥）。

## P3（同批完成）

1. **用例计数勘正**：52（不是 50——24 repository + 21 migration + 7 verify；`--collect-only` 实证）。含新增 3 例：case 11 / case 12 / 键集保持钉。
2. **演练口径勘正**：真实 decision-log.md 全输入分类 = **179 行**（分类面），其中 **DEC 记录 116 条**（118 管道行 − 1 表头 − 1 分隔行）；演练报告含 11 处 `DEC-nnn①` 模拟处置 + 7 变体行显式接受 + 1 组勘正对接受。
3. **fixture mojibake 修复（FIX-278 口径）**：演练报告改为脚本直写文件（显式 UTF-8，不经控制台管道）；三个子进程调用点（控制器 `_run_verifier` / 测试 `_verifier` / 演练 `run_cli`）统一 `-X utf8` 钉住子进程 stdio 编码；`decision_migration.main` 增加 UTF-8 stdio reconfigure。fixture 复核：U+FFFD 计数 = 0。
4. **docstring 失准两处**：governance_store 模块头 `decision-append` 描述改为双后端口径；`decision_append` docstring「Appends at end-of-file」改为「追加为权威工件末项（md=文件尾行 / JSON=末记录）」。

## 验证结果（完成标准逐项）

| # | 完成标准 | 结果 |
|---|---|---|
| ① | F-1 复现场景反演 | ✅ test_case_11（seam=锁获取前交错，审查场景的锁内反演）——拒绝 + observed_epoch=2 + md 字节不变 |
| ② | F-2 真实形态测试 | ✅ test_append_preserves_store_top_level_keys——带 duplicate_acceptances 的 store append 后键集不变、无砖化 |
| ③ | 10+2 用例全绿 | ✅ 12 崩溃并发用例（10 原始 + ⑪⑫ seam 交错）+ 键集钉全绿 |
| ④ | 回归零退化（154 基线） | ✅ 157（52 新 + 105 governance_store 基线）+ 263（triage_write_guard/archive/bootstrap/archive_decision/product_code）全绿 |
| ⑤ | verify/cross-refs/manifest PASS | ✅ verify exit 0 + check-cross-references exit 0 + check-manifest-consistency exit 0（另：check-duplicate-code/check-locks/引擎 dispatch dry-run 探针 exit 0） |

**真实数据演练（P0/P1 修复后重跑）**：verify PASS → activate exit 0 → rollback-export exit 0 + reverse PASS → rollback-activate exit 0 → 字节回环 True；fixture `infra/tests/fixtures/feat061-rehearsal-result.json`（19 步、零 U+FFFD）。

**红线复核**：真实权威切换未执行；`.governance/` 零写入（git status 复核为空）。

## 修改文件（本修复批）

| 文件 | 修改 |
|---|---|
| `infra/governance_store.py` | F-1（`_revalidate_authority_in_lock` + 两腿锁内调用）、F-2（`dict(store)` 重建）、P2-1（投影失败类别）、P3-4（docstring ×2） |
| `infra/decision_repository.py` | P2-2（`_AUTHORITY_TOP_KEYS` 白名单） |
| `infra/decision_migration.py` | F-3（rollback_begin 钉摘要 + rollback_activate 对称复检）、P2-3（json 锁）、P3-3（`-X utf8` + stdio reconfigure） |
| `infra/tests/test_decision_migration.py` | F-4（case 11/12）、F-2 钉（键集保持）、`_verifier` utf8 |
| `infra/tests/fixtures/feat061-rehearsal-result.json` | P3-3 干净 UTF-8 报告（修复后重跑，19 步全链 PASS） |

测试执行命令：

```
python -m pytest skills/software-project-governance/infra/tests/test_decision_repository.py skills/software-project-governance/infra/tests/test_decision_migration.py skills/software-project-governance/infra/tests/test_decision_migration_verify.py skills/software-project-governance/infra/tests/test_governance_store.py -q   # 157 passed
python skills/software-project-governance/infra/verify_workflow.py verify            # PASSED
python skills/software-project-governance/infra/verify_workflow.py check-cross-references
python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency
```
