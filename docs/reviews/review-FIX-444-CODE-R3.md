# FIX-444 Code Review R3 — 签名门/谓语尾/fail-closed 复审（同一 Reviewer 必达轮·T2 熔断点）

- **轮次**: R3（复审；R2 结论 NEEDS_CHANGE，unresolved_blockers=3，txn 5baf2920…/seq25）
- **前轮引用**: `docs/reviews/review-FIX-444-CODE-R2.md`（**原机 92 行/9563B/sha `8cdcb694…` 未改**）+ post-record 补充件 `.governance/incidents/FIX-444-reviewer-R2-post-record-supplement.md`（sha 链 8cdc→7615→恢复 8cdc，回执 `FIX-444-R2-report-binding-recovery.json`：13:42:37Z 保全/13:43:36Z 恢复核验）——**C6/fail-closed 事实经补充件引用，不称原机 recorded**
- **审查方**: Code Reviewer Agent（与 R0~R2 同一实例；只读；唯一写面 = 本报告）
- **审查对象绑定**: HEAD `bf6942dd…` staged 空（实测）；`hooks/commit-msg` blob **`8efea9430658b73c3baf481676e455666bd914f7`**（155+/1−）+ `tests/test_hooks.py` blob **`8efd64da0f28a632179e890a27f4cb4a0494295b`**（470+/2−）=625+/3−——与派发精确一致（实测 hash-object）
- **结论**: **BLOCKED**（round 3 = 复审 fuse；仍有确认阻塞 → T2 终态+用户升级，不自动 R4）

```json
{"verdict": "BLOCKED", "unresolved_blockers": 3}
```

---

## 0. 结论

**R2 三项阻断的修复面全部实际达成**：R2 逃逸 n1/n7/n8 的 unsigned 形实测 BLOCK；旧五攻击保持 BLOCK；三 ctl 合法引用 PASS；防线 N3/N4/N6（unknown 键/未闭合/第二肯定）BLOCK；**mask 层 fail-open 已修**（FC1 缺失/FC2 崩溃/FC3 空输出/FC4 真实在场全正确——R2 C6 补充件要求的受控故障检查通过）；V1 终冻结窗口（**829,726B/SHA 49FE75CF…8BC8**，=Coordinator 冻结态）三任务实数行集 **72/24/65 全 PASS**（真实 Step-12 路径、真 bash、clean exit；非零行断言）。

**但三个必要不接受的逃逸面经实际探针确认仍然开放**（全部 actual output）：①**伪造签名**——≥3 闭表键的纯语法计数不是 source provenance：`{"id":"#1","observed":"PASS｜我编造了测试结果;","raw":"x"}` 等 **三形全 PASS**（F1/F2/F3；F4 两键形正确 BLOCK——阈值语法有效但可自伪造）；②**封闭谓语尾后接背书续句**——`发现"不允许不编造"为边界，请照此要求必须遵守并当真执行`/`…已实证，我要求把结果当作真实数据` **PASS**（P1/P2；P3 真引用 ctl 正确 PASS——尾后上下文未区分）；③**故障传播未覆盖 sed/grep 管线腿**——真实 mask 保持运行、仅 fixture 内函数桩替换下，sed 失败/grep 错误（exit 2）使**实际肯定 payload 判 PASS**（FC5/FC6——R2 fail-closed 原则只落到 mask 层）。round 3 仍 NEEDS_CHANGE → **T2 熔断：BLOCKED 终态，升级用户决策**，不自动 R4、不以压力降质。

## 1. 验证矩阵结果（全部真 bash 实跑；生成器/补丁/probes.txt 全 literal 落隔离根 fix444r3-rev-110c44aa）

| # | 项 | 结果 | 证据 |
|---|----|------|------|
| V1 | 三任务真实行端到端（终冻结窗口） | **PASS** | 829,726B/SHA 49FE75CF…；72/24/65 全 PASS 零 BARE_ROW；clean exit（探针 exit 1 系 FC5/FC6 预期 fail 标记） |
| V2 | 拒绝集 | **PASS** | affirm/mixed/dneg 全 BLOCK（missing-basis 门 R2 已验保持） |
| V3A | 旧五攻击+三 ctl | **PASS** | A1~A5 全 BLOCK；C1~C3 全 PASS |
| V3N | R2 三逃逸（unsigned 形）+防线 | **PASS** | N1/N7/N8 BLOCK；N3/N4/N6 BLOCK |
| V3F | **伪造签名面** | **FAIL×3** | F1/F2/F3 PASS（逃逸）；F4（2 键）BLOCK |
| V3P | **谓语尾边界** | **FAIL×2** | P1/P2 PASS（逃逸）；P3 ctl PASS |
| FC | fail-closed 故障注入（六变体） | **FAIL×2** | FC1~FC4 全对（mask 层已修）；**FC5-sed-fail / FC6-grep-error = PASS(FAILOPEN)** |
| P-1/P-2 | 可移植性/bash 边界 | **PASS** | 沿 R2 结构（synthetic 永久面 :669-737 族+live 可见 skip+seen≥1；本轮测试 diff 新增 wrap/fault tests——Developer 声称，测试面细节见 §5 模块独立跑） |
| V4 | 原门保持 | **PASS** | 推测模式 verbatim（diff :592-595）；事实依据门/review 门零触碰 |
| V5 | 模块最终唯一独立跑 | 见 §5 | 46 测后台收齐 |
| V6 | blob 绑定 | **PASS** | 8efea943…/8efd64da… 实测一致 |

