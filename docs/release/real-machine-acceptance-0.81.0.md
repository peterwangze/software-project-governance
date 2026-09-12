# 真机验收规程 — 0.81.0（DSH 真实环境三项 + 隔离验收）

> **目的**：0.80.0 遗留的「真机三项」在本版尝试闭合。按 **DEC-190 ⑧**：自动化验收一律以 `DSH_HOME` 重定向到临时目录；**真机三项由用户手动执行并回贴输出**，由 Coordinator 机录 evidence 行。
> **纪律（M7.7 R1/R4）**：本规程全部命令**只读**。任何写操作（安装/同步/删除）都**不**在本规程内——需要时单独授权。
> **措辞纪律**：自动化部分一律表述为「隔离环境安装冒烟（环境变量重定向至临时目录）通过」；不使用无限定语的「真实安装/真实环境通过」。

## 0. 前置确认（只读）

```powershell
# 0.1 仓库版本与 HEAD（应为你 link 安装指向的源码仓）
cd D:\AI\agent\claude\coding\project_management_workflow
git log --oneline -1
(Get-Content .\package.json -Raw | ConvertFrom-Json).version

# 0.2 插件在 profile 里的声明形态（应为 link: 指向本仓库）
Get-Content "$env:USERPROFILE\.dsh\profiles\web\package.json" -Encoding UTF8

# 0.3 用户预设根当前内容（应含 governance + novel-writing）
Get-ChildItem "$env:USERPROFILE\.dsh\.agent-presets" | Select-Object Name, LastWriteTime

# 0.4 已渲染预设的版本标记（重启 dsh 后应与 package.json 版本一致）
Get-Content "$env:USERPROFILE\.dsh\.agent-presets\governance\.dsh-bundle-version"
```

**期望**：0.1 的版本号 = 本次发布版本（0.81.0）；0.4 的标记 = 同一版本号（说明 `ensurePreset` 已在启动时重新渲染）。若 0.4 落后于 0.1，重启一次 dsh 再复读。

## 1. 真机三项验收（用户手动执行，逐项回贴）

### 项 1：设置页「自定义」标签 + 删除按钮 + 打开目录

**操作**（GUI，无命令）：打开 dsh 设置页 → Agent 预设列表 → 找到「治理协调器」。

**判据**（逐项回答 是/否 + 截图或文字描述）：
- [ ] 标签显示为「**自定义**」（不是「内置」）
- [ ] 有「**删除**」按钮
- [ ] 有「**打开目录**」（或「打开位置」）按钮，点击后打开的目录 = `C:\Users\<你>\.dsh\.agent-presets\governance`

**只读复核命令**（可与 GUI 结果互相印证）：

```powershell
# 预设标识（应指向用户根，而非仓库内）
Get-Content "$env:USERPROFILE\.dsh\.agent-presets\governance\preset.yml" -Encoding UTF8

# 渲染产物存在性（两个文件）
Get-ChildItem "$env:USERPROFILE\.dsh\.agent-presets\governance"

# 渲染产物哈希（应与仓库内两条渲染路径一致；替代 <REPO> 为你的仓库路径）
(Get-FileHash "$env:USERPROFILE\.dsh\.agent-presets\governance\agent.cordis.yml" -Algorithm SHA256).Hash
```

### 项 2：非治理预设会话**不含**治理技能（FIX-310 的核心行为目标）

**操作**：新建一个使用 **standard**（或任意非 governance）预设的会话，向该会话的 agent 说：

> 请列出你当前可用的 skill 名称（只要名字列表）。

**判据**：
- [ ] 列表中**不包含** `software-project-governance`，也不包含 `governance`、`stage-*`、`*-review` 等本项目技能
- [ ] （正面）治理预设会话中同一提问**应包含**上述技能 —— 见项 3

### 项 3：治理预设会话技能目录完整性

**操作**：新建一个使用 **governance** 预设的会话，逐条执行：

1. 说：`/governance`（或直接粘贴 `/governance`）→ 应能加载治理入口 skill（`governance` 手势可用）
2. 说：`请列出你当前可用的 skill 名称（只要名字列表）。`

**判据**（**按声明名断言，不得按目录大小断言**）：
- [ ] `/governance` 手势可用（加载成功、输出治理状态或场景路由）
- [ ] 列表中**包含** `software-project-governance`
- [ ] 列表中**包含** `governance`（命令投影 shim）与至少 3 个 `stage-*`（如 `stage-development`）
- [ ] `/governance` 会话内执行 `python "<plugin_root>/skills/software-project-governance/infra/resolve_entry.py" --json` → `resolved_root_ok: true`

## 2. 隔离环境验收（Coordinator 侧，自动化；供对照）

以下由 Coordinator 在**隔离 `DSH_HOME`**下执行，用户无需操作，仅作对照记录：

| # | 命令 | 期望 |
|---|---|---|
| 1 | `check-dsh-preset-smoke`（28u） | exit 0；`real-home writes: 0` |
| 2 | `check-dsh-preset-compat`（28v） | PASSED；`rows_enabled 23` / `rows_checked 18` |
| 3 | `check-dsh-boundary`（28w，V8 交付后） | PASSED（K-1~K-13） |
| 4 | `dsh-doctor --offline --json`（V8 交付后） | 8 阶段全 `NOT_RUN` 且 exit 0 |
| 5 | 三路径渲染 sha256 | 全等 `00e0d330…3723` |

## 3. 回贴方式

把每项结果按下表回贴（**可直接粘贴命令输出**）：

```
[项 1] 自定义标签: 是/否 | 删除按钮: 是/否 | 打开目录: 是/否 | 打开路径: <路径>
[项 2] 非治理会话技能列表: <粘贴> | 含治理技能: 是/否
[项 3] /governance 可用: 是/否 | 含 software-project-governance: 是/否 | 含 governance shim: 是/否 | stage-* 数量: <n> | resolve_entry resolved_root_ok: <true/false>
```

Coordinator 收到后**当下机录** evidence 行；未回贴的项在发布文档中如实标注「**未验证**」，**不声明其成立**。

## 4. 未验证项的后果

若某项未验证或为否：
- 发布文档 `docs/release/release-checklist-0.81.0.md` §真机验收面 MUST 逐项标注 `未验证` / `FAIL`，不得写 PASS；
- 对应风险（如设置页标签异常 → RISK-050 的可见面）**不关闭**；
- 若为「否」，记录为缺陷并按变更控制流程新开 task（或并入本次发布前修复链，视严重度）。

---

*本规程为 DEC-190 ⑧ 的执行载体；随发布版本更新。*
