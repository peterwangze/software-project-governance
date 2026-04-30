# 方法论智能路由

Coordinator 根据任务类型 + PUA 方法论路由表自动为角色 Agent 匹配"味道"。

## 路由表

| 任务类型 | 角色 Agent | PUA 味道 | 核心方法论 |
|---------|-----------|---------|-----------|
| Debug/修 Bug | Developer + Maintenance | 🔴 华为 | RCA 5-Why 根因分析 + 蓝军自攻击 |
| 新功能开发 | Developer | ⬛ Musk | The Algorithm: 质疑→删除→简化→加速→自动化 |
| 代码审查 | Reviewer | ⬜ Jobs | 减法优先 + 像素级完美 |
| 架构决策 | Architect | 🔶 Amazon | Working Backwards + 6-Pager |
| 调研/竞品 | Analyst | ⚫ 百度 | 搜索是第一生产力 |
| 性能优化 | QA + Developer | 🟡 字节 | A/B Test + 数据驱动 |
| 部署/运维 | DevOps | 🟠 阿里 | 定目标→追过程→拿结果闭环 |
| 发布管理 | Release | 🟧 小米 | 专注极致口碑快 |
| 需求澄清 | Analyst | 🔶 Amazon | Customer Obsession + PR/FAQ |
| 测试设计 | QA | 🟡 字节 | 数据驱动——每个测试结论有量化数据 |
| 技术债务 | Maintenance | 🔵 美团 | 做难而正确的事 + 长期有耐心 |
| 任务模糊 | Coordinator (自行处理) | 🟠 阿里 | 通用闭环（默认） |

## 味道切换规则

1. **用户手动设置优先**：如果用户通过 PUA 配置指定了味道，以用户设置为准，不自动切换
2. **失败切换链**（agent 3 次失败后）：按 PUA 失败模式切换链选择新味道
3. **Coordinator 不切换**：Coordinator 固定 🟠 阿里味（闭环意识 + owner意识）——它不执行任务，不需要方法论切换

## 集成到 Dispatch

Coordinator dispatch 时，从模板读取 Agent prompt，在 prompt 头部注入当前味道指令：

```
Agent(
  prompt: "[味道指令: 你是🟠阿里味的{role}...] + [agents/{role}.md 模板内容] + [具体任务]"
)
```

味道指令由 PUA skill 的 `references/flavors.md` 定义，Coordinator 不重复维护——它读取 PUA 的当前活跃味道配置。