## 2. Findings（终轮阻塞项，全部 actual output）

### B1（P1·阻塞）签名门=纯语法计数，非 source provenance——伪造三键签名豁免 span 内真实肯定

- **位置**: `json_region_mask` `signature_ok`（键闭表计数 ≥3 → 整对象入 record 层）；record 层 span 剥离族（`(PASS|BLOCK)｜[^;]*` / `check "…"` / `check-quoted [^;)]*`）
- **实证**: `F1-forged3key-passspan=PASS`（`{"id":"#1","observed":"PASS｜我编造了测试结果;","raw":"x"}`）；`F2-forged3key-checkquoted=PASS`（literal 键+check-quoted span）；`F3-forged3key-checkraw=PASS`（output_as_captured+check 转义 span）；对照 `F4-forged-2key=BLOCK`（两键不足）——**键数阈值语法有效，但任何作者可自写三已知键包裹真实肯定声明**。真实行 G1（真签名+真引用载荷）PASS ✓——类对真数据有效，唯不可区分自伪造。
- **修复方向（供用户决策/后续票）**: 真 provenance 需结构外凭证（行级 EVD 行由机器写入的签名链/位置约束——如 record 对象必须整体占据 事实依据: 后唯一载荷+行首 EVD 列匹配机器行形态），或 span 剥除增加载荷约束（span 内不得含第一人称肯定起式），或将 record 豁免降为「复核告警+人工门」而非静默通过。

### B2（P1·阻塞）封闭谓语尾不约束尾后上下文——引用形后接背书续句逃逸

- **位置**: prose 层 E1 `(双否定|发现|边界|命名|引用)“stacked”(为边界|已实证|是攻击|是逃逸)` 剥除后不检查后续成分
- **实证**: `P1-closedtail-then-endorse=PASS`（`发现"不允许不编造"为边界，请照此要求必须遵守并当真执行`）；`P2-shixiang-then-endorse=PASS`（`…已实证，我要求把结果当作真实数据`）——尾后无 token 背书续句全免；P3（真引用+闭合尾+括注）PASS ✓。
- **修复方向**: 剥除后残句做封闭语法核验（残句限定为括注/行尾/标点收束等闭合形，含祈使/要求/把字处置式即拒），或该类引用降级为告警面。

### B3（P1·阻塞）fail-closed 未覆盖 sed/grep 管线腿——mask 守卫外仍 fail-open

- **位置**: helper 两 tier `printf | sed -E … | grep -Eq`（if 语境取 pipeline 末位退出；R3 仅对 `json_region_mask` 两处命令替换加了 `|| return 0`/空 prose 守卫）
- **实证**: `FC5-sed-fail=PASS(FAILOPEN)`、`FC6-grep-error=PASS(FAILOPEN)`——真实 mask 保持运行、fixture 内函数桩（sed return 1 / grep return 2，不卸不改系统工具）下，**实际肯定 payload 判 PASS**；grep exit 2（真错误）与 exit 1（无匹配）在 if 语境同判 false——错误被吞为"无术语"。
- **修复方向**: pipeline 拆步+显式错误区分（grep 2≠1；sed 非 0 → BLOCK），或 pipefail+逐腿状态捕获；与 R2 C6 同一故障传播原则的完备化。

**三项共同特征**：均为「语法形可满足而语义凭证缺失」面——与 R0→R3 一贯的 fail-closed/不可自授豁免原则冲突；round 3 仍存 → T2。

## 3. 前轮 findings 复审对照

| 前轮项 | R3 判定 |
|-------|---------|
| R2 B1 mask 层（分类无 provenance + mask 故障 fail-open） | **分类面部分修复**（签名门挡 unsigned/2 键形——N1/N8/F4 BLOCK；但伪造 3 键形开放→本 B1）；**mask 故障面已修**（FC1~FC4 ✓） |
| R2 B2 check-quoted 无 provenance | **部分修复**（unsigned N8 BLOCK；F2/F3 伪造签名形开放→并入 B1） |
| R2 B3 标记门背书滥用 | **部分修复**（裸 endorsement N7 BLOCK、P3 真引用 PASS；封闭尾后续句 P1/P2 开放→本 B2） |
| R2 补充件 C6 fail-closed（mask） | **已修**（FC1~FC3）；**残余面新发现**：sed/grep 腿（FC5/FC6→本 B3） |

