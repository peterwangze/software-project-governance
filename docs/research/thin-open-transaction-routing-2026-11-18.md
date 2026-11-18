# 从事务发现资源，到用交付结果选路

2026-11-18 · AUDIT-162 · 分析基线 `4264d46`（0.99.0 发布后的工作树）

用户要解决的问题是：一项事务分解出来后，谁会主动去找社区已有的代码、工具、素材或方法，谁会实际试用，下一位执行者又如何知道哪条路有效？本次复核了 Codex 与 DSH，并在治理仓和一个真实 RPG 中各做了一次资源选择。用户确认本轮实施两项小改动，即派发时传递选择与验收方法、能力诊断只采样一次。后续阶段按下面的退出条件决策。

## 断点在何处

| 走过的入口 | 已有能力和可复核的事实 | 对用户交付的影响 |
| --- | --- | --- |
| 任务受理 | FEAT-111 要求 FEAT、DESIGN、RESEARCH、AUDIT 提供 prior art。取 11 月 15–17 日连续的 FEAT-114～118 和 FIX-499～501：五条 FEAT 有记录，其中两条含公开 URL，三条引用宿主 API 或本地材料。三条 FIX 均获豁免。 | 引用能帮助找出处。单凭这一字段无法知道候选经过什么试验，失败的 FIX 也可能比常规 FEAT 更需要找替代路径。 |
| 平台能力诊断 | `capability-context --fail-on-issues` 在这个 Codex 会话的仓库根下报告 `local-governance-repository`，选择本地诊断回退，状态 DEGRADED。命令接受 fixture，没有事务参数。六个适配器的通道声明检查通过。当前会话实际能用网页搜索、GitHub CLI 和已启用的 GitHub 连接器。 | 项目文件描述的是环境线索。要回答“我现在能用什么完成这件事”，还得检查本次会话暴露的工具、权限和可运行入口。历史 headless Codex 和 DSH 的声明不可替代现场探测。 |
| 规划与普通派发 | 主 skill 指向行为协议 M10，已有需要探索、可跳过、受限三种判断。原派发模板却只要求填写“任务详细描述”和“验收标准”。通用短包生成器可保留手工扩展，未把 prior art 转成当前事务的试用方法。 | 上一人即使比较过两个候选，下一人仍容易拿到一句“实现并验证”。在同一份派发内容里交接选择、适用范围和复验入口即可补上这个断点。 |
| DSH 单项直修 | FIX-501 的配对试验从已证故障直达修复。同一候选提交包有 64 个文件，独立重建逐字节相同，Chromium 普通入口五条路径通过。原生 Servo 自验失败，对同一生产包的补测未运行到手册环节；两臂最终都预算暂停。 | 这是保留短路的理由，也说明工具结论必须绑定构建物和入口。该记录证明实际使用了社区工具，未记录当时怎样发现并比较它们。单对样本不能估算平均耗时收益。 |

