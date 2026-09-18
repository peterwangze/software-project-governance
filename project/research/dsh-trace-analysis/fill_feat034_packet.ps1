# Fill FEAT-034 execution packet contracts
$ErrorActionPreference = "Stop"
$p = "D:\AI\agent\claude\coding\project_management_workflow\.governance\execution-packets.json"
$j = [System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
$pk = ($j.packets.PSObject.Properties | Where-Object { $_.Name -eq "FEAT-034" }).Value

$pk.product_success_contract = [PSCustomObject]@{
    user = "执行 /governance 或打开治理会话的终端用户——实测冷启动到首次交互中位 ~4.5 分钟，在收到第一个问题前被 31 次工具调用与全量深检阻塞"
    job_to_be_done = "当我说 /governance 时，数十秒内先看到一个最小状态行和第一个问题（基于快路径聚合数据），深检查在我做出选择之后再按需执行——而不是等全部检查做完才能开口"
    non_goals = @(
        "不做 Snapshot 字段瘦身——那是 FEAT-036 的边界（本任务只重排时序）"
        "不删减任何深检义务——后置不等于可选，推进类动作前仍强制补齐（M5.5 条 3 明示不削减 M6/M8）"
        "不做多平台 persona 适配（agent.cordis.yml.template）——FEAT-040 范围"
    )
    success_metrics = @(
        "用户可见结果：/governance 冷启动到首次提问的机制构成从「全量健康摘要（31~47s）+六段热文件逐读+交叉验证+面板组装」变为「两次 CLI（<1.5s）+一轮短生成」——协议层已落地，数值验收需新协议会话采样（如实口径，非本任务内可测）",
        "用户可见结果：健康未完成时状态行显示「待检查」而非绿色通过——用户不再被静默的假健康误导",
        "可运行验收：python skills/software-project-governance/infra/verify_workflow.py check-entry-bootstrap-sync --fail-on-issues 返回 PASS（新语义投影双面一致）"
    )
    competitive_baseline = "成熟交互系统的 perceived-performance 惯例：先响应再计算（optimistic UI / streaming first token）——对照现状把全部确定性检查串在首次交互前的阻塞事务设计（arch 判定：控制面侵入交互关键路径）"
    done_definition = @(
        "协议四处一致（命令/入口 SKILL/canonical 模板/行为协议 M5.5）且六项校验全 PASS——已实跑",
        "投影同步幂等（repo+fixture 双 apply [WROTE]→[SKIP]）+ 新语义在本会话活体加载（CLAUDE.md 系统提示已按 FEAT-034 语义重新注入）",
        "独立 Design Reviewer 确认协议语义自洽（C/E 场景深检后置安全性、M5.5 与既有 M5/M7.4 一致性、fallback 路径）——review-FEAT-034-DESIGN-R0.md",
        "效果数值验收（p50≤25s/p95≤45s 轨迹复验）登记为后续会话采样义务（协议改造的验收信号天然滞后一轮——DEC 留档）"
    )
}

$pk.acceptance_contract = [PSCustomObject]@{
    scenario = "新会话执行 /governance：resolve_entry → governance-bootstrap 快路径 → 数十秒内最小状态行 + 首次 ask；深检后置按需执行"
    command = 'python skills/software-project-governance/infra/verify_workflow.py check-entry-bootstrap-sync --fail-on-issues'
    expected_output = "exit 0；repo 根 CLAUDE.md（主入口完整版含 FEAT-034 首次交互前置段）+ AGENTS.md 薄指针双面一致；六项校验全 PASS"
    last_run = [PSCustomObject]@{
        status = "pass"
        exit_code = 0
        summary = "2026-09-18 开发会话实测：projection-sync（16 投影）/entry-bootstrap-sync/cross-refs/manifest/injection-contract/version-consistency 全 PASS；受影响测试 105 passed；治理子集零漂移复现（测量工具稳定）；活体验证=本会话系统提示已按新协议语义加载 CLAUDE.md"
    }
    demo_evidence = "CLAUDE.md 新语义活体（本会话系统提醒已注入含「FEAT-034 首次交互前置」段的完整模板）；sync 双 apply 幂等输出；105 测试 passed"
}

$pk.quality_budget = [PSCustomObject]@{
    dimensions = [PSCustomObject]@{
        performance = [PSCustomObject]@{
            threshold = "交互前路径机制构成：两次 CLI（resolve 0.09s + bootstrap 0.358s）+ 一轮短生成（预期 TTFA p50≤25s——数值验收需后续会话采样）"
            validation = "机制实测：governance-bootstrap 358ms（FEAT-033）；治理子集测量工具零漂移复现（p50=271.8s 与基线逐值一致）"
            status = "pass"
            evidence = "预期机制分析（FEAT-034 返回 §五）；governance-cost-report 对比输出"
            exception = ""
        }
        reliability = [PSCustomObject]@{
            threshold = "深检后置不削减义务（推进类动作前 MUST 补齐）；fallback 路径（聚合命令不可用回退六段读取）"
            validation = "协议文本四处一致性核查 + check-injection-contract PASS（行为契约锚点）"
            status = "pass"
            evidence = "M5.5 条 3；governance-init 模板 fallback 段；六项校验输出"
            exception = ""
        }
        security = [PSCustomObject]@{
            threshold = "resolve_entry fail-closed 第一动作不变；fail-closed STOP 分支原文未动"
            validation = "安全检查（静态）：决策树第一动作比对 + STOP 分支原文核对"
            status = "pass"
            evidence = "governance.md 决策树（未动面）"
            exception = ""
        }
        accessibility = [PSCustomObject]@{
            threshold = "「待检查」诚实语义四处一致；薄指针平台（AGENTS.md）经主入口指针可达新语义"
            validation = "check：deferred ≠ 已检查 ≠ PASS 表述四处核查；AGENTS.md 薄指针零 diff（幂等 SKIP）语义经主入口承载"
            status = "pass"
            evidence = "四处文本 + sync 幂等输出"
            exception = ""
        }
        ux = [PSCustomObject]@{
            threshold = "首次交互前置：快路径后立即 ask；TTFA 与 TTW 成对报告义务（arch 判定：不能只看首次 ask）"
            validation = "M5.5 条 4：实质工作时间跟踪义务 + DEC-205 下界声明 + 成对报告条款在位"
            status = "pass"
            evidence = "behavior-protocol.md M5.5"
            exception = ""
        }
        maintainability = [PSCustomObject]@{
            threshold = "canonical 流向合规（模板→工具生成投影，零手改）；M5.5 为 canonical 行为协议条目"
            validation = "架构检查：sync_entry_projection 生成链 + check-projection-sync 16 投影 PASS + fixture drift 顺手修复（确定性工具）"
            status = "pass"
            evidence = "六项校验 + 105 测试"
            exception = ""
        }
    }
}

$pk.status = "🔄 审查中"
$out = $j | ConvertTo-Json -Depth 12
[System.IO.File]::WriteAllText($p, $out, (New-Object System.Text.UTF8Encoding($false)))
Write-Output "FEAT-034 packet contracts filled"
