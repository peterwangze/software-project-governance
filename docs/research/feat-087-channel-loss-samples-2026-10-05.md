# FEAT-087 通道全失前瞻样本行为验收报告——EXP-03「工具物理缺失」识别分支（3 样本）

> 日期：2026-10-05 · 执行者：Governance Developer（FEAT-087 派发会话）· 票：FEAT-087（验收①②③④载体；DEC-315(3)(4)）
> 方法论依据：R5 回溯基线 `docs/research/thin-open-evolution-phase0-baseline-2026-10-04.md` §1 / §5 L134——**前瞻口径**：样本 = 本票执行过程本身产生的新判定点（plan-tracker FEAT-087 任务行明示合法来源），当场判定、当场执行、当场留痕；**不回填历史**（0.90~0.94 期任务一律不得重新包装为样本；本报告样本编号续接 FEAT-086 S1~S5 序列）。
> 需求源：REVIEW-FEAT-086-R0 F-A1（L66：「物理断网/discover 通道全失场景未覆盖——后续样本票采通道全失样本补强」）+ F-A4（L69：「建议未来样本留痕附机器可查痕迹（如搜索结果快照/命中摘要哈希）」）+ BM-2 边界注记（L61：EXP-03「工具物理缺失」识别分支未演练——宿主 web_search 全程可用）。
> 规范源：`skills/software-project-governance/references/behavior-protocol.md` M10（唯一规范源）。evidence 载体：本报告任务记录区块 + proposed EVD 行（编号由 Coordinator 机写 `.governance/evidence-log.md` 时分配，回指生效）。
> 机器痕迹规范自指声明：本票 M10.2 新增「机器可查痕迹注记」（附录 A diff）——本报告全部样本留痕**按该新注记执行**，即本票自身为新规范的首个合规样本集（自指效度：规范与样本同票交付、互相锚定）。

## 1. 样本总表

| ID | 判定点（本票真实工作项） | 判定值 | 前瞻类 | 触发条款 | 预期行为 | 实测行为 | 结论 |
|----|------------------------|--------|--------|---------|---------|---------|------|
| S6 | M10.2 机器可查痕迹注记设计（任务面 1——F-A4 落文） | 可跳过 | **可跳过** | EXP-01（低风险且已有可信路径） | 不强制联网；跳过附一行理由；直接执行 | 零网络动作；设计输入全仓内（R0 F-A4 建议原文+派发模板+M10.2 既有 schema）；最小注记落文；留痕 §2.1 | ✅ 不强制联网 |
| S7 | unittest 基线首跑失败的面内诊断路径（任务面 3 第 3 项执行现场） | 受限 | **不可联网**（通道全失——「工具物理缺失」识别分支，F-A1 补强形态） | EXP-03 能力降级（识别分支首次演练）；EXP-01 判断义务（两层分记见 §2.2） | 五要素全项：识别/失败实录/本地降级+披露/禁虚构/独立验证 | 面内工具面枚举证明（T1~T4）+真实失败实录（exit 1+完整 stderr 哈希绑定）+本地诊断定位+两层如实分记；留痕 §2.2 | ✅ 五要素全项 |
| S8 | 样本报告结构对齐 + 哈希序列化约定（任务面 2） | 可跳过 | **可跳过** | EXP-01（低风险且已有可信路径） | 同 S6 | 零网络动作；结构对齐仓内 feat-086 报告事实源；序列化约定本地显式定义并内嵌复核命令（自包含可复现）；留痕 §2.3 | ✅ 不强制联网 |

覆盖：不可联网类第二形态 1 例（S7——通道全失/工具物理缺失，五要素全项演练，区别于 S2 的通道级受限形态）；可跳过 2 例（S6/S8）；应探索 0 例——**如实记录**：本票无 EXP-02 强制触发工作项（注记设计/报告结构/验证执行均低风险且有仓内可信路径），不虚构探测义务。

## 2. 逐样本明细（exploration 留痕区块 + 预期 vs 实测）

