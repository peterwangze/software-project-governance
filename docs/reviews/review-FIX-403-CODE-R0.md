# Code Review Report — FIX-403 (CODE-R0)

- **Task**: FIX-403 — 热修 `_run_identity_attestation_fixture_only()` TemporaryDirectory 清理崩溃（UAC 过滤令牌 WinError 5 → check-governance 全量面崩溃，违反 never-crash 契约）
- **Reviewer**: Code Reviewer Agent（独立 R0）
- **Round**: R0（首审）
- **审查对象**: `skills/software-project-governance/infra/verify_workflow.py`（21265-21308）、`skills/software-project-governance/infra/tests/test_verify_workflow.py`（314-373，新增 `FIX403IdentityFixtureCleanupContractTests`）；diff +78/−1，与 Developer 报告一致
- **审查方法**: git diff 全量 + 函数/测试全文阅读 + 本机 Python 3.14.3 标准库源码独立核验 + 契约测试一手复跑

## 结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`

| P0 | P1 | P2 | P3 |
|----|----|----|----|
| 0  | 0  | 2  | 2  |

五项验收标准全部满足（①never-crash 契约恢复 ②契约测试真实走 rmtree 清理链 ③3.14 逃逸选型论证成立 ④零范围外修改 ⑤测试风格一致）。P2 为遗留建议，不阻塞。

## 关键裁决点核验：Python 3.14 onexc 逃逸论断 — **成立**（源码级证据）

Developer 论断：`ignore_cleanup_errors=True` 无法封堵该逃逸，因为恢复 chmod 的 raise 发生在 tempfile 的 onexc 处理器内部、处于其 ignore_errors 检查点之外。本审查未采信 Developer 实证报告，直接读取本机 `C:\Python314\Lib\tempfile.py` / `shutil.py`（3.14.3, MSC v.1944）源码独立核验：

**旧链逃逸路径（逐帧）**：

1. `TemporaryDirectory.cleanup()`（tempfile.py:973-975）→ `self._rmtree(self.name, ignore_errors=self._ignore_cleanup_errors)`
2. `_rmtree`（tempfile.py:916-955）把全部恢复逻辑放进自定义 `onexc`，最终 `_shutil.rmtree(name, onexc=onexc)`（L955）——**不向 shutil 传递 ignore_errors**
3. shutil 侧 `_rmtree_unsafe`（shutil.py:669-711）经 `os.walk(..., onerror=...)`（L688）遍历；`os.scandir` 的 PermissionError 经 onerror 包装（L685-687）转发 `onexc(os.scandir, err.filename, err)`——**该调用点无任何 try 包裹**
4. tempfile 的 `onexc`（L917-953）PermissionError 分支执行 `_resetperms(path)`（L927），其外层 `try/except FileNotFoundError: pass`（L924-948）**只捕获 FileNotFoundError**
5. `_resetperms`（L280-287）→ `_dont_follow_symlinks(_os.chmod, path, 0o700)`；`_dont_follow_symlinks`（L273-278）**无任何异常处理** → `os.chmod` 的 PermissionError 原样向上传播
6. 该异常绕过 L947 的 FileNotFoundError 捕获 → 从 onexc 返回到 shutil 裸调用点（步骤 3）→ 穿透 `rmtree` → `TemporaryDirectory.__exit__` → 生产代码崩溃

**`ignore_cleanup_errors=True` 为何无效**：它只作为 onexc 内部决策点的条件（L920-921 / L942-943 / L952-953 的 `if ignore_errors: return / raise`），控制"已捕获异常是否 re-raise"；而 `_resetperms` 在 L927 抛出的**新异常**从未进入任何这些决策点，L947 的 except 又与其类型不匹配。结构性无效，非偶发。

**新链为何闭合**：`shutil.rmtree(path, ignore_errors=True)`（shutil.py:832-834）在入口处将 onexc 整体替换为 no-op（`def onexc(*args): pass`）；`_rmtree_unsafe` 的全部错误出口（lstat L675 / walk onerror L687 / rmdir L697,711 / unlink L705）均路由到该 no-op；且 **shutil.rmtree 不做任何主动 chmod 权限恢复**，不触碰 `_resetperms`。清理期任何 OSError 均被吞噬，无法逃逸。

**裁决**：任务首选方案（`ignore_cleanup_errors=True`）经源码确认不能修复此崩溃；Developer 偏离首选方案的理由真实、充分，且替代方案（`mkdtemp` + `finally` + `shutil.rmtree(ignore_errors=True)`）是当前标准库下唯一能保证清理零逃逸的最小改动形态。

## 维度逐项结论

