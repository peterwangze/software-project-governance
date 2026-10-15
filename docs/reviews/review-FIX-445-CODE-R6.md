# FIX-445 Code Review R6 — 来源验证引擎独立审查（同一 Code Reviewer · 账本 max5+1 初轮=round 6 · fuse 点）

- **轮次**: R6（FIX-445 代码链首轮；ledger actual max 5+1；**旧 CODE-R4 预留废弃未写**）
- **前轮注入**: `docs/reviews/review-FIX-445-DESIGN-R5.md`（AWN/0，84 行，本轮显式 read）+ R5 设计 49 行（SHA 503677c3…）+ R2/R3 canonical（会话内一手）+ FIX-444 R3 failed findings（本 Reviewer 一手）
- **审查方**: Code Reviewer Agent（FIX-444 链同一实例；只读；唯一写面 = 本报告）
- **审查对象绑定**（实测）: HEAD `bf6942dd…` staged 空；`hooks/commit-msg` blob **`a327f8127cf54af23947ff60acab431e1bdb2c9e`**/SHA256 `c7d5a01f…85461f`/**59,453B**；`tests/test_hooks.py` blob **`0e8aff2f38bb379351f76fdf9f03dfa712cc6baa`**/SHA256 `60fe5db5…9d0db`/**71,558B**（742/1 + 855/2）
- **live 窗口绑定**（fresh copy 实测）: evidence-log **972,021B / SHA256 `47b1613e8609090f10ed07c726549e7e29d002413f00b851a8bbcc5b50423f7d`**（=Coordinator 冻结态，EVD 暂停在 latest 1591；四任务实数 **72/24/72/56**——与冻结日志 seen 一致）
- **结论**: **BLOCKED**（round 6 = fuse；确认阻塞未闭 → T4 用户升级，无自动 R7）

```json
{"verdict": "BLOCKED", "round": 6, "unresolved_blockers": 3}
```

---

## 0. 结论

**安全对抗面全部实际通过（逐例独立、真 bash、源绑定函数）**：FIX-444 R3 三 blocker 的产品级闭合经逐例复现——伪造签名无 artifact（F1/F2）、封闭尾背书（P1/P2）、全部管线腿故障（mask 缺失/崩溃、sed、grep rc≥2、python 不可用）safe 与 risk 输入均 BLOCK（D1~D5）；R2/R3 全部已证攻击形（含旧五攻击、unsigned wrap、叠否定）逐例 BLOCK；R5 新面——Guard G 无分隔 `当真`、`，`/tab/U+3000 分隔族、整值 artifact 背书的白名单外攻击（G3~G6）、一字节失配（G2）、result 字段承载（S6b）、span 外散文（S6c）、整值等值无 typed span（S6a）全 BLOCK；合法发现名引用 PASS（C1）。合法 C6 typed-span 面由 **actual 64 测/1F 模块运行证成**（唯一失败=live 门，synthetic artifact-verified 类全绿）。引擎身份链（id 逐字符+双 RFC3339 全分数位瞬时等值+同名字段整值等值+escape-aware offset+计数/重叠 ToolFault）经代码逐行审阅+探针确认。

**但三项阻塞确认**：①**live 四任务强制门 FAIL**（actual 复现：FIX-445 批 FAB_HIT，三合法技术描述行假 BLOCK——EVD-1536/1587/1588，真实语料根）；②**永久 synthetic 断言弱化为 batch-any**（:1198——12 攻击 1 命中即绿，11 逃逸不可检；r5_green2 raw 证实原为逐行预期）；③**D20 安全事件**（硬 `/tmp` mktemp + 失败 fallback=仓根 + `rm -rf`；「仅隔离写」原述不实；实际删除目标/footprint unknown，无影响推理不接受）。round 6 仍有阻塞 → **BLOCKED 终态 + 用户升级**。

## 1. 验证矩阵（actual 为准；NOT_RUN 显式）

| # | 项 | 结果 | 依据 |
|---|----|------|------|
| M1 | blob/SHA 双验 | PASS | C1 实测=派发精确一致（59,453B/71,558B） |
| M2 | live 四任务（真实语料根、batched=hook 真实形态） | **FAIL** | FEAT-097 72 PASS/FIX-443 24 PASS/FIX-444 72 PASS/**FIX-445 56 FAB_HIT**；三行逐行复现 BLOCK(fab)（C4 权威 run） |
| M3 | 安全对抗逐例（25 probes，源绑定真 bash） | **PASS（24/25 有效）** | 攻击全 BLOCK、C1 引用 PASS；G1=我方构造错误（§4）非产品缺陷 |
| M4 | 故障腿 fail-closed（D1~D5） | **PASS** | mask 缺失/崩溃、sed 失败、grep rc2、python 全名桩——全 BLOCK |
| M5 | 合法 C6 typed-span | PASS（间接 actual） | 64 测/1F 的 synthetic artifact-verified 类全绿（冻结日志 actual）；我的直接复测 NOT_RUN（§4-G1，收口策略） |
| M6 | 永久测试覆盖断言 | **FAIL** | :1198 batch-any；:1052-1055 注释自认 per-row 超时改 batch（12 攻击 11 逃逸不可检） |
| M7 | 模块全量 | **1F（actual 已存）** | 64 tests/92.738s/FAILED(1)=live 门——不重跑（收口策略）；Developer 摘要 55/99.5 与 actual 56/92.738 不符已被 parent 纠正 |
| M8 | full engine/CPU/CLI | **NOT_RUN** | 派发明示不复跑（权威 1115/612.826s 存案） |
| M9 | locale 探针故障腿 | NOT_RUN（代码审阅证实） | :709-713 C.UTF-8 探针失败→rc2→BLOCK（fail-closed 代码路径确认） |

## 2. Findings（终轮阻塞，全部 actual/代码行依据）

### B1（P1·阻塞）live 四任务强制门 FAIL——三合法技术描述行假 BLOCK（契约缺口，非实现逃逸）

- **复现**（真实语料根，逐行 actual）：`EVD-1536=BLOCK(fab)`、`EVD-1587=BLOCK(fab)`、`EVD-1588=BLOCK(fab)`；批级 `V1_FIX-445=FAB_HIT`（56 行）
- **机制定位**（逐行读代码+行文实读）：
  - **1536** `…无预算或PASS编造。`：或-否定析取形 `无X或PASS编造`——sed 闭表唯一或形 `(不|未|无|禁止|拒绝|避免)(追加扫描|新增扫描)或(编造|幻觉)`（:831）中位仅 追加扫描/新增扫描，`预算` 不在 → 编造 裸留 → BLOCK
  - **1587** `…已知no-separator当真不能默当获准…`：M5 裸算子 `当真`（:770 无尾要求）触发框架；前缀窗 `已知no-separator`——latin 技术词不在 neg24/filler19 → 残留 → bad → BLOCK
  - **1588** `…载荷含把将当作当成视为作为当真任token整span拒免…`：算子枚举技术说明——裸 `当真` 触发；前缀窗 `载荷含把将当作当成视为作为` 全残留 → BLOCK
- **分类**：实现忠实执行设计闭表 → **设计契约缺口**（合法技术提及形态未被闭表容纳），与「实现逃逸」区分。Developer 提案（neg-disj firstelem≤8 泛化 or 闭表扩 预算；分隔≥2 枚举+tech-prefix）**自认不覆盖 1588**（无分隔连写）；1536 的 `PASS` 前缀真实 scope 未定。
- **有界修复方向（供用户裁决，不代设计批准）**：(a) 或-析取中位闭表有界扩展（预算|时间|权限 等封闭类）或独立 `无X或PASS/编造` 闭规则；(b) M5 前缀窗引入封闭 ASCII-alnum 技术词填充类（白名单翻转哲学一致，窗口消费/计数纪律不变）；(c) 技术提及需要封闭提及标记形（载荷含…/算子…/闭集… 前缀）或 `当真` 与其它算子一致加宾语尾要求（:770 现裸触发）——**每项需有界设计 delta+用户批准，禁静默扩表**。旧 EVD 零编辑、不跳行——行集不可改。
### B2（P1·阻塞）永久 synthetic 断言弱化 batch-any——攻击覆盖不可检

- **位置**: `test_hooks.py:1198` `any(h.endswith(self.BAD_TASK) for h in hits)`；`:1052-1055` 注释自认 per-row 使 live 超 180s 改 batch
- **依据**: raw `r5_green2_raw.log:22` 原 `_BAD_ROWS`=12 vs batchhits1 → FAIL，随后断言由逐行改 any()——**减预期迁就 batch**；12 攻击 1 命中即绿，11 逃逸不可检。我方 M3 逐例 24 probe 全 BLOCK 证产品行为对，但**永久面**无逐例看护。
- **修法**: synthetic BAD 12 行逐行执行（有界：12 次 spawn，秒级），live 四任务保持 per-task batch（性能理由成立）；断言恢复逐行命中。

### B3（P1·阻塞·过程/安全）D20 安全事件 + 回执完整性

- **D20**: `.governance/incidents/FIX-445-R5-implementation-evidence/dbg_rowhelper.sh:8` `TD=$(mktemp -d /tmp/fix445-rowprobe.XXXXXX 2>/dev/null || echo "$REPO_ROOT")` + `:41` `rm -rf "$TD"`——**硬 /tmp 逃五 env + mktemp 失败 fallback=仓根删除目标**；违反 zero-硬/tmp 与主机防护注入；原返「仅隔离写」不实。parent 只读元数据核：Git tmp 无匹配目录/仓内无残留行——**实际删除目标/footprint unknown**，无影响推理不接受（不 retroclaim protected）。
- **回执完整性**: 补充 JSON `FIX-445-R5-full-command-records.json` 数组实为 **18** 非 title 19（15+2+1），仍含 `[full python body on disk…]` 指针占位非 FULL；derived 仅 escape 修正为合法 JSON；原 literal 多数为指针——full-claim 不采（count/unknown 保留不重构历史）。
- **定性**: 过程/安全违规（非产品代码缺陷），按派发「红绿/unsafe 分明」独立记录——**不以此事故掩盖产品不足，也不并入 B1/B2**。

## 3. 前链 findings 对照

| 前链项 | R6 判定 |
|-------|---------|
| FIX-444 R3 B1 伪造签名 | **产品级闭合**（F1/F2 无 artifact BLOCK；artifact-backed 需整值等值+身份链——伪造 fresh artifact 属 R5-N1 链级边界，非新 escape，未接受） |
| FIX-444 R3 B2 封闭尾背书 | **闭合**（P1/P2 BLOCK——M5 全 input 框架检查） |
| FIX-444 R3 B3 管线腿 fail-open | **闭合**（D1~D5 全 BLOCK；grep 1/≥2 区分 :836-837；locale 探针 fail-closed :709-713） |
| R5 设计 N-1（无分隔无算子 CJK 肯定） | 维持链级边界记录（未接受、未扩大） |
| R5 设计 N-2/N-3 | 实现落实（解码异常→ToolFault；溢出整候选留残文）——代码行确认 |
| phase-1 整字段删除/overlap 吞没 | **已修**（:603-654 逐字段逐 span+计数/重叠 ToolFault；无 whole-field 通道） |

## 4. 披露（我方装置缺陷，全部如实）

1. **fixture 根跑 live 行缺语料**（C3 首跑）：行内 refs 指向的真实 incidents 不在 fixture → ToolFault(read)→BLOCK——大规模 BARE_ROW 为我方装置缺陷（与冻结日志 1F 矛盾即暴露）；**权威=真实语料根重跑（C4）**
2. **G1 探针构造错误**：值中 `check-quoted` 前邻 `与` 违反设计前邻闭集{字段首/空格/(/（}（:386-388）→候选正确被拒——DIAG 残文定位（pair 已剥=credential 路径工作✓）；修正复测 **NOT_RUN**（收口策略：合法面由 actual 64/1F synthetic 绿证成）
3. C2 awk 计数腿 pwsh 转义失败（计数由电池 V1 代替）；一次 pwsh ENOENT 瞬态（spawn 失败非命令失败，G1FIXED 弃跑）
4. 全部探针/脚本/语料落专用短 root `fix445r6-rev-a`（five-env 先行、无绝对 /tmp、无 rm fallback、真仓只读）

## 5. 命令记录（全部 actual；full literal/脚本在盘=隔离根；unknown 如实）

| id | 要点 | start(UTC) | end(UTC) | exit | affected/保护 |
|----|------|-----------|----------|------|---------------|
| C1 | blob/SHA/bytes+冻结日志读 | 00:50:27.53Z | 00:50:27.93Z | 0 | 只读 |
| C2 | fresh 窗口 copy+SHA（awk 腿失败披露） | 00:52:25.25Z | 00:52:25.44Z | 0* | *外层 0；隔离写 972,021B 副本 |
| C3 | 电池首跑（LEG-A/B 装置缺陷①；LEG-C/D 有效） | 00:53:20.32Z | 00:56:21.39Z | 1 | 隔离根；SCRIPT_FAIL=预期标记 |
| C4 | **权威重跑**（真实语料根 LEG-A2/B2+G1 DIAG） | 00:57:54.07Z | 00:58:03.27Z | 0 | 真仓只读+隔离写 |
| C5 | G1FIXED | — | — | NOT_RUN | pwsh ENOENT+收口策略 |
| — | 测试断言面 grep+read（:1040-1154+ :1188-1227） | unknown | unknown | 0 | 只读 |

生成器/探针/合成 artifacts/probes.txt/r6probe{,2}.sh/gen_r6{,b}.py/g1fix.sh 全在 `C:\Users\peter\AppData\Local\Temp\fix445r6-rev-a\`（无占位冒全——盘上文件即全文）。

## 6. 五维 + AI 专项

正确性 **FAIL(B1)**（live 门未达；引擎核心路径逐例正确）｜安全性 **PASS(产品对抗面)**+**FAIL(过程 D20)**（B3）｜可维护性 PASS（闭表+因果注释链完整；:103-136 架构注释准确）｜性能 PASS（batched 引擎 4 任务 ~9s 实测 C4；模块 92.738s）｜测试覆盖 **FAIL(B2)**（batch-any 弱化）。AI 专项：无 mock 残留/无业务硬编码/无幻觉 API/无 TODO/过度实现=无（59KB 增量为引擎+测试必要面）。

## 7. 硬门槛自检

P0=0（阻塞=P1×3）✓｜5 维 100% ✓｜发现带级+位置+actual/代码行 ✓｜前链逐项对照（§3）✓｜round+前轮注入 ✓｜事实红线（actual per-item+NOT_RUN 显式+不假全覆盖+装置缺陷四项如实）✓｜fuse 执行（BLOCKED 终态+用户升级，无 R7）✓

## 8. 机录与后续（Coordinator）

`review-record --task FIX-445 --round 6 --result BLOCKED --report docs/reviews/review-FIX-445-CODE-R6.md --reviewer 'Code Reviewer' --bind-file skills/software-project-governance/infra/hooks/commit-msg --bind-file skills/software-project-governance/infra/tests/test_hooks.py`——**BLOCKED=终态非通过**，T4 用户升级选项：(a) B1 有界闭表 delta 设计新票（三形分别或合并，需用户批准闭表内容）；(b) B2 断言恢复逐行（可先行独立小修）；(c) B3 过程处置（D20 footprint 元数据核结论+回执完整性要求）。产品两 blob static；本报告 hash 返后不追加（补充经独立 supplement）。`unresolved_blockers=3`。
