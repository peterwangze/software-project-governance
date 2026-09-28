# Review FEAT-075-R1 — 四行族 dry-run + 聚合层例外标注（DEC-278 单元二）复审

- **round**: R1（复审轮；前轮引用：docs/reviews/review-FEAT-075-R0.md，R0 结论 NEEDS_CHANGE：P1×1+P2×1+P3×3）
- **日期**: 2026-09-28
- **Reviewer**: 同一 Code Reviewer（R0）——按 M7.4 step 4.6 复审协议：逐条比对前轮 findings，验证返工而非重扫全域
- **复审范围**: 返工面（落档 §1/§3/§4 重写 + exception_registry.py/verify_workflow.py 渲染层披露 + 两测试文件）+ 产品代码主链回归抽查
- **结论**: **APPROVED_WITH_NOTES，unresolved_blockers=0**

## 1. 前轮 findings 逐条处置对照

| # | R0 级别 | 处置 | 核验事实（本轮亲证） |
|---|---|---|---|
| F-1 | P1（阻塞） | **已修复** | 落档 §3 全节重写为机械分解（§3.1/§3.2/§3.3），恒等式双口径精确闭合（独立复算见 §2）；措辞矛盾消除（「估算解析面无系统性高估证伪——估算判可迁的行中被六条件实测阻塞的仅 28 行〔估算未建模的更严门：重复 ID 24+显式保留 4〕」——精确限定、无自相矛盾）；第三方向假说行级定谳零贡献（§3.3）+ U₃=0 显式桶；§1 新增扫描后漂移注记（REVIEW 634 live vs 锚定 633——亲证 L2923 追加行存在、文件 2,923 行，注记属实）。 |
| F-2 | P2 | **已修复** | `registry_error_note()`（exception_registry.py L299-313：errors 非空→一行披露，清洁/缺文件→""）+ 包装器（verify_workflow.py L1122-1128，延迟导入 R6 保持）+ 两条渲染路径 attach-once 闩锁（28s 块 L16636-16646；共享渲染器 L22468-22483）。清洁态输出逐字节不变（零新增 print，R4 1318=1318 一致）。新测试 L22515-22558 亲读：恰一次披露 + counts 返回不变 (2,0) + 清洁注册表零输出。 |
| F-3 | P3 | **已修复** | `_now_iso` 已删（grep 0 命中）；import 收窄 `from datetime import date`（L33）。 |
| F-4 | P3 | **已修复** | test_archive.py L5341-2345：勘正为锚定机械计数 633=404 plain+42 scope+**183** valid no-round+4 malformed（404+42+183+4=633 ✓）并注明原「187」系 183+4 合并误记；archive.py 模块注释未含错误数字、维持原状（单侧勘正+机械锚定，成立）。 |
| F-5 | P3 | **维持（知识记录）+ 本轮勘正** | 代码面事实不变（`_split_ref_ids` 部分匹配收整 token，archive.py L2253-2261，继承单元一语法面，方向安全）。**R0 所引 live 实证例经本轮定谳撤销**：R0 grep 输出中的「TRIAGE-FIX-302 \| FIX-3更控制」为工具截断拼接伪影——直读 L1793 实为干净行，`FIX-3更控制` 全文 grep 0 命中、疑似源行 TRIAGE-FEAT-051（L2349）本身干净。F-5 结论不受影响（代码事实来自读码而非该行）。 |

## 2. §3 恒等式独立复算结果（F-1 验收核心）

**加总闭合（§3.1）**：X 470 + U₁ 164 + U₂ 74 + U₃ 0 = **708** ✓；242,985 + 67,501 + 120,252 + 0 = **430,738** ✓（与 §2.2 三族小计精确相等）。U=238/187,753 与 R0 解锁面（REQ 74+FEAT 154+FX 10=238；120,252+49,422+18,079=187,753）同数重构 ✓。

**偏差闭合（§3.2）**：X+B = 498/261,045 ✓；δ = +3/−2,118 ✓；Δ = U−B+δ：行 238−28+3 = **+213** ✓；字节 187,753−18,060−2,118 = **+167,575** ✓。**双口径逐项精确相等，R0 的 +94 行/+37,836B 残余消解。**

**B=28 的第三方交叉复算（不依赖 Developer 上报）**：由 R0 已证数据独立推导 ≥1 窗三族被阻塞行 = oor 24（全窗 10+窗移 14）+ unparseable 26 + active 8 + duplicate 56 + keep 5 = **119 = R0 原「收紧面」全量**；返工 B=28（duplicate 24+keep 4）+ 估算亦排除 91 = 119 ✓——「原 119 系把估算同样排除的 91 行误计入」的归因与独立推导精确咬合。