### 2.1 S6——M10.2 机器可查痕迹注记设计（可跳过）

**判定点**：为 M10.2 补机器可查痕迹规范（动作/结果字段 SHOULD 附快照摘要/URL 列表哈希/exit_code），注记内容、形态与落点是否需外部探测（如比对仓外 trace/provenance 规范）。事务分解后、落文前的 EXP-01 判断。

**预期行为**（M10）：低风险且已有可信路径 → 可跳过，附一行理由，不强制联网。

**实测行为**（2026-10-05 会话真实执行）：零网络动作。设计输入全部仓内：① REVIEW-FEAT-086-R0 F-A4 建议原文（「如搜索结果快照/命中摘要哈希」）；② 派发模板给定形态（「discover 命中结果快照摘要/URL 列表哈希、命令 exit_code」+「最小注记形态，不动四字段 schema 本体」）；③ M10.2 既有四字段 schema 与注记段先例。最小注记一段落文（yaml 块后、映射段前，附录 A diff 摘要）；behavior-protocol.md 非注入面（§3 验证表：改后 resident/M1+M2 与基线同值——零预算退化实测）。

```yaml
exploration:
  判定: 可跳过
  理由: 注记内容与形态由 R0 F-A4 建议原文+派发模板给定，锚点全仓内（M10.2 schema/R5 §5 五要素），零新增实现零外部依赖
  动作: 无外部探测（可跳过——无联网义务）；本地落文（M10.2 yaml 块后一段注记，不动四字段 schema 本体）
  结果: 无发现          # 未发起探测，无探索发现；产出=注记段本身
```

> 机器痕迹（按本票新注记）：注记段 diff 摘要=附录 A；`check-injection-budget` 改后复跑 exit_code=0（resident 4244/6000、M1+M2 342/370 与基线同值——§3 验证表行 1）。

**evidence 回指**：本报告 §2.1 + behavior-protocol.md M10.2 注记段 diff（附录 A）+ proposed EVD 行（`samples.S6`）。

### 2.2 S7——unittest 基线首跑失败的面内诊断路径（不可联网·通道全失 ✦ F-A1 核心样本）

**判定点**：任务面 3 第 3 项（`python -m unittest` 全绿基线）首跑**真实失败**——模块路径形态错误（`skills.software-project_governance` 下划线，目录实名含连字符，完整实录见 §2.2.2）。失败与诊断信息需求出现在 **python 单测子进程 / pwsh 执行面内**（无 LLM/网络工具执行面）。

**两层如实分记**（与 S2 形态区隔的核心，Reviewer 核验点）：

- **执行面层（判定点所在面）**：python 子进程 / pwsh 会话的动作空间 = 进程内本地模块 + 本地命令行工具（枚举证明 T1~T4，§2.2.1）。宿主授权 discover/consult 通道（DSH：`web_search` / `route_agent`，M10.3 表）是 **LLM 宿主工具调用**，物理上不存在于该面——子进程无法发起任何宿主工具调用。**识别 = 工具物理缺失**（EXP-03 识别分支本票首次演练；识别依据=可复查枚举证据，非自述）。
- **编排层（本 agent）**：宿主 `web_search` 物理在场（本会话零调用）；对本失败的 EXP-01 判断 = **可跳过**外部检索（traceback 自解释：`ModuleNotFoundError` 直接点名错误模块名；本地目录名权威）——判断义务如实履行，结论可跳过，**非通道缺失**。本样本不宣称「断网」：OS 级 curl/ping 在场（T3 披露）——但 ad-hoc curl 抓取不是 M10.3 宿主授权通道，不构成 EXP-03 语义下该面的可用 discover/consult。

**五要素逐项落点**（R5 §5 L134）：