10 月 AUDIT-158 对 12 项回溯样本判定其中 4 项值得探索，这 4 项均缺少可追溯引用。FEAT-086 的前瞻样本确有两次网页搜索，最后沿用了仓内模式。FEAT-087 的三项样本验证了跳过和受限。10 月 28 日 AUDIT-160 提议在受理时检查 prior art，随后 FEAT-111 按 DEC-377 将它接进 change-triage。把这四段证据合起来，缺的是日常任务中从搜索到选择、从选择到交付的可见链条。仓内记录不足以估算所有历史事务的探索率。[回溯基线](https://github.com/peterwangze/software-project-governance/blob/7b9fd3720376549c53b06d4fc362f5fb0c96e40b/docs/research/thin-open-evolution-phase0-baseline-2026-10-04.md) · [前瞻样本](feat-086-prospective-samples-2026-10-04.md) · [受限样本](feat-087-channel-loss-samples-2026-10-05.md) · [10 月演进论纲](https://github.com/peterwangze/software-project-governance/blob/7b9fd3720376549c53b06d4fc362f5fb0c96e40b/docs/research/audit-160-evolution-thesis-2026-10-28.md)

可复查的实现入口为 [行为协议 M10](../../skills/software-project-governance/references/behavior-protocol.md#m10-主动生态探索协议exp-0105)、[派发模板](../../skills/software-project-governance/references/agent-dispatch-template.md)、[Codex 清单](../../adapters/codex/adapter-manifest.json)、[DSH 清单](../../adapters/dsh/adapter-manifest.json)、[DSH 原生准入](../../lib/dsh-native/goal-admission.js)。FIX-501 的盲验、回放和构建摘要保存在狗粮工作区的 `.governance/incidents/FIX-501-dsh-single-source/report.md`，该目录未随插件分发。

## 两次实际选路

### 在治理仓找出哪些退休候选仍有调用者

10 月的研究已提到 ast-grep。此次通过 GitHub CLI 查到上游主项目、MCP 服务和编辑器扩展，再从本机工具清单找到可直接运行的 ast-grep 0.50.0。上游在 11 月 16 日发布了 0.51.3，主项目为 MIT 许可。任务只需识别 Python 的直接调用，已装 CLI 就能给出带语法位置的结果，版本升级与接入 MCP 对这个问题没有额外收益。[GitHub CLI 的仓库搜索](https://cli.github.com/manual/gh_search_repos) · [ast-grep 用法](https://ast-grep.github.io/guide/quick-start.html) · [上游发行记录](https://github.com/ast-grep/ast-grep/releases/tag/0.51.3)

复现命令可在仓库根目录运行，`ast-grep` 可替换为已安装 CLI 的完整路径。下面是 PowerShell 写法。

```powershell
$engine = 'skills/software-project-governance/infra/verify_workflow.py'
gh search repos ast-grep --owner ast-grep --archived=false --limit 5 --json fullName,url,pushedAt
ast-grep run -l python -p 'check_official_submission_ecosystem($$$ARGS)' --json=stream $engine
ast-grep run -l python -p 'check_codex_desktop_marketplace_e2e_report($$$ARGS)' --json=stream $engine
```

在基线文件中，首个查询命中第 6591、17666、23905 行，分别是历史发布回放、产品完整检查和独立命令。第二个命中第 6480、6589 行。沿调用者与注册表复核后，保留历史回放和显式命令，把 **28m 常规产品完整检查的触发范围**列为下一批可缩减项。快速检查本已跳过 28m，收益只能在产品完整检查中测。直接调用查询也检不出动态分派和外部消费者，不能用零命中证明可删除。

### 为 RPG 的 8×8 中文字格选素材

先按《山海契》的字号和许可需求比较 Fusion Pixel 与 Zpix。前者提供 8px 等宽简体字库，可对齐 Phaser 当前图集。后者按 12px 设计，项目另列商业许可条件。在游戏正常标题入口跑了两组对照，一组沿用原字体栈，另一组优先加载 Fusion Pixel 的固定发行包。另核对同一发行的 12px 简体包，仍缺同一个字。[Fusion Pixel 2026.11.10](https://github.com/TakWolf/fusion-pixel-font/releases/tag/2026.11.10) · [Zpix 固定修订的尺寸和许可说明](https://github.com/SolidZORO/zpix-pixel-font/blob/a4dc7a397322813a6c6aa2c179336974fa3bca30/README.md)

| 试验 | 结果 |
| --- | --- |
| 先核对资源 | 8px 发行 ZIP 的 SHA-256 为 `0e4b2c46135da55271bcd751db87ab4e3d79b95c26852e93f324003efd531a61`。包内含 OFL 许可及来源说明。简体 WOFF 为 582,516 字节。 |
| 查覆盖 | fontTools 4.66.1 读取字体 cmap。标题与提示的 43 个去重字符均有映射。91 条对话合并说话人、正文、分支选项，剔除换行后得到 569 个不同字符，覆盖 568 个，缺“䨼”（U+4A3C）。 |
| 在目标环境试用 | Playwright 1.62.0 驱动 Edge 157.0.4341.46，从同一生产包普通入口打开 1280×720 标题画面。候选臂在隔离浏览器响应中加载字体并替换六处字体族，两臂均观察到标题图集绘字，脚本异常均为零。前后生产包入口 JS 的 SHA-256 均为 `986a546d1d7399573a780ebd772cb9d156c77afe91a41741711134d45944e88d`。 |
| 对照原始目标 | 对同一 569 字，以实际字体栈在 8×8 Canvas 左上绘制，逐像素按 alpha ≥128 取 64 位掩码并按掩码分组。原栈有 568 种掩码，碰撞“己／已”；候选加回退有 567 种，碰撞“—／一”“闲／闹”。 |

**本配置暂缓采用。** 最新发布的素材能加载，字号、许可证和覆盖也有据可查，真正改变选择的是游戏里的异字同形。若设计者调整字格，再以原始标题和对话进行玩家辨读测试。当前数据只衡量该环境的覆盖与位图可区分性，玩家可读性仍待盲评。此试验由本次 Codex 调研发起，DSH 的 FIX-501 历史修复针对另一项事务。复跑完整画面需要原游戏输入和相应系统字体。[本次采样原始摘要](thin-open-rpg-font-probe-2026-11-18.json)

公开可复验的最小部分是确认候选字库是否含有这些字。取同一固定发行包并将其保存为 `font.zip`，在已有 fontTools 的环境运行以下代码，依次得到 True、True、True、False。完整对话输入 `src/data/dialogues.json` 的 SHA-256 为 `0c2f6a40b8d5a529bd60f8fc9d71c29990a176f4e873cb0a09716d53bdd9987f`。[8px 等宽 WOFF 发行包](https://github.com/TakWolf/fusion-pixel-font/releases/download/2026.11.10/fusion-pixel-font-8px-monospaced-otf.woff-v2026.11.10.zip)

```python
from zipfile import ZipFile
from fontTools.ttLib import TTFont

with ZipFile("font.zip") as bundle:
    with bundle.open("fusion-pixel-8px-monospaced-zh_hans.otf.woff") as font:
        cmap = TTFont(font).getBestCmap()
        print([ord(character) in cmap for character in "山海契䨼"])
```

## 治理该持有什么

| 核心职责 | 核心保留的决策与事实 | 具体工作由谁承担 |
| --- | --- | --- |
| 意图识别、事务分解 | 保存原话、目标用户、可观察的完成条件，将验收缺口分成可独立验证的事务 | 用户裁定目标与重要取舍，领域执行者解释具体技术条件 |
| 路径规划、落盘契约 | 选择下一步，在现有工作包与证据中留下选择依据、制品和验收引用；同一事实只有一个权威写入点 | 宿主处理身份、权限、工具目录、沙箱与调度；项目仓维护领域工件 |
| 循环演进、过程看护 | 用交付结果决定继续、换路或恢复。保留预算、独立验收、可回滚和用户数据保护 | 浏览器、编译器、CI、专用测试或人工评价分别给出自己能观察到的证据 |
| 主动探索、兼容开放 | 按事务缺口判断何时探索，要求使用前有可复核的适配证据，并把有效范围传给下一人 | 宿主和开放社区维护搜索、索引、插件、工具、素材、领域方法和版本 |

资源供给端可替换。Agent Skills 的元数据支持按需发现和加载方法；MCP Registry 可提供服务器线索；连接后的 MCP 服务按协商能力用 `tools/list` 枚举当前工具。仓库与素材从项目上游或发行页核对版本、许可和适用条件。没有相应服务时，仍可用本地命令、项目锁定版本、现有文档或授权人工复核。这些是适用的渠道，无须将目录抓取器、协议客户程序、字体或游戏验收脚本装进治理核心。[Agent Skills 规范](https://agentskills.io/specification) · [MCP Registry](https://registry.modelcontextprotocol.io/docs) · [MCP 工具能力协商与枚举](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)

## 从一笔事务走到下一次决策

1. **分解后确定缺口。** 以“玩家能区分对话用字”为例，已有验收必须落在实际字格和文本上。先看本次宿主工具、已有项目依赖和最近一次同条件回执。入口、版本、权限、产物或验收目标变化，原回执的适用性需要重查。
2. **在承诺方案前，用任务预算找候选。** 复用 M10 的五项触发条件。若路径成熟，给出现有回执便继续。需要探索时，用宿主已授权渠道核对当前上游，再比较足以区分候选的约束。网络受限时记录尝试、可用的本地替代和仍未知的部分。只读发现与引入依赖各按已有权限执行。
3. **把选择放进现有派发。** 在任务描述留下候选来源、实际试验与选用或淘汰原因；仍待试用时写明由谁在何处试。在验收标准指定工件、正常入口和能证实目标的观察。领域执行者在获准范围内使用选中的工具，交回结果。沿用 M10 的 exploration 和现有证据引用，续跑直接消费已有结果。
4. **按结果重排。** 用户验收已满足就收口，试用失败就回到对应缺口。DSH 已证实且已授权的单项直修继续走原生工作包；仅在现有手段失效、环境改变或新验收缺口出现时重选。成熟事务无需反复搜索，失败候选也可避免重复试用。

例如，这次字体试验交给下一位设计者的指令可以只有两句：“保持当前 8×8 布局，研究如何让玩家区分‘己／已’。Fusion Pixel 2026.11.10 已在同一生产包试过，增加了‘闲／闹’的碰撞；若改字格，请用同一对话集复测，再安排正常对话入口的玩家辨读。”原交付目标、被淘汰的路径和新方案要通过的验收都在其中。

## 减法清单与推进顺序

10 月快照记录注册表 98 个命令、73 个检查段。此次基线的同口径值为 **109 / 74**（`infra/registry.py` 的 `command_keys()`、`segment_ids()`），主验证文件为 **28,543 物理行**。这是维护面大小；删行或增加检查通过率都不能替代用户结果。10 月点名的 28e、28m、Desktop Marketplace E2E 函数各仍有消费者。另方面，FEAT-101 已退出 chrys 适配器，说明责任能真实退出。历史报告中的 E2E Python 大副本受 Git 忽略，当前仅 15 个跟踪文件位于样例树内，清本地生成物不会减少发布产品职责。

| 顺序与负责人 | 本步交付 | 退出证据与回退 |
| --- | --- | --- |
| 本轮 · 治理开发与独立审查 | FEAT-119 在既有派发字段交接选择和复验方法。FIX-502 将两个诊断 CLI 的展示和校验绑定同一份采样，保留独立按 root 检查的调用方式。 | 覆盖需探、跳过、受限与待试用，检查模板占位符和旧入口。用两次读取结果不同的反例验证 CLI 错误如实返回，校验调用次数 2→1。两处可单独回滚。 |
| 下一批 · Codex、DSH 项目执行者与独立验收者 | 先用正常任务入口做前瞻配对，覆盖一次新资源实际采用、一次试用淘汰、一次受限、一次成熟直修。至少含两个宿主和两个事务类别；在接到适合任务时采样。 | 旧路径和候选路径用相同输入、权限、预算和验收，留下从派发到最终工件的引用。记录首次有效操作用时、交付是否通过、额外治理读取和未知样本数。仅比较同质量结果的时间/成本。若模板未被消费，先修实际交接点；不扩平台或强制联网。 |
| 随后 · 产品检查维护者 | 针对 28m 做同输入的完整检查对照。保留独立 CLI 与 0.46.0 发布回放；核实活跃使用者与唯一的错误声明保护，确认承接后再收窄普通产品检查。 | 正例、故意错误的官方提交声明、旧版本回放各跑一遍，保留旧输出和新输出。若有消费者失去独有保护，维持原触发或恢复单项变更。28e 仍被发布准备消费，另案处理。 |
| 再后 · 领域维护者与架构审查 | 将 `core/lifecycle-registry.json` 中的十章游戏样例与通用迁移语义分开评估。旧项目缺 runtime 时迁移预览会引用样例；先为该入口找到承接者。锁、归档、工作流发布也逐项核实边界。 | 选真实旧项目与无游戏数据的项目，比较迁移预览、实际回滚与原数据校验。独有保护、消费者、替代方案和恢复证据齐备后，再逐项裁定退出。既有 DEC-312 的兼容观察窗与后续版本安排仍属待裁决事项。 |

配对时从收到同一事务起计时，到第一次直接作用于该验收缺口的查询、复现或试用为止。没有该动作的样本记录为“未到达”，另记暂停原因。交付通过率以全部受理样本为分母，单列暂停、失败和结果未知。扩大到新平台的依据是该平台能用自己的工具完成同一份事务契约，并交回可复验的用户结果。探索次数、外链数和插件安装数均不足以独立作出这个决定。
