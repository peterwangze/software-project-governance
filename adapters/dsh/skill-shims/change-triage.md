---
name: change-triage
description: 变更控制 triage——产品代码新任务强制入账门禁（五步 triage + 机器记录，快速通道仅限治理记录）
---

# change-triage（DSH 投影）

本 skill 是 `commands/change-triage.md` 在 DeepSeek Harness 上的薄投影（thin pointer），自身不含 workflow 规则，不重复、不覆盖源文件。

加载后执行：

1. 用 `read` 工具读取治理插件仓库的 `commands/change-triage.md`（`<plugin_root>` 见本会话 persona 或项目 `AGENTS.md` 的 Governance Bootstrap 段；software-project-governance skill 的 resourceBase 亦指向该仓库内 skill 目录）。
2. 完全遵循该文件内容执行。

若源文件缺失或仓库路径不可得：MUST STOP，向用户报告"治理命令投影无法解析插件仓库根目录"，并给出安装提示（`python <plugin_root>/adapters/dsh/launch.py --install`），不得凭空执行命令内容。