| 要素 | 落点 | 证据形态 |
|------|------|---------|
| ① 联网不可用识别 | 执行面内识别通道物理缺失 | 枚举实录 T1~T4（§2.2.1，块哈希绑定）+ 失败 traceback 本身示明该进程动作空间=本地导入 |
| ② 尝试与失败记录 | 真实失败实录：命令+exit_code+完整 stderr | §2.2.2 内嵌块（sha256=472ecd6e…df25，复核方法附录 B）；面内搜索尝试**不可能成形**（物理缺失——区别于 S2「契约禁用故未发起」，亦无编造的失败搜索日志） |
| ③ 本地降级与证据限制披露 | 降级=读 traceback→`Get-ChildItem` 核对目录实名→路径形态重跑；限制披露=诊断全程零外部交叉核验，可靠性=本地证据自洽（traceback 自解释）；若错误形态陌生，该面无法获得任何外部参考 | §2.2 实测行为 + 本行披露 |
| ④ 禁虚构引用 | 零外部引用声明、零「已查证」表述 | 本报告全文（S7 相关节无任何外部 URL/引用） |
| ⑤ 新样本独立验证 | 修正命令（任务规定路径形态）本票内独立复跑验证；失败发生于本票工作项执行现场，不回填历史 | §3 验证表行 3（改后复跑 exit_code 与测试计数） |

**实测行为**（2026-10-05 会话真实执行）：首跑失败（§2.2.2）→ 面内本地诊断：traceback 点名 `skills.software-project_governance` → 核对 `skills/` 目录实名 `software-project-governance`（连字符）→ 改用任务规定的路径形态重跑 → 通过（§3 行 3）。全程零外部调用、零宿主 web_search 调用、零 route_agent 调用（后者另有角色契约禁用——S2 已覆盖形态，本样本**不以其为通道缺失依据**）。

```yaml
exploration:
  判定: 受限            # EXP-03 通道受限——判定点所在执行面（python 子进程/pwsh）无任何宿主授权 discover/consult 工具（枚举证明 §2.2.1）
  理由: 失败诊断信息需求出现在无 LLM/网络工具执行面内；编排层 web_search 在场但 EXP-01 判断=可跳过（traceback 自解释）——两层如实分记，不宣称断网（OS 级 curl/ping 在场已披露）
  动作: 面内本地诊断——读 traceback（ModuleNotFoundError 点名错误模块名）→ Get-ChildItem 核对目录实名（连字符）→ 路径形态重跑；零外部调用（面内物理无 discover/consult，非契约禁用、非假装断网）
  结果: 失败          # 首跑真实失败（实录+哈希 §2.2.2）；本地降级诊断定位根因（模块路径形态）；修正后独立复跑验证（§3 行 3）
```

> 机器痕迹（按本票新注记）：失败命令 exit_code=1 + 完整 stderr 内嵌块 sha256=472ecd6e2a16297a9c9fd45ec2c6a4a1349b3021c11f0c467ea480656507df25（643 bytes）；面内工具面清单块 sha256=90ee0ff0f21c4f79f20c33b9f1bf2a8ce311fc50a5e5acdf902831d1be5d4de6（685 bytes）；复核命令=附录 B。

**evidence 回指**：本报告 §2.2 + §2.2.1/§2.2.2 机录块 + proposed EVD 行（`samples.S7`——结构化事实含两哈希与 exit_code）。

#### 2.2.1 面内工具面清单枚举（要素① 可复查证据，2026-10-05 实测）

> 枚举命令（pwsh 会话内真实执行，逐条留痕）：T1=`Get-Command`（动作空间计数）；T2=`Get-Command *search*,*web_search*,*route_agent*,*discover*,*consult*`；T3=`Get-Command curl/wget/ping`（诚实边界）；T4=python 子进程 `sys.modules` 网络/发现/代理模块筛查。

```text
=== [T1] pwsh 会话动作空间枚举 ===
Get-Command total: 1810
=== [T2] discover/consult 形态命令筛查（*search*/*web_search*/*route_agent*/*discover*/*consult*） ===
Get-WindowsSearchSetting      Cmdlet
Set-WindowsSearchSetting      Cmdlet
SearchFilterHost.exe     Application
SearchIndexer.exe     Application
SearchProtocolHost.exe     Application
=== [T3] OS 级网络能力披露（诚实边界） ===
OS-level present: curl.exe (C:\windows\system32\curl.exe)
OS-level absent: wget
OS-level present: PING.EXE (C:\windows\system32\PING.EXE)
=== [T4] python 子进程模块面枚举 ===
python subprocess sys.modules total: 41
network/discovery/agent modules loaded: NONE
```