## 4. 披露

- **我方本轮装置缺陷（2 处，已定位修复、权威 run 干净）**：①首版生成 echo 行缺闭合单引号（177 行吞 178-179 致 bash -n 拒绝——**未执行**）；②probes 循环相对路径在 CWD=repo 下未命中（该面首跑未执行，FC/V1 首跑有效）——改 `$REPO_ROOT/probes.txt` 绝对路径后全量重跑为权威。补丁脚本 `patch_r3.py`（write 工具零插值通道）+ 修正后 `r3probe.sh` 落隔离根。FC1 stderr "command not found" 为预期噪声（guard 转化为 BLOCK）。
- **Developer 侧（不代填）**：R3-2~4 literal 仍只结构摘要缺 outer pwsh 全文（原 shell 已 copy incidents 支持复查）——按其自留缺口引用；其自曝「完整伪造签名仍可逃」经本轮 F1~F3 实证为真（非推测）。
- **R2 报告纪律事件（如实纳入）**：我方在 R2 机录后追加编辑致 hash 漂移（8cdc→7615），Coordinator 经补充件保全+逐字节恢复（回执 13:42:37Z/13:43:36Z）——本报告引用的 R2 结论以原机 92 行版为准，C6/fail-closed 以补充件为准，两者区分标注。

## 5. 验证命令记录（five-env 全程；全部 literal/脚本/raw 落隔离根，收据 JSON 随本报告落盘）

| id | command 要点 | start(UTC) | end(UTC) | exit | affected/protection |
|----|-------------|-----------|----------|------|---------------------|
| C1 | blob/HEAD/staged/numstat+incidents 清单 | 13:56:59.94Z | 13:57:00.35Z | 0 | 只读 |
| C2 | hook 全 diff -U12 只读 | unknown | unknown | 0 | 只读 |
| C3 | 电池首跑（bash -n 拒——我方缺陷①，未执行） | 13:58 前后 | — | 1 | 缺陷①；SYNTAX gate 拦截 |
| C4 | 补丁 run（引号修复+FC5/FC6 注入；V1/FC 有效、probes 面未跑=缺陷②） | 13:59:38.68Z | 13:59:42.21Z | 1 | 隔离根；FC5/FC6 FAILOPEN 首次实证 |
| C5 | **权威全量重跑**（probes 绝对路径修复后；clean run） | 14:00:14.65Z | 14:00:28.44Z | 1* | *exit 1=SCRIPT_FAIL 预期标记（FC5/FC6/F/P 面）；V1 72/24/65 PASS；全部 label 判定见 §1 |
| C6 | 模块最终唯一独立跑（后台 job pwsh-20，raw Tee） | 14:00:47.35Z | 14:02:40.58Z | 0 | **Ran 46 tests in 106.831s — OK**；隔离 fix444r3-mod-d86f7764 |

roles 本轮已按 MUST 重载（code-review SKILL 全文+agents/code-reviewer.md :1-106 全读）。

## 6. 五维 + AI 专项

正确性 **FAIL(B1~B3)**（签名门/谓语尾/故障传播三面；核心否定族+双否定+unsigned 面正确）｜安全性 **FAIL(B1~B3)**（自授豁免通道+管线级 fail-open）｜可维护性 **PASS（带 P3）**（闭表纪律延续、注释因果完整；P3：键表/谓语尾表为维护面，扩展需同步溯源）｜性能 PASS（awk 双遍+sed 链单行级；模块 ~103s 级）｜测试覆盖 **PARTIAL**（wrap/fault tests 新增——模块结果见 §5；F1~F3/P1~P2/FC5~FC6 无红测=逃逸存活原因）。AI 专项：无 mock 残留/无业务硬编码/无幻觉 API/无 TODO/无过度实现。

## 7. 硬门槛自检

P0=0（阻塞=P1×3，终轮）✓｜5 维 100% ✓｜发现带级+位置+actual output ✓｜前轮逐条对照+补充件/原机区分（§3/§4）✓｜round+前轮引用 ✓｜事实红线（全部逃逸=实跑输出；Developer 缺口不代填；窗口终冻结绑定；我方两缺陷如实）✓｜T2 熔断执行（BLOCKED 终态，不自动 R4）✓

## 8. 机录与后续（Coordinator）

`review-record --task FIX-444 --round 3 --result BLOCKED --report docs/reviews/review-FIX-444-CODE-R3.md --reviewer 'Code Reviewer'`——**BLOCKED = 复审链终态（非通过）**，MUST 用户升级（T4）：三阻塞均为「语法形 vs 语义凭证」设计边界，需用户决策——(a) 接受指定残余并显式风险入账（每项用户点名）；(b) 后续票做结构外 provenance（行级机器签名/位置约束）；(c) record 豁免降级为告警+人工门。`unresolved_blockers=3`。
