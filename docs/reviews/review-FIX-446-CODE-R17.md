# FIX-446 — Independent Code Review R17（DEC-351/352 限修补丁；只读审查）

```json
{"verdict":"APPROVED_WITH_NOTES","round":17,"unresolved_blockers":0,"review_scope":"dec351_352_limited_corrective_three_files_code","parent_full_product_complete":false}
```

## 0. 绑定、独立性与输入（全部一手实读；零 shell/写/测试/子agent）

- **审查对象**：终稿三 file（2026-10-14T08:20:12Z 绑定，validation log :8）——entity SHA `3aa63b47…`/31586B/blob `e4084d2b…`、engine `3a4ff909…`/70967B/blob `15768658…`、test_archive `9cca4549…`/332111B/blob `e97dc863…`。我未独立重测 hash（零 shell 约束，如实，与 R16 同口径）；绑定事实=Coordinator validation log :8 的 Get-FileHash+git hash-object exit=0 记录；我的核验是**内容级三层对照**（见下）。
- **三层对照全部一手实读**：(a) R17 终稿三 file 全文/关键段——entity 全 624 行、engine :1-539+:1279-1468、test :1-75/:95-149/:6236-6275/:6658-6943；(b) R16 冻结件 `FIX-446-R16-frozen-products/`（entity 612 行证据段+imports、engine :224-423+:1171-1240+尾、test 头部+R16 类 :6231-6270）；(c) R16 前基线 `FIX-446-product-baseline/`（entity :395-484 证据段+engine :85-114 `_write_archive_file`）。**S1 的等价性对照基线是 (c) 非 (b)**——R16 本身就是越权态。
- **结构等价性证据（engine）**：R16 冻结 1360 行 vs R17 1468 行，34 个 def/class **同名同序**；唯 `_verify_existing_archive_target`（:224，122→216 行）与 `_write_archive_file_never_overwrite` docstring（+14 行 F4/F7 措辞）变化，其后全部函数**等距平移 +108**；平移区抽查（`_write_archive_file` :91-97≡基线 :85-91、`_atomic_write_text` 尾、`_big_table_target_lock`、`_evidence_apply_commit` :1279-1317≡:1171-1209 逐行、文件尾 :1439-1468≡:1331-1360）均逐字一致——resumable 锁/digest 纪律零触及。
- **结构等价性证据（entity/test）**：entity 612→624 行=证据段分支重构 +12（imports :43-52 与 R16 冻结逐字同；decisions/risks/rollback 抽查 :243-256 逐字同）。test 6648→6947 行=模块 docstring +5+新类 `TestFix446R17EvdScopeAndTargetIdentity`（:6658-6943，6 用例）+`__main__` 移尾；R16 类 :6236-6275 ≡ 冻结件 :6231-6270 逐字保留。
- **观测证据**：R17-validation.log 9 行全文（含 :2-3 exit=2 形态错误命令零测试执行的如实记录）；4 份 rawlog 全文——red（5F/1P/201 deselect/exit1，`r17-red-focused-class.log` 353 行含完整 traceback）、green（15P+1s）、full（206P+1s+8subtests/4.17s/exit0）、related（Ran 146/OK/4.530s）；EVD-1692 反例三件套（probe.py 91 行/probe.log/receipt：真实 os.replace 置换、R16 返回 idempotent_skip 而 target SHA≠payload SHA、st_ino 21955048185001685→19984723348027094、安全断言 exit 1）；R16 报告全文；裁决卡 `FIX-446-R16-closeout-and-scope.md` F1-F7 解除条件表；R17-authorization.json（DEC-351 op-6cd4a4c8…+DEC-352 op-4cf2794f…，scope=三 file 限修+同独立 R17）。
- **独立性**：与 R16 非同会话；不沿 R16 结论与开发者主张，S1/S2/测试有效性均以终稿代码+rawlog+反例独立重推；对 R16 F1-F7 逐条按裁决卡解除条件重新裁决。
- **第五面（无第四 file）**：零 shell 不能跑 git status（validation log :8 有 exit=0 记录但输出未引用，如实披露）；替代证据=skills/**.py 全树 mtime 序（旧→新）清单 174 项，**最末三项恰为 test_archive→entity→engine**（与红测先行的开发时序吻合），其后再无更晚修改的 py。非 skills/ 的非授权新写未独立扫描（披露为限）。

## 1. S1 逐项裁决——**真闭合**

- **非 EVD 分支 vs 基线逐字等价（核对于 product-baseline，非 R16）**：entity else 分支（:462-473）可执行语句仅两条——`_write_archive_file(archive_path, header, archive_body)`（:472）+ `elog.write_text("\n".join(kept_lines), encoding="utf-8")`（:473），与基线 :437-438 **逐字相同**；上游计算亦同——family 命名 :437-441≡基线 :428-432、header :442-445≡:433-436、archive_body :423-425≡:422-424；分支只增注释。engine `_write_archive_file`（:91-97）与基线 :85-91 逐字同（文本模式 open("w")→Windows CRLF、同名碰撞=普通覆写、异常直接传播无包装、publish→hot 顺序不变）。非 EVD 家族恢复 **R16 前原调用/异常/byte 语义**成立。
- **EVD 分支真走 never-overwrite 原语**：:454-455 `_write_archive_file_never_overwrite` + :461 `host["_atomic_write_text"]`，调用点与 R16 相同（S2 修正只发生在 engine 判定内），archive-first/hot-after 顺序保持。
- **guard 测试真能防全局回滚**：`test_evd_leg_keeps_never_overwrite_semantics`（:6807-6821）毒化 `_write_archive_file` 后 EVD 迁移仍须成功——全局回滚（把 EVD 也退回 legacy writer）会当场红；`test_non_evd_families_not_routed_to_evd_only_primitives`（:6755-6783）双向毒化两个 EVD 专用原语后 REVIEW 腿须完整工作；`test_non_evd_family_keeps_legacy_collision_overwrite_semantics`（:6785-6805）钉死碰撞=普通覆写+直接 write_text 热写（REVIEW-OLD 消失、新行入档、热行移除）。
- **红证据直接暴露 R16 越权**：red rawlog :71-72 traceback 显示 R16 entity:455 对 **REVIEW** 家族调用 `_write_archive_file_never_overwrite`；:139-141+:266-268 显示 REVIEW 同名碰撞被 R16 以 foreign_bytes 结构化拒（恰是被裁决越权的新语义）。5 条红均有意义失败，非恒真。

## 2. S2 逐项裁决——**真闭合**

- **两窗口 identity 复验**：lstat 捕 `(st_dev, st_ino)`（engine :297）；窗口 1（lstat→readonly open）:309-330 fstat 复验 type+identity→`identity_changed`；窗口 2（readonly→O_RDWR 重开）:368 open 后 :380-397 fstat 再复验 type+identity。EVD-1692（probe 确定性复现：重开窗内置换后 R16 仍 idempotent_skip 且 target≠payload，exit 1）在 R17 被结构化拒。readonly fsync 成功路径（POSIX，:360-361）无需重开——fsync 作用于已过 identity 复验的 fd 所指 inode，路径置换无法转移其对象，逻辑自洽。
- **重开后 size+bytes 复验在 fsync/成功之前**：:398-408 size 门（`wst.st_size != len(payload)`→foreign_bytes）→ :409-415 全量重读→ :416-425 bytes 复验→ **然后才** :426 `os.fsync(wfd)`→ :439 返回。成功返回前置条件链完整。
- **F6 size 门真零 I/O**：readonly 腿 :331-341 size 门先于 :342 读循环；O_RDWR 腿 :398 先于 :409。`test_large_different_existing_target_refused_without_reading`（:6910-6943）以 os.read 计数器断言 32MiB 异件 `read_bytes_total==0`；红证据 :40 `33554432 != 0` 证明 R16 确实整读了 32MiB——反事实成立。
- **EVD-1692 回归与 probe 同 seam**：`test_target_swap_before_rdwr_retry_refused_no_false_success`（:6825-6873）复刻 probe 的确定性 seam（首次 fsync 拒 + 在 O_RDWR open 钩子处对**真实文件** `os.replace` 置换），非 mock 自说自话——identity 判定作用于真实 st_dev/st_ino（probe.log :19-26 实证本平台 os.replace 改变 st_ino）；断言 identity_changed+置换件 bytes 原样+热行逐字不动。`test_regular_swap_in_lstat_window_refused`（:6875-6906）以真实 decoy 的 os.stat 经 patched lstat 模拟窗口 1 置换，同为真实 stat 对象。红证据 :297/:344 两条 "BigTableMigrationError not raised" 即 R16 假幂等在测试内复现。
- **fail 路径保热行不动**：`_verify_existing_archive_target` 全程零写（O_RDONLY 只读；O_RDWR 打开后仅 fstat/read/fsync，无任何 write）；一切拒在 entity :461 热写之前抛出——结构上不可删热行。
- **有界读的微残余（见 F-2）**：docstring "only ever reads at most len(payload) bytes"（:248-249）严格说只由 size 快照保证；判读窗内并发 append 者可短暂推高读量直至 foreign_bytes 拒——属已披露的持写权对手类残余（docstring :260-271 已披露同类），静态占名件（F6 主张）确已闭合。

## 3. R16 F1-F7 处置核验（对照裁决卡解除条件逐条重判）

| Finding | R17 处置 | 依据 |
|---|---|---|
| F1 范围/注释不实 | **closed-with-evidence** | EVD/非 EVD 分支拆分+三向 guard 回归；注释 :447-453/:463-471 与代码一致（不再有 R16 "scoped to EVD only" 的失实共享注释）；红 traceback 直证 R16 越权被纠 |
| F2 identity/重开不复验 | **closed-with-evidence** | 两窗口 type+identity、重开 size+bytes 先于 fsync、同 seam EVD-1692 永久回归；「不宣称 inode 比对阻止任意持写权者未来修改」按裁决卡原文写入 docstring :260-271 |
| F3 symlink 平台 skip | **disclosed-limitation** | Windows 无符号链接创建特权，R16 类 skip 如实保留（green 15P+1s 的 1 skip）；R17 未新增 symlink 实测；新增的 S_ISREG+identity 判定在结构上覆盖 symlink 置换（非常规拒/identity_changed），但 POSIX O_NOFOLLOW ELOOP 腿仍未执行——按裁决卡「创建权缺失继续披露」为接受态，不升格阻断 |
| F4 目录 fsync 口径 | **closed-with-evidence** | never_overwrite docstring :470-482："a file fsync is NOT directory durability"、created 与 idempotent_skip 的持久化范围分述、不 claim 全平台断电保证 |
| F5 CRLF/旧 byte | **closed-with-evidence** | 非 EVD 恢复原文本 writer（CRLF 路径回归）；EVD 一切拒保旧 bytes verbatim（无写路径）；旧 CRLF 档遇 EVD forced 碰撞→foreign_bytes 保守拒（与 R16 同，未改） |
| F6 既有件整读 | **closed-with-evidence** | 两处 size 门先于读+32MiB 零读永久回归；CPU27.8/CLI36/semantic434339/32MiB/1500 门未出现在本 diff、未触碰 |
| F7 legacy 无锁 race | **closed（按披露义务）** | docstring :269-271 明确不宣称解决既有 lock-free race；新增同步依赖失败不静默——payload fsync 直接传播、verify fsync 失败→结构化 `durability_unverifiable` 拒；唯一吞没是 readonly→O_RDWR 重试转移（:362-364 pass，是重试非终态 no-op）；`_fsync_dir` 吞没为既有 FEAT-060 纪律未改。race 本体为继承性既有条件、在本票范围外如实保持 |

## 4. Findings（P0=0，P1=0）

- **F-R17-1（P3·docstring 措辞）** engine:245-249「byte comparison only ever reads at most len(payload) bytes」——该上界由 :331/:398 的 size **快照**保证；判读窗内持写权者 append 可使实际读取短暂超过 len(payload) 直至 foreign_bytes 拒（读后不等即拒，fail-closed 方向不变）。影响=措辞强于代码一档，行为缺口不超出已披露的 F2 类对手残余。修法=将句子限定为 "bounded by the gate-checked size；并发 append 仅延长读取至失配拒"。不阻断。
- **F-R17-2（P3·测试覆盖披露）** symlink 拒绝在本平台仍无 live 覆盖（skip 如实）；见上表 F3。不阻断。
- **验证限披露**：hash 未独立重测（零 shell）；git status 第五面以 validation log :8 记录+skills 全树 mtime 序清单替代直测；两者均沿用 R16 同口径披露，非新缺陷。

## 5. 五维 + AI 专项

**正确性 PASS**——S1 三向语义（EVD 专用硬化/非 EVD 基线逐字等价/guard 防回滚）与 S2 两窗口判定经逐行重推成立；红→绿反事实链完整（5 红均因 R16 缺陷、绿仅因 R17 修正；全量 207 项=201+6、related 146 与 R16 同集零回归）。**安全性 PASS**——verify 零写、一切拒保热、结构化 fail-loud、有界读、判定不可转移至置换对象；对抗残余（判定后同 inode 修改、判读窗内 append）均披露未超 claim。**可维护性 PASS**——分支结构镜像裁决；注释/代码一致（F1 纠正）；verify 函数 ~216 行但单一职责+完整 docstring；`_expected_evd_payload` 行模板与 `_make_evidence_log` 有少量重复，漂移时会以 foreign_bytes 红显而非静默过。**性能 PASS**——异 size 件零读拒、读量以 payload 长度为界（非对抗态）；全量 4.17s（R16 3.194s，增量=6 新测含 32MiB truncate）；无 per-row I/O 新增；性能门未动。**测试覆盖 PASS（附 F3 披露）**——S1 双向 guard+碰撞 byte 语义钉死、S2 两窗口+EVD-1692 同 seam、F6 零读、错误路径（identity_changed/foreign_bytes/durability_unverifiable 分类断言）、related 回归；覆盖率%未测不编造。**AI 专项 5 项**：无 mock 残留（全部 with/ExitStack 域内，四轮 suite 绿证无泄漏）/无业务硬编码（sentinel 均为测试面 fixture）/无幻觉 API（os.lstat/S_IFMT/st_dev/st_ino/O_NOFOLLOW getattr/_fsync_dir try-import 全一手核实存）/变更区无 TODO 或未实现桩/无过度实现（无 uid 闸、无锁重构、无第四 file——恰按裁决卡边界）。

## 6. 硬门槛与范围声明

P0=0 ✓｜P1=0 ✓｜5 维 100% ✓｜AI 5 项 100% ✓｜每条发现 P 级+path:line+影响+修法 ✓｜事实红线（每结论锚 终稿:行/rawlog 行/probe 记录；未验证处显式标明：hash 未独立重测、symlink live 未证、git status 未直测、覆盖率未测）✓。**round17≥3 fuse**：零未解阻断，不触发；无 R18 建议。**范围**：本 APPROVED_WITH_NOTES/unresolved_blockers=0 仅覆盖 DEC-351/352 三 file 限修补丁（S1 范围隔离+S2 假幂等闭合+F6 有界读）；不改变 FIX-445 CodeR6 ×3 BLOCKED、64tests/1FAIL、full23/exit1、source NOT_ESTABLISHED、隔离 witness FAIL 等父面事实；实际治理归档迁移仍禁、无 commit/push/release、无自动 R18、外部人类 DRI unknown 不发明。

（审查过程：read/grep/glob 累计 30+ 次，覆盖角色文件+SKILL+R16 报告+授权/验证链+4 rawlog+反例三件套+裁决卡+三终稿必要段+两层冻结基线对照+engine 34 函数结构等价核验+skills 全树 mtime 清单；零执行零写入。本正文为唯一最终稿，供 Coordinator 逐字落盘 `docs/reviews/review-FIX-446-CODE-R17.md` 后机录 review-record。）
