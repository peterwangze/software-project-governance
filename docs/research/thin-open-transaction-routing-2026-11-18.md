# 两次社区资源试用的验收记录

2026-11-18，AUDIT-162。在治理仓和《山海契》分别试用社区代码工具与字体，前者定位实际调用者，后者用生产包的真实字格决定是否采用素材。Codex 与 DSH 的诊断、当时的派发范围和完整计划可按原行号在固定提交回读。当前职责与下一轮采样方法见演进页。[完整研究与当时的路线](https://github.com/peterwangze/software-project-governance/blob/3565407cb8622942939259c904ac6bace475b3c3/docs/research/thin-open-transaction-routing-2026-11-18.md) · [工作流的职责与演进方向](../governance/evolution.md)

## 用 ast-grep 核对退休候选的调用者

10 月的研究已提到 ast-grep。此次通过 GitHub CLI 查到上游主项目、MCP 服务和编辑器扩展，再从本机工具清单找到可直接运行的 ast-grep 0.50.0。上游在 11 月 16 日发布了 0.51.3，主项目为 MIT 许可。任务只需识别 Python 的直接调用，已装 CLI 就能给出带语法位置的结果，版本升级与接入 MCP 对这个问题没有额外收益。[GitHub CLI 的仓库搜索](https://cli.github.com/manual/gh_search_repos) · [ast-grep 用法](https://ast-grep.github.io/guide/quick-start.html) · [上游发行记录](https://github.com/ast-grep/ast-grep/releases/tag/0.51.3)

检出分析基线 `4264d46` 后，在该工作树运行以下 PowerShell 命令。行号以这个版本为准。

```powershell
$engine = 'skills/software-project-governance/infra/verify_workflow.py'
gh search repos ast-grep --owner ast-grep --archived=false --limit 5 --json fullName,url,pushedAt
ast-grep run -l python -p 'check_official_submission_ecosystem($$$ARGS)' --json=stream $engine
ast-grep run -l python -p 'check_codex_desktop_marketplace_e2e_report($$$ARGS)' --json=stream $engine
```

在基线文件中，首个查询命中第 6591、17666、23905 行，分别是历史发布回放、产品完整检查和独立命令。第二个命中第 6480、6589 行。对照注册表后，研究者保留历史回放与显式命令，把常规产品完整检查列为待复验的消费者。动态分派与外部调用者还需沿其入口核实。

## 为 RPG 的 8×8 中文字格选素材

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