**第三方向静态抽查（§3.3 声明）**：三族空 col2 grep **0 命中**；受损 token 形态 grep **0 命中**——「零空列、零失配」抽查通过；U₃=0 桶在闭合恒等式内承载该结论（恒等式精确闭合本身即行级定谳的证明）。

## 3. F-2 断言亲读摘要

`registry_error_note` 语义正确：registry 级（非 finding 级）错误→一次性披露，首条 finding 行附加，闩锁防重复；清洁→""→渲染逐字节回退。零 findings 边界（闩锁未触发→该路径不显示）：可接受——无 finding 即无「被静默不标注」对象，且 release 披露块无条件承载 registry errors。包装器延迟导入保 R6 冻结面；引擎增量 +42→+65 与三处新增账面一致。

## 4. 新引入问题扫描

零阻塞新引入。已核：主链零回归（五守卫原位 L1893/L2678/L3079/L4916/L5351/族规格未动/延迟导入保持/`exceptions.json` 仍不存在=live 惰性）；exception_registry 无新增模块级依赖（datetime 反而收窄）；MUST NOT 红线返工零触碰（披露性追加≠语义变更）。测试面：FEAT075ExceptionAnnotationTests 11→12（新测试在类内）；FEAT075RowFamilyScanTests 11 未动。

## 5. 硬门槛自检（R1）

- [x] 逐条比对前轮 findings（F-1~F-5 全处置标注：已修复×4/维持×1）
- [x] round=R1 头部+前轮引用声明
- [x] P0=0；阻塞 finding 计数=0（F-1 修复经双重独立复算确认）
- [x] §3 恒等式行/字节双口径独立复算精确闭合
- [x] F-2 新增渲染面亲读（代码+测试）
- [x] 只读纪律：零写入/零命令/零子 agent/零用户交互
- [x] 事实锚定：每条处置带文件+行号或独立复算

## 6. 终态结论

**APPROVED_WITH_NOTES，unresolved_blockers=0**。F-1（R0 唯一阻塞项）经机械分解+双口径精确闭合+第三方交叉复算确认修复；F-2/F-3/F-4 亲证修复；F-5 维持知识记录并附 Reviewer 侧勘正（R0 live 实证例系工具伪影）。产品代码主链（R0 已亲证）零回归。

**Notes（非阻塞，留痕）**：
- N1：估算重建规则与原临时脚本规则集可能存在差异——原脚本已删不可考，δ=+3 行/−2,118B（0.6%/0.8%）标定其上界；档已如实将 δ 定性为「不可复现性的量化」，处置诚实。
- N2：渲染路径零 findings 时 registry-error 不显示（无被抑制标注对象；release 块无条件披露兜底）——未来细化项。
- N3：R0 F-5 live 实证例更正记录（grep 拼接伪影；代码事实不变）。
- N4：R0 遗留不确定项 1-3（`_make_ref_verdict` verbatim git 对照、live sha256 锚、测试运行声明采信）维持原结论不变。

## 证据清单

1. 前轮报告：docs/reviews/review-FEAT-075-R0.md（78 行重读，与 R0 交付一致）
2. 返工落档：feat-075-four-family-dryrun-20260928.md §1 漂移注记（L20）/§3 全节（L58-90）/§4 registry-error 披露句（L96）
3. F-2 代码：exception_registry.py L299-313；verify_workflow.py L1122-1128/L16634-16647/L22466-22484
4. F-3：exception_registry.py L33；`_now_iso` grep 0 命中
5. F-4：test_archive.py L5341-5345（404+42+183+4=633）；archive.py L2210-2215（未动）
6. 主链回归：archive.py 五守卫 grep 原位；verify_workflow.py 延迟导入 L1109/L1118/L1127
7. live 交叉：evidence-log L1793 直读（干净行——R0 伪影定谳）；`FIX-3更控制` grep 0 命中；TRIAGE-FEAT-051 L2349 干净；L2923 REVIEW-FEAT-075-R0 追加行；三族空 col2 grep 0 命中；`.governance/exceptions.json` 仍不存在
8. 独立复算：§3.1/§3.2 全部加总与恒等式；B 补集 119=24+26+8+56+5 由 §2.1+窗移算术独立推导咬合

## 遗留不确定项

1. N1（估算重建规则 vs 原脚本规则集差异）——不可考且已被 δ 标定+档内如实披露，非阻塞
2. R0 遗留 1-3 维持：`_make_ref_verdict` verbatim git 对照（可由 Coordinator `git diff c90768f` 一次性定谳）、live sha256/字节锚采信、测试运行声明（FEAT075 两类 23/23、test_architecture_health 24/24、test_archive 170/170、verify 聚合 exit 0、manifest 968）按硬门槛采信——修改面与声明账面一致
3. N2（零 findings 路径的 registry-error 显示）——未来细化候选，登记即可
