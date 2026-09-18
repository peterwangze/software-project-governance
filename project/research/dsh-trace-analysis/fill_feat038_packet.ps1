# Fill FEAT-038 execution packet contracts
$ErrorActionPreference = "Stop"
$p = "D:\AI\agent\claude\coding\project_management_workflow\.governance\execution-packets.json"
$j = [System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
$pk = ($j.packets.PSObject.Properties | Where-Object { $_.Name -eq "FEAT-038" }).Value

$pk.product_success_contract = [PSCustomObject]@{
    user = "每次 /governance 会话的 agent 执行者——660+ 行全量命令文档进入上下文（实测 30KB 注入），而当前场景只需要一个分支"
    job_to_be_done = "命中场景时只加载对应分支的完整规程（按需 Read），默认注入面只携带路由层（决策树+六摘要+路由指令）"
    non_goals = @(
        "不删减任何 Scenario 语义——内容是搬移到按需文件（逐行对照零丢失）"
        "不做多平台回归——FEAT-040 边界"
        "不动 FEAT-039 的预算面（并行任务）"
    )
    success_metrics = @(
        "用户可见结果：/governance 命令文档注入从 49,889B 降到 11,702B（-76.5%，预算 12,288B 内余量 586B）——会话启动的固定注入开销显著下降",
        "用户可见结果：六场景规程完整可达（命中场景读对应文件，语义零丢失——A 24/24 至 F 120/120 逐行对照）",
        "可运行验收：python -m pytest skills/software-project-governance/infra/tests/test_verify_workflow.py -q -k FEAT038 返回 9 用例全绿（≤12KB 硬上限/六摘要/路由指令/零丢失/零回退守护）"
    )
    competitive_baseline = "成熟 CLI 的 lazy-loading 惯例：主命令输出概要+子命令详情按需（如 git/kubectl 子命令帮助不随主帮助注入）——对照现状 6 场景全量手册常驻上下文"
    done_definition = @(
        "路由层+九按需文件就位，manifest 登记（16→25 投影与 projection_ids 精确一致）",
        "交叉引用零悬空零循环（695 引用 PASS）；fixture 镜像 10 文件同步",
        "独立 Code Reviewer 确认零语义丢失（抽验 C/F 含 FEAT-035/036 关键 token）与路由无歧义——review-FEAT-038-CODE-R0.md"
    )
}

$pk.acceptance_contract = [PSCustomObject]@{
    scenario = "/governance 会话：决策树命中场景 → Read 对应 scenario 文件执行完整规程；未命中场景的规程不占注入面"
    command = 'python -m pytest skills/software-project-governance/infra/tests/test_verify_workflow.py -q -k FEAT038'
    expected_output = "9 passed；cross-references（695 引用零悬空零循环）/projection-sync（25 投影）/manifest/injection-contract/verify/e2e-check 全 exit 0"
    last_run = [PSCustomObject]@{
        status = "pass"
        exit_code = 0
        summary = "2026-09-18 开发会话实测：主文件 11,702B≤12,288B（余量 586B）；六场景逐行对照 A24/24 B104/104 C41/41 D58/58 E75/75 F120/120；901+38+18+53 测试 OK；2 处披露改写（Snapshot 节标题/overview 首行指称）"
    }
    demo_evidence = "FEAT038GovernanceOnDemandSplitTests 9 用例 + 零丢失对照表（Developer git HEAD 逐行复核）+ 字节对比 49,889→11,702B"
}

$pk.quality_budget = [PSCustomObject]@{
    dimensions = [PSCustomObject]@{
        performance = [PSCustomObject]@{
            threshold = "主文件 ≤12,288B（12KB 预算）；拆出文件不计入默认注入面"
            validation = "体积指标：11,702B 实测（余量 586B）+ 守护测试硬上限断言"
            status = "pass"
            evidence = "字节对比表 + test FEAT038 硬上限用例"
            exception = ""
        }
        reliability = [PSCustomObject]@{
            threshold = "零语义丢失（搬移非删减）；FEAT-034/035/036 语义零回退"
            validation = "python -m pytest 检查：9 用例含子标题零丢失+零回退守护；抽验 token（用户未响应前零写操作/dry-run 先行/≤8 字段/20+4 双契约）在场"
            status = "pass"
            evidence = "逐行对照表 A24-F120 + 901 测试 OK"
            exception = ""
        }
        security = [PSCustomObject]@{
            threshold = "路由层保留决策树与 fail-closed 语义；按需文件不削弱任何 MUST 约束"
            validation = "安全检查（静态）：六摘要+路由指令在场；跨场景注记重申首次交互前置/深检后置/deferred 待检查"
            status = "pass"
            evidence = "commands/governance.md 路由层全文"
            exception = ""
        }
        accessibility = [PSCustomObject]@{
            threshold = "六摘要足够 agent 自主路由（触发条件/步骤数/文件指针无歧义）"
            validation = "check：六摘要表结构一致（每场景 3-5 行摘要+MUST Read 指令）"
            status = "pass"
            evidence = "路由层六摘要表"
            exception = ""
        }
        ux = [PSCustomObject]@{
            threshold = "会话启动固定注入面 -76.5%（49,889→11,702B）"
            validation = "指标检查：字节实测对比 + 不在注入面守护用例"
            status = "pass"
            evidence = "注入体积验收表（开发会话）"
            exception = ""
        }
        maintainability = [PSCustomObject]@{
            threshold = "子目录结构与扁平命令发现机制隔离；manifest 25 投影精确登记"
            validation = "架构检查：cross-references 695 引用零悬空零循环 + projection-sync 25 投影 PASS + 校验器 5 处归属改指 owning document"
            status = "pass"
            evidence = "六项校验全 exit 0"
            exception = ""
        }
    }
}

$pk.status = "🔄 审查中"
$out = $j | ConvertTo-Json -Depth 12
[System.IO.File]::WriteAllText($p, $out, (New-Object System.Text.UTF8Encoding($false)))
Write-Output "FEAT-038 packet contracts filled"
