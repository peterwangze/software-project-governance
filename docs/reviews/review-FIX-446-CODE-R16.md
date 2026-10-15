# FIX-446 — Independent Code Review R16（DEC-350 限定归档保真；只读审查）

```json
{"verdict":"APPROVED_WITH_NOTES","round":16,"unresolved_blockers":0,"review_scope":"legacy_evidence_preservation_per_dec350_code","parent_full_product_complete":false}
```

## 0. 绑定、独立性与输入（全部一手实读；零 shell/写/测试/子agent）

- **审查对象**：producer 正式停写后冻结三元组（final-bindings.json，2026-10-14T03:28:51Z）——entity SHA `01a6e9a7…`/30818B、engine `75dbc485…`/65018B、test_archive `536bd47d…`/316345B；冻结 diff `FIX-446-final-diff.patch` 717 行**全文逐行实读**（3 files/641+/4-，无第四写面）。我未独立重测 hash（零 shell 约束，如实）；以 Coordinator 冻结 patch+bindings 为绑定事实。
- **产品上下文实读**：entity 终态 :1-53(imports)/:331-462(`_migrate_evidence_impl` 全函数)/:466-519(rollback 分组)；engine 终态 :40-86(imports)/:91-97(`_write_archive_file` 原样)/:141-203(增量命名族)/:205-221(异常类)/:224-345(`_verify_existing_archive_target`)/:348-404(`_write_archive_file_never_overwrite`)/:407-433(`_atomic_write_text` 未改)/:1050-1209(resumable stage/apply 未改)/:1212-1258；archive.py :140-180(engine import)/:269-349(host wrappers)/:421-425(`host=globals()`)/:535-595+:620-704(`_run_entity_migrations`/families 循环)；governance_store :425-438(`_fsync_dir`)/:441-458(`_atomic_write_bytes`)/:511-544(`_TargetLock`)；test_archive :1-139(imports+fixture)/:6226-6648(新类终态)。冷 baseline 三件备份对照实读（entity :400-449、engine :60-124 等）。
- **观测证据**：4 receipts+4 rawlogs 全文实读（red 10/6F/3E/1skip/exit1；green 10/9ok/1skip/exit0；test_archive 全量 201/OK(skipped=1)/3.194s/exit0；related 146/OK 零skip/4.138s/exit0——合计 346 passed+1 skip=347 项，**非 347 PASS、非零 skip**）。授权链：DEC-350/op-82063…、R15 设计 156 行、R15 设计审查 55 行、authorization.json、R16-challenges、CODE-R6（父边界，未改未宣布关闭）。
- **独立性**：不沿 producer 叙述；Coordinator 三项质疑（共享call面/O_NOFOLLOW-identity/dirfsync）均独立核验并入 findings。

## 1. C1-C10 逐项裁决（挑战表非预定判决，逐项以代码/log 为据）