| 维度 | 结论 | 依据 |
|------|------|------|
| **正确性** | ✅ 通过 | `finally` 语义完整：try 块内两条降级 return（21296/21302）、正常完成、未捕获 BaseException 传播——所有路径均先执行 `shutil.rmtree(ignore_errors=True)` 再离开；`import shutil` 已存在（verify_workflow.py:27）；`mkdtemp` 失败（TEMP 不可写）与旧 `TemporaryDirectory()` 构造失败位置/行为等价，无回归 |
| **异常吞噬边界** | ✅ 合理 | `ignore_errors=True` 吞掉全部清理 OSError，但该目录是自建一次性 fixture（prefix `fix200-identity-`），清理失败不携带任何 verdict 语义（verdict 已在 try 块内产出或降级），唯一后果是目录遗留 TEMP——注释（21273-21276）已明示该可接受性，与 OS TEMP 生命周期兜底一致 |
| **契约** | ✅ 通过 | docstring 承诺 "the governance check never crashes on identity work"（21239）经修复真实恢复；测试断言（不 raise + `verdict`/`issues`/`phase` 三键 + 类型校验）与契约逐点对应 |
| **测试质量** | ✅ 通过 | monkeypatch 靶点 `os.scandir`/`os.chmod` 精确命中生产崩溃链的两个必经点（os.walk→scandir；tempfile onexc→_resetperms→chmod）；`patch.object(os, "scandir", ...)` 对 `os.walk` 模块内名字查找生效（绿相一手复跑 `Ran 1 test in 0.973s OK` 证实）；**未整体 mock 清理机制**——shutil.rmtree/os.walk 真实运行，验收标准②满足；红相（旧代码 + deny patch 下 __exit__ 崩溃）未复跑（需回滚工作区），但其路径经上述源码逐帧推演结构性成立，且 Developer 提供的同签名红相 traceback 与推演帧序一致，可信 |
| **回归** | ✅ 通过 | 三处调用方（verify_workflow.py:16788 Check31 / 21329 `_loop_runtime_claim_gate_detail` / 21533 standalone CLI）消费同一 `{verdict, issues, phase}` 结构，结构未变；PENDING/FAIL 降级分支（21295-21306）逐行未动；本审查一手复跑新测试 1/1 OK |
| **安全性** | ✅ 无新面 | 临时目录生命周期管理内部化，无输入校验/注入/敏感数据/权限面变化 |
| **性能** | ✅ 无影响 | mkdtemp 与 TemporaryDirectory 等价（均一次 mkdir，0700）；rmtree 同为一次树遍历 |
| **AI 专项 5 项** | ✅ 全过 | ①mock 残留：无（两个 patch 均在 with 作用域内，测试结束后自动还原）②硬编码返回值：无（断言为结构/类型，不伪造具体 verdict——契约测试正确定位）③幻觉 API：无（mkdtemp/rmtree/ignore_errors/PermissionError(errno, strerror, filename) 三参构造均为真实 API 且经源码核验）④未实现 TODO：无 ⑤过度实现：无（修复最小化：生命周期管理替换 + 单个契约测试） |
| **范围纪律** | ✅ 通过 | diff 仅触及两文件；verify_workflow.py 改动局限于注释 + mkdtemp/try/finally 包装（21265-21308），try 块内逻辑零改动；Developer 自报的两处范围外同类模式（L21038 `spg-external-validation-`、L21601 `fix216-scanner-`）核实存在且确未被本 diff 修改 |

## Findings

### P2（建议修改，可遗留）

- **P2-1【契约文档】** `verify_workflow.py:21234-21239` — 函数 docstring 的降级承诺仅列举 "failure to build the attestation (missing files, attestation module issues)"，未涵盖本次修复新增的清理失败降级面；说明目前由函数体内 FIX-403 注释（21265-21276）承担。建议下一轮将该面补入 docstring（如 "including temporary-directory cleanup failure"），让契约第一读者可见。非阻塞：in-code 注释已完整准确。
- **P2-2【风险外溢/立项建议】** `verify_workflow.py:21038`、`verify_workflow.py:21601` — 同文件内 `spg-external-validation-` 与 `fix216-scanner-` 两处仍使用未防护的 `TemporaryDirectory` 模式，同一 UAC 过滤令牌环境下理论上仍可发生同类清理崩溃。Developer 已自报并建议另立任务（核实属实；其报告行号 21586 与实际 21601 有轻微偏差，不影响结论）。按范围纪律本任务正确地未动它们——建议 Coordinator 尽快立项（可复用本次的 mkdtemp+finally+rmtree 模式或抽公共 helper）。

### P3（讨论，不要求修改）

- **P3-1【测试】** `test_verify_workflow.py:344/351` — deny 判定用子串匹配 `"fix200-identity-" in str(path)`；理论上 fixture 外路径若含该子串也会被拒，但 prefix 由 mkdtemp 控制且作用域仅限测试进程内，实际风险为零。仅记录。
- **P3-2【测试】** `test_verify_workflow.py:362` — 红相包装 `except Exception` 不覆盖 BaseException（如 SystemExit）；若未来回归以 SystemExit 崩溃，测试仍失败（以 error 形态而非友好 fail 消息）。行为等价红，无需修改。

## 回归风险评估

**低**。理由：(a) 变更仅替换临时目录生命周期管理，attestation 构建、降级分支、返回结构逐行未动；(b) 三调用方均经 helper 间接受益（单点修复全覆盖，与 Developer 声明一致）；(c) 本审查一手复跑契约测试通过；(d) Developer 提供的定向 12 测试中相关项 4/4 ok，7 个 ERROR 经 git stash 实证为预先存在的环境性失败（本沙箱对运行期临时目录内文件操作返回 WinError 5），与本修复无关；(e) 真实环境双面验证（重定向 TEMP 38 issues / 默认 TEMP 40 issues，均 EXIT=0，后者正是崩溃场景降级为 PENDING issue 入账的一手证据）。

## 放行建议

**放行（APPROVED_WITH_NOTES，unresolved_blockers=0）**。P2-1 建议随下一触碰该函数的任务顺带完成；P2-2 建议 Coordinator 另立任务覆盖两处同类未防护模式。无阻塞项，无需 R1。
