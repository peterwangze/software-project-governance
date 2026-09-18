# Fill FEAT-037 execution packet contracts with delivered values
$ErrorActionPreference = "Stop"
$p = "D:\AI\agent\claude\coding\project_management_workflow\.governance\execution-packets.json"
$j = [System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
$pk = ($j.packets.PSObject.Properties | Where-Object { $_.Name -eq "FEAT-037" }).Value

$pk.product_success_contract = [PSCustomObject]@{
    user = "双入口工作区（AGENTS.md+CLAUDE.md 并存）的使用者——每次会话被注入两份高度重复的 bootstrap 模板（实测各 ~16-22KB），上下文在进入主题前被翻倍占用"
    job_to_be_done = "当我在双入口工作区打开会话时，注入面只保留一份完整引导+一份薄指针（≤3KB），把省下的上下文留给实际工作内容，且单入口工作区体验完全不变"
    non_goals = @(
        "不做协议重排或交互时序变更——那是 FEAT-034 的边界"
        "不删除任何行为约束——薄指针保留最小存活检查（fail-closed 第一动作/先读 plan-tracker/SELF-CHECK/模式确认/UTF-8 规则），完整规则由主入口指针承载"
        "不引入新的运行时依赖或平台耦合——同步机制全宿主可用"
    )
    success_metrics = @(
        "用户可见结果：次要入口注入体积 16011B→2699B（-83%），双入口会话固定注入成本接近减半——用户在会话开始时多出 ~13KB 上下文可用空间"
        "可运行验收：python -m pytest skills/software-project-governance/infra/tests/test_entry_projection.py -q 返回 32 用例全绿（含双 apply 幂等与单入口回归）"
        "可运行验收：python skills/software-project-governance/infra/verify_workflow.py check-entry-bootstrap-sync --fail-on-issues 返回 PASS（repo 根 + fixture 双面守护）"
    )
    competitive_baseline = "成熟工具链的多平台配置管理惯例：单一源生成多目标投影（single-source projection），杜绝手工双维护漂移——本仓 FIX-222/审计史中 AGENTS.md 曾长期携带与模板漂移的旧内容（方法 A/B/C 块、缺失节），正是无生成机制的直接后果"
    done_definition = @(
        "幂等性证明：仓库双文件 + fixture 各连续 apply 两次 SHA256 零 diff——已实跑记录"
        "独立 Code Reviewer 确认薄指针保留最小存活检查、单入口回归不变、launch 语义不变——review-FEAT-037-CODE-R0.md"
        "守护机制上线：check-projection-sync 持续覆盖双面（repo+fixture），漂移在 CI 时点被拦截"
    )
}

$pk.acceptance_contract = [PSCustomObject]@{
    scenario = "维护者运行 sync_entry_projection --write 后再次运行（幂等验证），再运行 check-entry-bootstrap-sync 确认双面一致；单入口 fixture 回归不变"
    command = 'python skills/software-project-governance/infra/verify_workflow.py check-entry-bootstrap-sync --fail-on-issues'
    expected_output = "exit 0；repo 根 AGENTS.md bootstrap 段 2699B ≤3072B 上限、CLAUDE.md 主入口完整 canonical；fixture 同构；双 apply 零 diff"
    last_run = [PSCustomObject]@{
        status = "pass"
        exit_code = 0
        summary = "2026-09-18 开发会话实测：AGENTS.md 16011B→2699B（-83%）；repo+fixture 双 apply SHA256 零 diff；check-projection-sync（16 投影+entry 守护）/cross-refs/manifest/archguard R1~R7 全 PASS；launch.py 冒烟（check/--bootstrap-project/dry-run）语义不变"
    }
    demo_evidence = "test_entry_projection.py 32/32（双 apply 幂等/单入口回归/薄指针结构/launch 复用断言）；当前 AGENTS.md 薄指针版即活体样例（系统已重新注入生效）"
}

$pk.quality_budget = [PSCustomObject]@{
    dimensions = [PSCustomObject]@{
        performance = [PSCustomObject]@{
            threshold = "同步脚本全仓运行秒级（模板提取+双面拼接）"
            validation = "实跑 sync_entry_projection --write 全仓 <5s（开发会话）；launch.py 延迟导入不影响启动路径"
            status = "pass"
            evidence = "开发会话实跑输出；test_entry_projection 集成用例"
            exception = ""
        }
        reliability = [PSCustomObject]@{
            threshold = "幂等零 diff（双 apply SHA256 相等）；单入口回归不变；粘滞防回翻"
            validation = "python -m pytest tests/test_entry_projection.py -q：32 用例含幂等/回归/粘滞全绿"
            status = "pass"
            evidence = "repo 双文件 + fixture 各两次 apply SHA256 零 diff（2026-09-18 实跑）"
            exception = ""
        }
        security = [PSCustomObject]@{
            threshold = "默认只读（--write 显式）；无 shell 注入面；段级 splice 保留非目标内容"
            validation = "安全检查（静态）：默认 dry-run 设计 + 拒绝无段文件 + force 语义显式；嵌套围栏解析边界处理"
            status = "pass"
            evidence = "sync_entry_projection.py CLI 参数面；launch.py 拒绝/dry-run 冒烟"
            exception = ""
        }
        accessibility = [PSCustomObject]@{
            threshold = "CLI 参数自解释（--write 默认只读提示）；报告可读（build_sync_report）"
            validation = "check：build_sync_report 输出漂移明细；--help 路径可用"
            status = "pass"
            evidence = "test_entry_projection 报告渲染用例"
            exception = ""
        }
        ux = [PSCustomObject]@{
            threshold = "次要入口宿主（Codex/opencode）会话注入 -83%；主入口宿主（Claude）行为不变"
            validation = "注入体积对比 16011B→2699B；CLAUDE.md canonical 完整版零改写承载"
            status = "pass"
            evidence = "当前 AGENTS.md 活体（系统已重新加载薄指针版）"
            exception = ""
        }
        maintainability = [PSCustomObject]@{
            threshold = "单一 canonical 源（governance-init.md Step 7）；launch.py 复用共享函数零逻辑复制；契约面走文档化 regen（86 keys）"
            validation = "check-manifest-consistency PASS（732 canonical）；archguard R1~R7 PASS（R2 47≤47 零新增反向依赖）"
            status = "pass"
            evidence = "registry 77/77 + contract_matrix 27/27 + archguard 38/38 全绿；version-projections canonical-bootstrap-version 投影登记"
            exception = ""
        }
    }
}

$pk.status = "🔄 审查中"
$out = $j | ConvertTo-Json -Depth 12
[System.IO.File]::WriteAllText($p, $out, (New-Object System.Text.UTF8Encoding($false)))
Write-Output "FEAT-037 packet contracts filled + status=审查中"