- **C1 同范围二批 PASS**：EVD 腿命名改经真实 host 链 `archive._next_evidence_archive_filename`(:341-343)→engine `_make_incremental_archive_filename_impl`(:141-171，base 不存在用 base 名、存在则 `-incremental-DATE-N`)；red log :143 字节级反事实（旧码 EVD-101 字节覆写 EVD-001 档，`\r\n` 可见）→green 同断言通过且旧 bytes `assertEqual` 逐字节比对（test :6354），非仅文件计数。无第四 file（patch 全文只有 3 节）。
- **C2 同名竞态 PASS**：O_EXCL 排他创建（engine :382-383）；负者走 EEXIST→verify，全程对既有 entry **零写零删**（EEXIST 分支仅 O_RDONLY 读+fsync、O_RDWR 无写 fsync），不可能删对方件；异内容 `foreign_bytes` 拒+旧 bytes 逐字保留（test :6383 断言 `target.read_text()==foreign`）。
- **C3 现目标判定 PASS**：等内容分支真实可达且只读（mtime sentinel 1000000 不动，test :6415）；异内容拒；lstat `S_ISREG` 先拒非常规（目录/静态 symlink→`not_regular`，test :6433 目录结构化拒；red 期为裸 PermissionError）；red :8 symlink skip=平台无创建特权，非 PASS（见 F3 残余）。
- **C4 中途失败 PASS**：publish 内 fsync 失败→OSError 传播、hot 逐字节不变、自身半件留终名不删（test :6521）；torn publish→hot 不动（test :6546）；不存在任何删除路径，"未知件不删"平凡成立；半件=fail-loud 可对账标识。
- **C5 archive 成/hot 中断重试 PASS**：crash 注入经 host 面 `patch.object(archive,"_atomic_write_text")`（真实 composition，archive.py :166 import 使其为 module global）；重试落**新**增量档、原档 bytes 不变、EVD-050 留热、双在如实断言为保守非恢复（test :6579）。
- **C6 partial+并发重试语义 PASS**：digest=byte 全等+独占 FD；等-但-未 durable 拒（`durability_unverifiable`，test :6490 fsync 注入两段式：拒→健康重试幂等完成）；热行删除从不依据不稳定现目标内容——一切拒均保热。
- **C7 家族隔离 PASS（附 F1 披露）**：decisions/risks/tasks writer 未动（entity :245/:327、archive.py :744 仍 `_write_archive_file`，grep 全仓核实）；resumable 五阶段代码零 diff 触及（apply :1177 锁/digest 复核原样）；`stat` stdlib、`_fsync_dir` 走既有 try-import 块——无新 import 环；201+146 回归绿。**但** :455/:461 在 family 分支后共享执行，REVIEW/TRIAGE/RECO 腿同样获得 never-overwrite+原子 hot 写（有效差=碰撞路径静默覆写→结构化拒、hot 截断→原子；正常路径 bytes 同构）——保守硬化、落在 R15 §3.4 授权编辑点（:437 共享行），且 R15 §3.2 本就谴责"调了生成名仍普通 w"；注释措辞失实见 F1。
- **C8 反事实证明力 PASS**：red 10 项中 9 项有意义失败（含 ImportError/AttributeError 证 seam 缺失、mtime/字节/结构化异常三类断言），1 平台 skip 如实；forced_name 固定命名 seam=对 compute-name→publish 竞争落点的合理模拟（竞争在此实现中必然落为 EEXIST），真实抢占式调度交织未模拟（披露，非 mock 伪 green——所有注入均在真实文件系统上生效）。
- **C9 命令/隔离 PASS**：四 receipt 命令全文/UTC 起止/child exit/rawlog 齐备；workdir=infra；TEMP/TMP/HOME/USERPROFILE/DSH_HOME 重定向至仓内 FIX-446-sandbox（red traceback :50 显示 fixture 落 sandbox/tmp）；`-B -Xutf8`；零真实治理数据/安装器接触；suite 内 kill137=注入语义、suite 真 exit0 未混淆。
- **C10 状态诚实 PASS**：本通过仅限 DEC-350 保真子范围；父 FIX-445 CodeR6 ×3 BLOCKED、64tests/1FAIL、full 18/exit1、source NOT_ESTABLISHED、隔离 witness FAIL 全部不因此改绿；无 registry/白名单/自授格。

## 2. Findings（全部非阻断；P0=0）