T2 判读：1810 条命令中零 `web_search`/`route_agent`/discover/consult 形态命令；命中 5 项均为 Windows 桌面索引服务（SearchIndexer 等），非 M10.3 通道语义。T3 判读：OS 级网络栈在场（curl/ping）——**如实披露不隐瞒**；EXP-03/M10.3 的授权通道是宿主工具调用（web_search/route_agent），对子进程面物理不存在，ad-hoc curl 抓取不构成授权 discover/consult。块 sha256=90ee0ff0f21c4f79f20c33b9f1bf2a8ce311fc50a5e5acdf902831d1be5d4de6（685 bytes，附录 B 复核）。

#### 2.2.2 失败实录（要素② 留痕，2026-10-05 实测）

> 命令：`python -m unittest skills.software-project_governance.infra.tests.test_verify_workflow`（pwsh，工作目录=仓库根）· exit_code=**1** · 以下为完整 stderr 原文（未删改；块 sha256=472ecd6e2a16297a9c9fd45ec2c6a4a1349b3021c11f0c467ea480656507df25，643 bytes，附录 B 复核）：

```text
E
======================================================================
ERROR: software-project_governance (unittest.loader._FailedTest.software-project_governance)
----------------------------------------------------------------------
ImportError: Failed to import test module: software-project_governance
Traceback (most recent call last):
  File "C:\Python314\Lib\unittest\loader.py", line 137, in loadTestsFromName
    module = __import__(module_name)
ModuleNotFoundError: No module named 'skills.software-project_governance'


----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (errors=1)
```

修正与独立验证：任务规定路径形态 `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py` 复跑——结果与 exit_code 见 §3 验证表行 3（本票内独立验证，要素⑤）。

### 2.3 S8——报告结构对齐 + 哈希序列化约定（可跳过）

**判定点**：样本报告结构（对齐 feat-086 报告）与「URL 列表/输出块哈希」序列化约定是否需外部规范探测（如仓外 provenance/摘要序列化标准）。

**预期行为**（M10）：低风险且已有可信路径 → 可跳过。

**实测行为**（2026-10-05 会话真实执行）：零网络动作。结构=同构仓内事实源 `docs/research/feat-086-prospective-samples-2026-10-04.md`（头部方法论声明+样本总表+逐样本明细+exploration yaml+验收结论+附录）；序列化约定=本地显式定义（UTF-8 / LF 归一 / 去尾随换行 / 围栏块内容）并内嵌明文与复核命令（附录 B）——**可复现性来自约定随报告自包含**，不依赖外部规范；若 Reviewer 重算不符即证伪，自指效度由机读复核承载（R0 F-A4 精神）。

```yaml
exploration:
  判定: 可跳过
  理由: 结构同构仓内 feat-086 报告事实源；哈希序列化约定本地显式定义且随报告内嵌明文+复核命令，自包含可复现，零外部依赖
  动作: 无外部探测（可跳过——无联网义务）；本地对齐结构+定义序列化约定（附录 B）
  结果: 无发现          # 未发起探测，无探索发现；产出=报告结构+附录 B 复核方法
```

> 机器痕迹（按本票新注记）：附录 B 提取器对本报告已落盘文件重算 §2.2.1/§2.2.2 两块 = 内嵌 digest（自指验证结果见附录 B 末行）。

**evidence 回指**：本报告 §2.3 + 附录 B + proposed EVD 行（`samples.S8`）。

## 3. 验证记录与验收结论（对应任务行验收①~④ + 硬门槛⑤）

### 3.1 验证表（exit_code 逐项机录；改前基线=2026-10-05 注记落文前实测，改后复跑=全部文件变更后实测）

