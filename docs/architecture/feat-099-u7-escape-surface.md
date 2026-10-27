# FEAT-099 — U7 对抗性逃逸面清单（A1-A4）

- **Task**: FEAT-099（U1 DSH 宿主级执法接线 PoC，0.100.0，DEC-374）
- **产物性质**: 设计 §4.2 口径——逃逸面如实记录为**披露输入**，非失败；「guard 面 + bash/fs 面 + git hooks 面全堵才算闭环」（调研 §7 U7）。
- **验证基础**: S4 in-process 探针（真实 dsh-tools@0.1.5-rc.3 管线，隔离 DSH_HOME，2026-10-27）+ 仓库级既有硬门现状。
- **判定**: 当前 A1-A4 全部开放——宿主级 PoC 证实的是「可达 + 可拦」，不是「全堵」。分层披露如下。

## A1 — guard 面：无锚派发放行

| 通道 | 实测 | 严重度 |
|---|---|---|
| `subagent`/`subagent_fork` 调用首行无 `[governance-dispatch …]` 锚 | probe v3a：**allow**（C7 计数 `enforcement-unanchored`） | 高（PoC 面主要残留缺口） |

- 机理：锚协议是**派发方义务**（Coordinator 侧协议级 MUST——SKILL「动作级执法」/派发模板注入锚）；guard 不强制锚的原因是误伤面（非治理流量全部被拒）。
- 补位：协议面（派发模板）+ CLI 面（`enforcement-check --facts` 在派发前判定）。强制锚（如「Coordinator 会话内无锚派发也拒」）需按调用方身份分流——后续批候选。
- U7 模型级绕行（拒了之后换通道）落入 A2/A4。

## A2 — bash/fs 面：绕开 tools 管线

| 通道 | 实测 | 严重度 |
|---|---|---|
| 直接 `pwsh` 跑 `python verify_workflow.py …`（不经 tools 管线） | guard 不可达（guard 只挂 `ctx.tools` 管线）——设计已知，非本轮回归 | 中 |
| 直接 fs 写 `.governance/`（write_guard 之外） | 同上；write-guard 只在写后校验 | 中 |

- 补位：CLI 判定面需要被调用（RPG 实证「不调用即绕过」）；git hooks 面对**提交时点**硬门（见 A3）；治理台账 CAS（task-row-update revision/evidence append CAS）拒机器面外写入。
- 根因定性：宿主级 guard 的管辖域 = tools 管线；shell/fs 直达通道属宿主 sandbox-policy 面（用户部署策略可关，调研发现 7——FEAT-095 明确不依赖它做执法）。

## A3 — git hooks 面：--no-verify 与推送窗

| 通道 | 现状 | 严重度 |
|---|---|---|
| `git commit --no-verify` 绕 pre-commit/commit-msg | 既有披露（hooks 仓库级，用户可绕）；纪律链披露处置 | 低（纪律面） |
| pre-push hook 缺失 | FEAT-095 §8.1 建议的「唯一零成本补强点」**未实施**（本 PoC 范围外，维持候选） | 中 |
| tag 推送看护 | 同上（release ledger 侧有 NATIVE_RELEASED 双 PASS 机器门补位） | 低 |

## A4 — 其他工具通道：face 枚举外

| 通道 | 实测 | 严重度 |
|---|---|---|
| 非 `subagent`/`subagent_fork` 工具名（`workflow`/`route_agent`/未来 spawn 通道） | guard 静默放行（`GUARDED_TOOLS` 枚举外，probe 证实 read_file 放行） | 中 |
| PTC 模式 `run_code` 内嵌 sub-dispatch | 类型面：`parent` token 标记 transport sub-dispatch——guard 挂全局层按 README「plain-context guard applies globally」应同样可见，**未实测**（probe 用 native 模式），如实标注 | 低（待测） |

- 补位：扩 face = 改 `GUARDED_TOOLS` 常量（设计预留单点）；PTC 面留后续批实测。

## 结论

宿主级拦截 PoC 证实（V1-V8）后，对抗面收敛为：**A1 无锚（协议补位）+ A2/A3 直达与推送（hooks/台账 CAS 补位）+ A4 枚举外（单点扩 face）**。全堵 = 三面联合（U7 原始口径），各面均有已交付或已登记的补位机制；无静默通道（每通道要么有补位要么在本清单披露）。