- **F1（P2·可维护性/范围措辞）** entity:451-454 注释"this fix is scoped to the EVD evidence leg only"与事实不符：:455 never-overwrite 发布与 :461 原子 hot 写位于 family 分支之后，经 `_run_entity_migrations`(archive.py:582-588，ALL=families :634-635) 同样治理 REVIEW/TRIAGE/RECO。影响=误导后续维护者以为 family 腿仍 open("w")。修复=改注释为"EVD 命名分支+四家族共享 never-overwrite 发布"；不阻断（行为方向严格保守、回归绿、编辑点在授权行内）。
- **F2（P2·加固缺口，对抗性残余）** engine `_verify_existing_archive_target`：(a) lstat(:254)↔fstat(:284) 仅比 mode，未比 st_dev/st_ino——lstat→open 窗内 regular→regular 置换不可检；(b) Windows `O_NOFOLLOW`=0（:252 getattr 默认），lstat 后换入 symlink 会被 open(:274) 跟随读取；(c) O_RDWR 重开(:320) 不复 stat/不复比 bytes——durable 化的是重开时路径所指向者。docstring"fstat re-check refuses any swap"仅对非常规 swap 成立，措辞过强。后果有界：EEXIST 分支零写零删、旧 bytes 构造性保全；最坏=微秒窗+目录写权+byte 等价/读后置换的主动对手诱使幂等分支放行热删（对手行为致损，非本补丁写入）；基线为无条件截断，严格更劣。建议后续加固票：lstat/fstat 及 O_RDWR 重开后 (st_dev,st_ino)+bytes 复验。
- **F3（P3·测试覆盖）** symlink 拒绝在主部署平台（Windows）无创建特权→skip，POSIX O_NOFOLLOW ELOOP 腿亦未执行；静态非常规拒由代码序（lstat S_ISREG 先于 open）+目录测试(:6433)旁证，live 覆盖未证——receipt 已如实披露非 PASS。
- **F4（P3·durability 口径）** 目录项持久化为 best-effort：`_fsync_dir` 在 Windows 整体吞没（governance_store:425-438 一手核）、minimal-packaging 回退为 None（engine:82-86/:400-403 注释披露）；crash 于 publish 后 hot 前热行完好可重试；crash 于 hot 后，Windows 目录项存续依赖 FS 日志——与既有 `_atomic_write_bytes`(:441-458) 全治理写同口径，非新回归；代码未超claim（"nicety/best-effort"措辞如实）。
- **F5（P3·字节格式）** 新发布为严格 LF 二进制；旧 `_write_archive_file` 文本模式在 Windows 产 CRLF（red log :143 `\r\n` 实证）。非竞争命名下不再重指旧 CRLF base；forced/竞态碰撞遇旧 CRLF 档→`foreign_bytes` 拒（保守）。hot 重写经 `_atomic_write_text`=LF，与 resumable 既有纪律一致；读取侧 universal-newline。
- **F6（P3·资源）** byte 比较整读既有件入内存、无 fstat st_size 预检短路；巨型占名件→同量级内存读。治理目录所有权限界，方向保守。
- **F7（P3·并发披露）** legacy 一次性腿仍无锁（`_big_table_target_lock` 仅 resumable apply :1177 持有）：hot 读-改-全量重写窗内并发 append 丢失=**既有**语义（旧 `elog.write_text` 同窗），本补丁未引入未扩大，且消除截断撕裂模式；DEC-350 未授权为 legacy 腿加锁（那将改其他家族路径）。

## 3. 五维 + AI 专项

正确性 **PASS**（W-A2 闭合：red 字节反事实→green 同断言；并发/中断推演有据，残余见 F2/F7 均非本补引入）｜安全性 **PASS**（无注入/权限扩张；结构化 fail-loud 拒；旧 bytes 构造性保全；对抗残余有界披露）｜可维护性 **PASS（附 F1）**（单一算法无 N-R15-3 fork——无 temp+replace 分支；helper ~120 行含完整 docstring，职责单一）｜性能 **PASS**（每次发布增一 file-fsync+best-effort dir-fsync+一次既有件读，per-migration 非每行；全量 201 测 3.194s）｜测试覆盖 **PASS（附 F3）**（核心/边界/错误路径 10 情形+回归 346P；覆盖率%未测不编造）。AI 专项：无 mock 残留（patch 全在 with 内）/无业务硬编码（sentinel/常量为测试面）/无幻觉 API（`_fsync_dir`、host 键、`O_NOFOLLOW` getattr 全实存一手核）/无 TODO/无过度实现（Windows EACCES 消歧为真实主平台用例，uid 不设闸已在 docstring 披露理由）。

## 4. 硬门槛与范围声明

P0=0 ✓｜P1=0 ✓｜5 维 100% ✓｜AI 5 项 100% ✓｜每条发现 P 级+path:line+影响+修法 ✓｜事实红线（每结论锚 文件:行/log 行/receipt；未验证处显式标明：hash 未独立重测、symlink live 未证、覆盖率未测）✓。**范围**：本 APPROVED_WITH_NOTES/unresolved_blockers=0 仅覆盖 DEC-350 三文件 legacy evidence 归档保真实现；不构成 FIX-445 CodeR6 三阻断的复审闭合，不改变 full 18/exit1、source NOT_ESTABLISHED、隔离 witness FAIL、64tests/1FAIL、四源门/12 攻击/B3/NFR 原门任何一项；P3/G1/谓词/registry/来源授格/实际迁移/风险接受/真实 HOME/commit-push-release/自动 R17 均未实施未授权。round16≥3 fuse：本轮零未解阻断不触发；无 R17。外部人类 DRI unknown 不发明。

（审查过程：read/grep/glob 累计 20 次，覆盖 2 角色文件+7 治理输入+冻结 diff 全文+4 产品文件必要段+2 基线对照+governance_store 原语+4 receipts+4 rawlogs；零执行零写入。本正文为唯一最终稿，供 Coordinator 逐字落盘 `docs/reviews/review-FIX-446-CODE-R16.md` 后机录 review-record。）