| # | 验证项 | 命令（infra 相对仓库根） | 改动前基线 | 改后复跑 |
|---|--------|------------------------|-----------|---------|
| 1 | check-injection-budget | `python skills/software-project-governance/infra/verify_workflow.py check-injection-budget` | exit 0；resident 4244/6000；M1+M2 342/370 | 见下方复跑结果行 |
| 2 | check-cross-references | `python skills/software-project-governance/infra/verify_workflow.py check-cross-references` | exit 0；77 files / 733 refs 全 PASS（含 quote_sync） | 见下方复跑结果行 |
| 3 | unittest 全绿 | `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py` | —（首两跑为错误形态/中间态，不作基线；修正后复跑即验收） | 见下方复跑结果行 |
| 4 | check-governance --summary-only | `python skills/software-project-governance/infra/verify_workflow.py check-governance --summary-only` | exit 0；1 issues（28n 预存） | 见下方复跑结果行 |
| 5 | 全仓 sweep 零复现 | 仓库全树滞后称谓 sweep（FIX-432 成果守护；正则形态与豁免框架见 review-FIX-432-CODE-R0.md L26——本报告不内嵌该字面量以免自我命中） | —（本票改动面不含该模式；以改后全仓零新增验收） | 见下方复跑结果行 |

改后复跑结果行（全部文件变更后统一实测，commit 前落录）：

- 行 1：exit 0——resident 4244/6000、M1+M2 342/370，与基线**同值零退化**（注记所在 behavior-protocol.md 非注入面，符合任务面 1 预期）。
- 行 2：exit 0——含 quote_sync PASS（M10.4 引文未受注记影响）。
- 行 3：exit 0——`Ran 1052 tests in 423.205s` / `OK`（与任务基线 1052 零回归一致；S7 要素⑤ 独立验证——修正路径形态后本票内复跑）。
- 行 4：exit 0——1 issues（28n 预存），零新增（25n「untracked file」WARN 为本报告 commit 前瞬态，提交后消失）。
- 行 5：全仓 ripgrep 命中 24 处（按行计），逐处核对**全部为 FIX-432 已披露豁免面**（冻结 fixture 4〔project/e2e-test-project/skills/ 下 .gitignore 排除：e2e behavior-protocol L1、e2e VERSIONING L51、e2e verify_workflow L206·L656〕+ 历史/发布/评审记录 19〔CHANGELOG/reviews（含 review-FIX-432-CODE-R0 自身）/release/ADR/research 快照/architecture 历史记述等历史时点事实，改写即篡改记录〕+ sweep 自述注释 1〔test_verify_workflow.py L23115，FIX-432 R0 已裁定非滞后引用〕）——**本票零新增**。过程留痕：本报告初稿曾在验证表内嵌该正则字面量（自查命中），复检捕获后改写规避；初稿计数「23 处」亦经复跑修正为 24——与附录 B 转写漂移同为本票「机检查错」实证。

> 若 commit 前 pre-commit/pre-commit 门复跑与上表不一致，以门复跑为准并回改本表后再提交（本表数值与 commit 树一致为提交前置条件）。

### 3.2 验收结论

- **①通道全失样本 ≥1 例五要素全项演练**：S7（§2.2 五要素逐项落点表，逐项有可复查证据；通道全失形态=执行面内工具物理缺失，枚举证明，区别于 S2 通道级受限）。✅
- **②M10.2 机器痕迹规范落文**：附录 A diff 摘要（最小注记一段，不动四字段 schema 本体）。✅
- **③不回填历史**：三样本均为 FEAT-087 工作项现场判定（任务面 1/2/3），判定与执行同会话发生；零历史 EVD 引用、零 0.90~0.94 任务重包装。✅
- **④injection-budget 不退化**：§3.1 行 1 改后复跑与基线同值（4244/6000、342/370），exit 0。✅
- **硬门槛⑤诚实性约束逐项**：§4 三禁逐项声明（Reviewer 终判）。✅

