# Fill FEAT-036 execution packet contracts
$ErrorActionPreference = "Stop"
$p = "D:\AI\agent\claude\coding\project_management_workflow\.governance\execution-packets.json"
$j = [System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
$pk = ($j.packets.PSObject.Properties | Where-Object { $_.Name -eq "FEAT-036" }).Value

$pk.product_success_contract = [PSCustomObject]@{
    user = "每次 /governance 或状态展示的观看者——24 字段全量面板在 98 tok/s 输出速度下贡献分钟级等待；关心异常但不需要每次读全部 24 项"
    job_to_be_done = "默认看到 8 字段以内的紧凑视图（含异常位——FAIL/风险/证据缺失不隐藏），需要时一步获取完整 24 字段信任面"
    non_goals = @(
        "不削减机器面——24 字段契约经 status --json 完整保留（断言面不降级）"
        "不隐藏异常——权限风险/已知 FAIL/证据缺失在默认视图必显（折叠保留异常位）"
        "不做 Scenario 按需加载——FEAT-038 边界"
    )
    success_metrics = @(
        "用户可见结果：默认状态展示从 24 行面板降为 8 字段紧凑视图（生成预算推演上界 ≈260 tok，对 700 tok 契约阈值余量 63%）——面板等待时间相应缩短",
        "用户可见结果：异常不隐藏——健康 FAIL/活跃风险/证据缺失在默认视图的 Health/Risks 位仍必显（红线入约并有守护测试）",
        "可运行验收：CLI 子命令 status --json 输出完整 delivery_trust_snapshot 对象（24 字段含 Flow-unit lanes）；first-run-demo --assert-snapshot 断言全字段 PASSED"
    )
    competitive_baseline = "成熟observability面板惯例：默认摘要视图 + 详情按需展开（如 Grafana 的 collapsed panels / kubectl 的 --show-managed-fields=false）——对照现状 24 字段全量强制渲染（arch 判定：输出量直接乘出用户等待）"
    done_definition = @(
        "守护测试在位：test_governance_snapshot_dual_contract_default_view_guard 锁定 compact 块恰 8 字段行、全脸字段不漏入、Flow-unit lanes 在案",
        "独立 Code Reviewer 确认异常不隐藏红线逐字核实、24 字段载体可达、预算推演合理——review-FEAT-036-CODE-R0.md",
        "同步面一致：governance-status.md 与 /governance 双契约同口径；全部校验 PASS（含两个自引入问题的修复验证）"
    )
}

$pk.acceptance_contract = [PSCustomObject]@{
    scenario = "用户执行 /governance 或状态展示：默认 8 字段紧凑视图（异常位可见）；显式请求或机器消费时一步获取完整 24 字段信任面"
    command = 'python skills/software-project-governance/infra/verify_workflow.py status --json'
    expected_output = "exit 0；JSON 含 delivery_trust_snapshot 对象（24 字段，含 Flow-unit lanes）；first-run-demo --assert-snapshot PASSED 断言全字段"
    last_run = [PSCustomObject]@{
        status = "pass"
        exit_code = 0
        summary = "2026-09-18 开发会话实测：verify/check-cross-references/check-manifest-consistency/check-projection-sync/check-governance-pack-status/e2e-check（cli 6/6·target 4/4·fixture 8/8）全 PASS + 858 单测 OK + 两个 harness PASS；默认视图预算推演上界 ≈260 tok≤700（DEC-205 推演口径——新会话采样随 FEAT-040）"
    }
    demo_evidence = "test_governance_snapshot_dual_contract_default_view_guard（新增守护）+ first-run-demo --assert-snapshot PASSED 输出 + commands/governance.md Scenario F 双契约段活体"
}

$pk.quality_budget = [PSCustomObject]@{
    dimensions = [PSCustomObject]@{
        performance = [PSCustomObject]@{
            threshold = "默认视图生成预算 ≤700 tok（arch 契约值）"
            validation = "预算指标：静态推演上界 ≈260 tok（8 字段×典型长度，DEC-205 推演口径标注）；实测采样随 FEAT-040 多平台回归（RISK-055 同族）"
            status = "pass"
            evidence = "推演表（FEAT-036 返回）；守护测试锁定字段数"
            exception = ""
        }
        reliability = [PSCustomObject]@{
            threshold = "机器面 24 字段零降级；守护测试防回归（compact 恰 8 行/全脸不漏入）"
            validation = "python -m pytest 检查：858 单测 OK 含新增守护；first-run-demo --assert-snapshot PASSED"
            status = "pass"
            evidence = "全部校验输出（开发会话实跑）"
            exception = ""
        }
        security = [PSCustomObject]@{
            threshold = "异常不隐藏红线：权限风险/已知 FAIL/证据缺失在默认视图必显（Health/Risks/Mode 位）"
            validation = "安全检查（静态）：红线逐字在两文件契约段 + 守护测试 token 断言"
            status = "pass"
            evidence = "commands/governance.md + governance-status.md 双契约段"
            exception = ""
        }
        accessibility = [PSCustomObject]@{
            threshold = "默认视图字段名自解释 + Full 指示行告知完整面获取方式"
            validation = "check：8 字段命名（Mode/Stage and Gate/Tasks/Risks/Health/Next/Decision + Full 行）与获取指引在案"
            status = "pass"
            evidence = "输出模板框（governance-status.md）"
            exception = ""
        }
        ux = [PSCustomObject]@{
            threshold = "面板行数 24→8；异常位保留；与 FEAT-034 时序衔接（最小状态行=一行子集）"
            validation = "指标检查：compact 块字段计数守护测试 + 最小状态行条款入约"
            status = "pass"
            evidence = "test_governance_snapshot_dual_contract_default_view_guard"
            exception = ""
        }
        maintainability = [PSCustomObject]@{
            threshold = "双契约单一事实源（governance.md 为 canonical，status 命令为同步面）；引擎零改动"
            validation = "架构检查：verify_workflow.py 机器面零改动核实 + cross-refs/manifest/projection-sync PASS"
            status = "pass"
            evidence = "六项校验 + 858 单测"
            exception = ""
        }
    }
}

$pk.status = "🔄 审查中"
$out = $j | ConvertTo-Json -Depth 12
[System.IO.File]::WriteAllText($p, $out, (New-Object System.Text.UTF8Encoding($false)))
Write-Output "FEAT-036 packet contracts filled"
