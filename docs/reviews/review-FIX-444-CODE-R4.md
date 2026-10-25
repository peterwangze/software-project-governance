# FIX-444 CODE R4 审查报告（DEC-370/DEC-371 恢复 R1）

- 审查对象：未提交 WIP 两文件（hooks/commit-msg +800/1、tests/test_hooks.py +975/2，vs HEAD=e1fceae）
- 审查者：Code Reviewer（独立 R4；一手复验，不采信自报）
- 日期：2026-10-25
- 授权链：DEC-370（解堵）→ DEC-371（R0 三项裁定）→ R1 实现票
- 历史链：R0~R3 三度熔断（标记类逃逸/谓词先行背书/sed-grep fail-open）→ DEC-334 转承 → 本票恢复

## 结论（L12）

FIX-444: APPROVED_WITH_NOTES (unresolved_blockers=0)

## 审查发现（逐项证据）

### 1. 验收① 误报修复（synthetic 面）
- 24-probe 老假 RED 形态全转 GREEN（R6 M3 载体 + DEC-371 三方向增量）；EVD-1536/1587/1588/1610 四实证形态逐行入 test_dec371_disjunction_midclass / ascii_prefix_and_dangzhen_tail / mention_marker_form 三用例，全部 assertFalse 复验。
- live 面（72 行 FIX-445 族外）：FIX-444 热行 72 行经真实 Step-12 路径复跑零 HIT（本审查独立 live 复跑 seen={FIX-444:72} clean）。

### 2. 验收② 安全语义不回退
- 攻击矩阵 12 行（prose 标记/无凭证包裹/伪造身份/UTC 第 7 位裁剪/背书框架/嵌入字）**逐行独立 spawn 断言**（B2 恢复，:1256-1270）——本审查隔离复跑 16 测试中 15 绿，逐行断言真实非 batch-any。
- 三方向红测邻居齐全：①闭表外中位词（成本）仍 BLOCK；②纯 ASCII 前缀（cnt==0）与「把编造结果当真提交」仍 BLOCK；③跨子句 laundering 与标记前主张仍 BLOCK。
- 当真三分支攻击面：本审查构造变体复核——bare 提及（cnt=0 窗拒绝）、imperative 尾（当真执行→框架→窗 cnt=0 拒）、对象尾（当真视为真实数据→框架）均 BLOCK；仅情态否定尾 disarm（EVD-1587 形）——fail-closed 方向正确。

### 3. 验收④ 自升级不绕 hook
- SelfUpgradeNoBypassTests 双测：正常升级回执（含 DEC-371 准入形态的诚实使用）clean；夹带「载荷含编造。我编造了…当真视为真实数据提交」laundering 仍 BLOCK。语义面成立。

### 4. sed/awk 分工与 locale
- sed 腿全部字面交替（无否定字符类承载 CJK——EVD-1610 字节碰撞注释在案）；字符级语义（endorsement 窗/提及剥离）走 awk C.UTF-8 字符模式；两处 locale 探针 fail-closed（不可用→BLOCK/不剥离保守向）——三连踩结论成立且已固化注释。

### 5. 范围与纪律
- diff 恰两文件（独立 numstat 复核）；WIP 漂移独立重测绘：+1,284B（vs R6 blob）= DEC-371 三方向增量（当真三分支/ASCII filler/strip_mention_clauses），全部落 R1 授权面；
- 知识资产注释（字节坑论证/闭表纪律）物有所值——R6→R1 复发防御依赖这些论证留在源码内；
- hook 主路径（Step 11~14）零重写：Step-12 仅换挂 has_unnegated_fabrication_terms（:1236），其余步骤逐行核对未动。

### 6. 独立复跑汇总
- 四关键类隔离：15/16 绿（唯一 FAIL 属 FIX-445 live 面，见 R7 报告）；
- verify PASSED / manifest PASS / xref exit 0 / write-guard PASS 0 issue；
- 全量 discover：本审查复跑已完成 exit 1——失败与模块级隔离定位完全一致（唯一 FAIL=live 门 B4，见 R7 §4；摘要计数行被测试 stdout 挤出未捕获，模块级 69 tests/1 fail 已独立复现）。R1 冻结自报 5083 OK skipped=2 跑于 EVD-2157 入账前，与本复现不冲突。两文件 diff 不涉其他模块，CI 提交时再全量权威。

## Notes（非阻塞）
- N1（沿 R7 报告共享）：live 门在当前真树因 EVD-2157（FIX-445 面）红——不属本票验收面（FIX-444 行 clean），但**提交合并前必须先解**（Step-12 按任务族扫描，FIX-444/445 合体提交会被物理拦截）。
- N2：EVD-1610 入表=方向①机制实例确认（显式交替成员、封闭、无通配）；类成员现为 6（追加扫描/新增扫描〔R6 既有〕+ 预算/时间/权限〔DEC-371 名〕+ 异常隐藏〔EVD-1610 追认〕）——较 DEC-371 文本多 1 个追认 token，Coordinator 追认在案，本审查确认其为实例非泛化，留档此精确计数。
- N3：R5 引擎 C6/identity/dmap/CH-7 面在 R6 链已审，本票未触碰（blob 对照+抽读确认），不重复展开。