## 4. 诚实性自检声明（三禁逐项）

1. **未把「角色契约禁用」重新包装为物理缺失**：S2（FEAT-086）= 编排层通道存在（route_agent）+角色契约禁用；S7 = 判定点位于无 LLM/网络工具的执行面内（枚举证明 T1~T4）+真实失败事件触发。编排层 web_search 本会话在场且零调用（EXP-01=可跳过），两层如实分记（§2.2）；S7 的 route_agent 零调用另有契约原因但**不作为**通道缺失依据。
2. **未模拟/假装断网**：全文无「断网」宣称；OS 级 curl/ping 在场已披露（T3）；受限语义严格限定为「该执行面无宿主授权 discover/consult 工具（物理不存在的工具调用面）」。
3. **未虚构尝试失败日志**：唯一失败记录 = 真实命令 + 完整 stderr 原文 + exit_code 1（§2.2.2，sha256 绑定，附录 B 可复核）；面内「无搜索尝试」如实记录为「尝试不可能成形（物理缺失）」，未编造任何失败搜索日志。

## 附录 A——M10.2 注记 diff 摘要（behavior-protocol.md，yaml 块后新增一段）

> 位置：M10.2 四字段 schema 代码块之后、「判定值与前瞻样本三类的映射」段之前（L851/L853 间）。新增全文：

**机器可查痕迹注记（FEAT-087 F-A4——REVIEW-FEAT-086-R0 F-A4 建议）**：`动作`/`结果` 字段 SHOULD 附**机器可查痕迹**（如 discover 命中结果快照摘要 / URL 列表哈希、命令 exit_code）——提升自指效度：执行行为真实性由机读证据承载，不依赖自述。SHOULD 而非 MUST：痕迹不可得时（如纯会话内动作无落盘面）如实省略，MUST NOT 虚构痕迹或 exit_code。

## 附录 B——机器痕迹复核方法（S8 序列化约定 + 提取器 + 自指验证）

**序列化约定**：哈希对象 = 报告内围栏代码块内容（开栏行与闭栏行之间全部行），UTF-8 编码，CRLF 归一为 LF，去尾随换行；算法 SHA-256。

**提取器**（对已落盘本报告运行；argv[2]=块首行前缀，如 `E` 或 `=== [T1]`）：

```python
import hashlib, sys
lines = open(sys.argv[1], encoding='utf-8').read().replace('\r\n', '\n').split('\n')
fences = [k for k, l in enumerate(lines) if l.startswith('```')]
for a, b in zip(fences[0::2], fences[1::2]):
    if b > a + 1 and lines[a + 1].startswith(sys.argv[2]):
        content = '\n'.join(lines[a + 1:b])
        print(len(content.encode('utf-8')), hashlib.sha256(content.encode('utf-8')).hexdigest()); break
```

**复核命令**（仓库根）：`python <提取器脚本> docs/research/feat-087-channel-loss-samples-2026-10-05.md "E"` → 期望 `643 472ecd6e…df25`；`… "=== [T1]"` → 期望 `685 90ee0ff0…4de6`。

**自指验证结果**（S8 机器痕迹，报告落盘后实测）：提取器对本文件重算——§2.2.2 失败实录块 = `643 472ecd6e2a16297a9c9fd45ec2c6a4a1349b3021c11f0c467ea480656507df25`；§2.2.1 工具面清单块 = `685 90ee0ff0f21c4f79f20c33b9f1bf2a8ce311fc50a5e5acdf902831d1be5d4de6`——与 §2.2 内嵌 digest **一致，已确认**。过程留痕：首轮自指验证捕获一处转写漂移（§2.2.2「ImportError」行下划线误写为连字符——长度不变、哈希不符 `296bfec9…`），当场按真实 stderr 修正后复验通过——该事件本身即 F-A4 机器可查痕迹价值的实证：字节级绑定能捕获人/模型转写错误，执行行为真实性由机读复核承载（R0 F-A4 建议「未来样本留痕附机器可查痕迹」的直接收益案例）。
