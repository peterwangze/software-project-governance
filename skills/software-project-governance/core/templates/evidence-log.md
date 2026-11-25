# 证据记录模板

用于记录 workflow 执行过程中的关键证据，支撑任务完成与 Gate 通过。

| 编号 | 对应任务 ID | 证据类型 | 证据说明 | 事实依据 | 原件位置 | 提交人 | 提交日期 | 关联 Gate | 结论 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `<CLI 分配的 EVD 编号>` | `<任务ID>` | `<证据类型>` | `<目标对齐：用判据和问题词说明此次核对>` | `<观测、命令或实测值>` | `<项目相对路径、稳定链接或“见本行”>` | `<提交人>` | `<YYYY-MM-DD>` | `<Gx 或 —>` | `<一句话说明结果>` |

## 使用规则

- 用 `evidence-append --task <任务ID>` 写入。将判据或具体问题词写在 `--description` 的“目标对齐：”说明中，用 `--conclusion` 写短结论。模型在这两列查找材料；详细观测与命令写入 `--basis`。
- 核对结果在一行内即可复验时，`--artifacts "见本行"` 即可。已有独立原件时，`--artifacts` 填稳定的项目相对路径或链接，多项任务可复用同一位置。只对某个单元或轮次有效的判断沿该单元的原生记录绑定。
- 已完成事项必须至少有一条证据。
- Gate 结论必须可追溯到证据。
- 产品代码交付证据必须包含 `事实依据:`、`目标对齐:`、`用户影响:`。
- 有正式审查时，在既有 `evidence-append` 命令上追加 `--review-record <REVIEW-ID>`。每轮传一次 ID。提交前以当前暂存树核对各轮覆盖和内容。事实依据只需记录用户影响的依据及实际执行的命令，例如：

```json
{"commands":[{"cmd":"python -m unittest tests.test_delivery","exit_code":0,"summary":"Two delivery regressions passed."}]}
```

将 JSON 置于 `--basis` 的 `结构化事实:` 标记后。写入器从正式签核和 Git 补出 `files_changed`、`diff_summary`、`review` 和 `git`。在 `--artifacts` 中指向测试回执或相关交付物。

- 提交后的复核可加 `--review-commit <实际完整 SHA>`；跨提交比较可指定 `--review-base <基线>`。例如先执行 `gh run view <run-id> --json headSha,conclusion,url`，确认 `headSha` 等于目标提交，再将真实结果和 URL 加入该笔 `commands` 与 `--refs`。本地测试结果和提交前的树只证明各自实际检查的范围。
- 既有显式 JSON 仍接受 `commands`、`files_changed`、`diff_summary` 与 `review`。无适用审查时使用 `"review":{"applicability":"NOT_REQUIRED","reason":"具体原因"}`；历史 `conclusion: NOT_REQUIRED` 记录仍然可读。
- `结构化事实:` 不得包含 API key、token、password、secret 等明文敏感值；只记录脱敏摘要或日志路径。
