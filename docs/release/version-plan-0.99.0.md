# 0.99.0 版本计划（REL-103 范围盘点）

> 状态：**范围定稿**（2026-10-23 用户三项裁决：承载=b 仅验证结论 / FIX-444·445=ii 顺延 0.100 / P2=FIX-448 §11 裁决先行，FIX-447/455/457/FEAT-099 保持现状随发布披露）
> 窗口：`v0.98.0`（tag，taggerdate 2026-10-16 09:11:06 +0800，160a7f0→7f161a6）→ HEAD `cad2f47`（2026-10-23）
> 上版回滚：docs/release/rollback-plan-0.98.0.md

## 1. 窗口载荷（21 commits，全部已推送 origin/master）

| 任务 | commits | 状态 | 备注 |
|---|---|---|---|
| FEAT-100 | b7be5a5/cc40646/41de8ed | ✅ committed | pi adapter 双桥 + DEC-359 能力升级（Check 28b/loop-claims 根修）+ R2 报告入库 |
| FEAT-101 | 7db915b/a001057 | ✅ committed | chrys 平台适配移除（live 面全清）+ 标题勘误 |
| FEAT-098 | dcf5009 | ✅ committed | cost numeric 等价（精确整数比例）；R3 机录闭环 |
| FEAT-102 | e6e2ca5/f08e0a2/22b6820/98d99c2/2ed8bb4 | ✅ committed | DSH 预设 native 派生（5 commit 链；CI run 39544818165 success；预设丢失事件已判定环境态闭环 EVD-2129） |
| **FEAT-103** | **cad2f47** | ✅ committed（2026-10-23） | owned registration 终态撤销隔离补丁验证：设计终稿 R8（F0189D13）+ 16 份审查报告入库；**11 轮独立审查全 AWN/0**；实现保留隔离副本（.governance ignored 区）；EVD-2130~2139 |
| FIX-449~456 | 8 commits | ✅ committed | CI fixture 自包含（FIX-453×3）/依赖解析权威（FIX-454）/zstandard CI 依赖（FIX-452）/CRLF projection 门（FIX-451）/注入预算（FIX-450）/fixture 版本权威（FIX-449）/本地契约前置拒收（FIX-456） |
| REL-102 M-8 | f392a0b | ✅ | 0.98.0 终账回填（窗口终值 15 commits；fault-injection 承载 8/8） |

## 2. 待判定项（用户决策点）

### 2.1 FEAT-103 承载形式（三选一）
- **a) 导出补丁 diff 入库**：隔离副本 vs 安装态的 diff 导出为 `docs/patches/`（或等价面），0.99 携带可直接应用于 DSH 升级的补丁材料
- **b) 仅验证结论承载**（最小面）：设计终稿 + 审查链已入库（cad2f47）；补丁实现留在隔离副本，待 DSH 上游/后续版本决策——FEAT-102 先例口径（"实际安装与对外提交另行决定"）
- **c) 副本拷贝入产品面**：将隔离副本七文件+测试拷贝入库内产品位置（占仓库空间，需审查副本面入库的产品化处理）

### 2.2 FIX-444 / FIX-445（DEC-342 暂停票）
- 现状：用户裁定"保持原门并暂停"（DESIGN R15 AWN/0 但 implementation_authorized=false；CODE R6 BLOCKED/3）；2026-10-15 定谳顺延 0.99（DEC-358①——"0.99 载荷待实施 pending"）
- 决策：i) 恢复实施链（进入 0.99 载荷，需恢复授权）ii) 继续暂停顺延 0.100（0.99 发布不含，Check 30 [V1]/18e 保持在册披露）iii) 部分恢复（仅 FIX-445 R11 门修复）

### 2.3 在册待收口（P2 排序）
| 票 | 状态 | 0.99 处置建议 |
|---|---|---|
| FIX-447 | 🔄 进行中（LRC 并发窗口间歇性看护） | 看护窗口结果收口或顺延 |
| FIX-455 | 🔄 进行中（WinError5 归因取证） | 取证结论收口（发现即闭环） |
| FIX-448 | 🔄 进行中（§11 三路径待用户裁决；evidence-log 2136KB+ 持续加深，Check 28s/31 FAIL 面） | **建议 0.99 前裁决**（D1 先审 A+C1 为设计+审查共同推荐） |
| FIX-457 | ⏳ triaged（28b projection sync，deps=FEAT-101 已满足） | 0.99 收尾批候选（产品代码票，需 Developer+Reviewer 链） |
| FEAT-099 | 🆕 待实施（未规划版本） | 明确排除出 0.99 |

### 2.4 终笔批候选（文本精度，非阻断）
FEAT-103 R6-P3×2（t-m5 头注释设计锚点版本/M5-REPORT 行号基线口径注）+ R8-P3×2（设计文首枚举/§17 待复审声明句）——建议随 0.99 收尾顺带一批。

### 2.5 FEAT-103 NOT_RUN 5 条（披露形式）
真实 host publish 链 / 物理 storage 注入 / startActivation 全链 / T10 census 全量 / 0.1.x——随 0.99 发布链披露承载（§设计 R8 §16 已成文）；若承载判定选 a)，可另行立项 E2E。

## 3. 版本主题（建议）
**"可信隔离验证与平台收敛"**：DSH 升级适配主线（FEAT-102/103/454/456）+ 平台面收敛（pi 进入/chrys 退出）+ CI 防护网自包含（FIX-449~453）。

## 4. 发布三件套（待范围定稿后）
- 版本 bump 全套（plan-tracker 工作流版本/SKILL frontmatter/CHANGELOG）
- CHANGELOG 0.99.0 条目
- rollback-plan-0.99.0.md
- 发布门：check-release candidate → M-3 双审（CODE+RELEASE）→ GO 终审 → tag+ledger+push
