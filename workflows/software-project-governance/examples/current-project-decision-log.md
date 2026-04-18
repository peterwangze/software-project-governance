# 当前项目决策记录

本文件记录插件化重构阶段的关键决策。

| 编号 | 日期 | 主题 | 背景 | 决策内容 | 备选方案 | 选择原因 | 影响范围 | 决策人 | 关联任务 | 后续动作 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DEC-001 | 2026-04-17 | 仓库定位升级 | 用户澄清项目目标不是文档仓库，而是 agent plugin/skill 仓库 | 将仓库重构为 protocol / workflows / adapters 分层 | 继续以 docs 为中心扩展 | 分层后更利于多 agent 兼容和协议演进 | README、协议层、适配层、样例 | Claude | INIT-001 | 后续迁移旧 docs 资产 |
| DEC-002 | 2026-04-17 | 适配优先级 | 当前需要先服务主流 coding agent | 优先支持 Claude 和 Codex，Gemini 与国内 agent 先预留兼容层 | 同时深度实现所有 agent | 先做主流闭环，再扩展更稳妥 | adapters 目录与后续验证脚本 | Claude | DESIGN-001 | 后续补兼容细节 |
| DEC-003 | 2026-04-18 | Claude 入口分层 | 当前仓库已有半可执行 adapter，但缺少 Claude 当前可直接加载的原生 skill 入口 | 采用“workflow 本体 + adapter contract + Claude native skill entry”三层结构；`CLAUDE.md` 仅作为最薄仓库级指针，`.claude/skills/software-project-governance/SKILL.md` 承载读取顺序、输出规则、Gate 与验证要求，`adapters/claude/*` 继续承载统一 contract 与调试入口 | 只保留 adapter launcher，或把全部规则复制进 skill | 三层结构既能贴近 Claude 当前机制，又能降低对用户仓库级资产的侵入，同时保持协议层与事实源稳定 | `CLAUDE.md`、`.claude/skills/`、`adapters/claude/`、样例记录 | Claude | ACCEPT-001 | 后续验证 Gemini/Codex 是否可按相同分层接入 |
