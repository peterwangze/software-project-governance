# Fill FEAT-035 execution packet contracts
$ErrorActionPreference = "Stop"
$p = "D:\AI\agent\claude\coding\project_management_workflow\.governance\execution-packets.json"
$j = [System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
$pk = ($j.packets.PSObject.Properties | Where-Object { $_.Name -eq "FEAT-035" }).Value

$pk.product_success_contract = [PSCustomObject]@{
    user = "插件使用者的本地工作区——旧协议下版本升级在用户开口前静默改写其入口文件与跟踪表（实测 Scenario C 交互前写操作）"
    job_to_be_done = "当插件版本更新后的首次会话启动时，先看到升级摘要（改哪些文件/怎么回滚），我确认后才动我的文件——未响应前我的工作区零改动"
    non_goals = @(
        "不删除升级能力——A~E 序列与清理/迁移在确认后完整可用"
        "不做 Scenario 按需加载——FEAT-038 边界（本任务只改时序）"
        "不改变 @bootstrap-version 标记值——版本联动 bump 属发布动作"
    )
    success_metrics = @(
        "用户可见结果：升级从「静默改写」变为「摘要先行+确认后执行」——用户首次获得对自身工作区写操作的知情权与否决权（默认选项仍为执行升级（推荐），自动精神保留）",
        "用户可见结果：拒绝或未响应时工作区零改动，版本落后状态在状态行持续可见（无静默版本差）",
        "可运行验收：python -m pytest skills/software-project-governance/infra/tests/test_verify_workflow.py -q -k UpgradeWriteConfirmation 返回 4 用例全绿（新标记断言+旧静默措辞反断言）"
    )
    competitive_baseline = "成熟软件的升级交互惯例：变更预览 + 显式确认（如 apt 的 diff 展示、IDE 的 update confirmation）——对照旧协议在用户首次发言前改写其文件（arch 判定：展示状态不应拥有修改项目的隐含授权）"
    done_definition = @(
        "写操作清单显式化：升级摘要列出全部目标文件与回滚方式（协议文本核实）",
        "独立 Design Reviewer 确认 DEC-207② P2-1 衔接句消除解读歧义、A~E 写面全覆盖、时序无歧义——review-FEAT-035-DESIGN-R0.md",
        "守护测试在位：4 断言组（ask 标记/dry-run 确认门/模板计数+旧措辞反断言/衔接句三落点）"
    )
}

$pk.acceptance_contract = [PSCustomObject]@{
    scenario = "版本更新后首次会话：呈现升级待处理摘要（含写操作清单+回滚）→ 默认推荐执行 → 确认后自动完成；未响应/拒绝 → 零写操作 + migration 标志持续提示"
    command = 'python -m pytest skills/software-project-governance/infra/tests/test_verify_workflow.py -q -k UpgradeWriteConfirmation'
    expected_output = "4 passed；另四项静态校验（entry-bootstrap/projection/injection-contract/version-consistency）exit=0"
    last_run = [PSCustomObject]@{
        status = "pass"
        exit_code = 0
        summary = "2026-09-18 开发会话实测：test_verify_workflow 全文件 862 passed（含新增 4）；四校验 exit=0；活体投影 CLAUDE.md 已按新语义重新加载（本会话系统提示可见「提示+确认后执行——FEAT-035；用户未响应前零写操作」）"
    }
    demo_evidence = "UpgradeWriteConfirmationTests（4 断言组）+ 活体 CLAUDE.md 升级段（系统已重新注入）+ grep 计数（呈现升级待处理×4/零写操作×4/旧措辞=0）"
}

$pk.quality_budget = [PSCustomObject]@{
    dimensions = [PSCustomObject]@{
        performance = [PSCustomObject]@{
            threshold = "升级检测零额外开销（版本比较已在聚合命令标志位，FEAT-033）"
            validation = "机制核实：migration 标志复用，确认 ask 复用既有交互通道——无新增命令"
            status = "pass"
            evidence = "governance-bootstrap migration 字段（FEAT-033 交付）"
            exception = ""
        }
        reliability = [PSCustomObject]@{
            threshold = "确认前零写操作语义可验证；拒绝路径无静默版本差"
            validation = "python -m pytest 检查：UpgradeWriteConfirmationTests 4 用例（标记+反断言）全绿"
            status = "pass"
            evidence = "862 passed（全文件）"
            exception = ""
        }
        security = [PSCustomObject]@{
            threshold = "用户工作区写操作全部确认前置（R1 语义强化：升级序列属推进类动作）"
            validation = "安全检查（静态）：写操作清单显式化 + 深检前置衔接句三落点逐字核实"
            status = "pass"
            evidence = "governance.md Scenario C + 模板块 + SKILL.md 衔接句"
            exception = ""
        }
        accessibility = [PSCustomObject]@{
            threshold = "升级摘要自解释（跨度/要点/清单/回滚四要素）+ 默认推荐项降低选择成本"
            validation = "check：摘要四要素在协议文本逐项在场"
            status = "pass"
            evidence = "governance.md Scenario C 重写段"
            exception = ""
        }
        ux = [PSCustomObject]@{
            threshold = "一次确认成本 vs 静默改写风险的权衡落地（默认推荐执行）"
            validation = "指标检查：承诺句安全化重写（自动精神保留——确认后其余自动完成）"
            status = "pass"
            evidence = "governance-init.md 尾部承诺句"
            exception = ""
        }
        maintainability = [PSCustomObject]@{
            threshold = "canonical 流向合规（模板→工具生成投影）；交叉引用零新环"
            validation = "架构检查：四项校验 exit=0 + sync 幂等复跑零 diff"
            status = "pass"
            evidence = "校验输出 + 投影 [SKIP] 输出"
            exception = ""
        }
    }
}

$pk.status = "🔄 审查中"
$out = $j | ConvertTo-Json -Depth 12
[System.IO.File]::WriteAllText($p, $out, (New-Object System.Text.UTF8Encoding($false)))
Write-Output "FEAT-035 packet contracts filled"
