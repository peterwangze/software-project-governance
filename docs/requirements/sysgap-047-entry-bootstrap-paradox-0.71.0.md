# SYSGAP-047: resolve_entry.py 入口确定性——bootstrap 悖论与真实环境不可发现性

> **状态**: 分析完成，待修复（FIX-222）
> **触发**: 用户反馈"真实环境直接找不到这个脚本" + "偶尔会卡住"
> **关联**: AUDIT-139（入口路径可发现性审计）, FIX-222（bootstrap prose 修正）, DEC-096（resolve_entry.py 双 root 模型）

## 1. 问题定位

### 1.1 bootstrap 悖论（CONFIRMED）

`AGENTS.md:5` 的"第一动作"说：
> 运行 `python <plugin_home>/infra/resolve_entry.py --json`（`<plugin_home>` 由该脚本自定位）

这是**鸡生蛋问题**：`<plugin_home>` 是占位符，未定义。要运行 resolve_entry.py 获取 plugin_home，必须先知道 plugin_home 才能构造命令行路径。resolve_entry.py 通过 `Path(__file__).resolve().parent.parent` 自定位 PLUGIN_HOME（行 45），但 `__file__` 自定位只在解释器成功打开文件后生效——需要命令行上已有完整路径。

下游所有命令（AGENTS.md 行 101/124/129/135/136/177；governance-init.md 行 202/327/346/369/374/487/498/596/615/638）都写"<plugin_home> 来自 resolve_entry.py"——整个 bootstrap 链依赖解析第一个占位符，但它从未被定义。

### 1.2 真实环境路径不存在（CONFIRMED）

- **dev 环境**（dogfooding）：plugin tree 在 `skills/software-project-governance/infra/resolve_entry.py`，repo root == host project root，相对路径能工作。
- **marketplace 安装环境**：plugin 在 cache 路径（如 `C:\Users\...\plugins\cache\...\skills\software-project-governance\infra\resolve_entry.py`），host 项目无 `skills/` 目录。从 host cwd 运行 `python skills/software-project-governance/infra/resolve_entry.py` 失败（file not found）。
- **e2e fixture**：plugin tree 被 vendored 在 host 内（`project/e2e-test-project/skills/...`），AGENTS.md 投影简化为"加载 SKILL.md"，回避了 resolve_entry.py 命令——这也是它能工作的原因。

### 1.3 "偶尔卡住"（MISATTRIBUTED — 可能误归因）

resolve_entry.py 是纯 stdlib（行 34-40：argparse/json/os/re/sys/datetime/pathlib），**零** subprocess/git/network 调用。hooks_installed 检查仅 3 个 `is_file()` stat 调用（行 264/276-278），不可能卡住。

实际卡顿来源可能是：
1. **后续 verify_workflow.py**（20k 行 God Module，check-governance 耗时 ~3min）——LLM 可能误归因到 resolve_entry.py（bootstrap 序列第一个命令）
2. **1.1 的 file-not-found** 被 LLM 重试，感知为卡住
3. OS 级 stat/getcwd 慢（网络挂载/大 worktree）

## 2. 根因

DEC-096 设计了 resolve_entry.py 双 root 模型（PLUGIN_HOME 从 `__file__` 推导；HOST_PROJECT_ROOT 从 cwd/平台/`--project-root` 解析），消除了 WORKFLOW_HOME 环境变量依赖。但 bootstrap prose 中 `<plugin_home>` 占位符的解析机制缺失——在真实安装环境中没有路径发现机制。

## 3. 修复方向

### 方案 A（推荐）：平台 skill `file:` 路径推导
平台 skill loader（ZCode/Claude/Codex 等）已知每个 skill 的 `file:` 绝对路径（在 session system context 中可见，如 `file: C:\Users\peter\.zcode\cli\plugins\cache\...\SKILL.md`）。bootstrap 应指示 agent 从 SKILL.md 的 `file:` 路径推导 plugin_home（`file:` 路径的 `skills/software-project-governance/` 父目录即 plugin_home）。

### 方案 B：install-time 绝对路径注入
在 host 的 native entry file（AGENTS.md/CLAUDE.md）安装时由 projection 工具注入绝对 plugin-cache 路径。

### 方案 C：`python -m` 包调用
如果 plugin 作为可安装 Python 包，使用 `python -m software_project_governance.infra.resolve_entry`。

**推荐方案 A**——零安装时操作，利用平台已有的 `file:` 路径信息。

## 4. 影响范围

- AGENTS.md bootstrap 段（行 3-5 + 所有 `<plugin_home>` 引用）
- governance-init.md / governance-update.md（命令文档中的路径引用）
- 所有平台 native entry file 模板

## 5. 验收标准

1. 在真实 marketplace 安装环境（host 无 `skills/` 目录），agent 能正确定位 resolve_entry.py
2. bootstrap prose 无未定义占位符
3. resolve_entry.py 本身不改（它的 `__file__` 自定位逻辑正确——问题在如何找到它）
