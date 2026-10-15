# FIX-445 设计 R1 — 有界来源验证修订版（D-1~D-5 精确修复）

- **性质**: `docs/design/FIX-445-source-verification.md`（R0，SHA256 `59f318d4…d22e3f2`/33,525B）的修订版本，经 `docs/reviews/review-FIX-445-DESIGN-R0.md`（NEEDS_CHANGE/unresolved_blockers=5）§8 新版本通道产生。R0 doc 与 R0 review 均静止零改；本文件是本轮唯一写面；产品两 blob（8efea943…/8efd64da…）零写。
- **授权**: DEC-334 有界来源修复（受限程序性设计修复，无需额外用户许可）；不推未来架构、不做 risk acceptance、不自称 APPROVED。
- **R1 新增事实全部来自本轮只读验证（§8 收据）与 R0 review 实测**；无新探索、无 module/engine 运行。

## 0. Finding → 修订映射

| R0 Finding | 修订落点 | 状态 |
|---|---|---|
| D-1 豁免凭据弱于所需（span+anchor 重组/字段角色无划界/CH-2 无理由推迟） | §2（凭据规则整体重造）+ §2.6 实测验证表 | 已修（规则收紧+真实 field-match 实证） |
| D-2 背书框架被句读截断 | §4（全 input 作用域） | 已修 |
| D-3 live 三任务硬编码 | §6（四任务） | 已修 |
| D-4 C7 哈希「不可复验」事实错误 | §5（正例更正） | 已修（引 Reviewer/Coordinator 双实测） |
| D-5 语料路径缺真实解析包含 | §3（resolved containment） | 已修 |
| （Coordinator 补充）`.governance` gitignored——R0 §2「diff 可见」措辞错误；无记录的 step-budget 自claim | §2.7 边界更正；§9（预算自claim 撤除） | 已修 |

R0 通过面（review §4：R6/B3 闭合、R7 保守处理、R2 闭语法方向、威胁模型诚实骨架、兼容计划骨架、过程纪律）**全部保留**，本文只述变更与增量，不重复 R0 长叙述。

## 1. 核心凭据规则（D-1 修复——canonical 全量逻辑，取代 R0 §5 R1/R3/R4）

豁免的**必要且充分**凭据 = 以下五条件全部成立；任一不成立 → 该 span 无豁免、按裸词进入 risk 扫描：

**C-1 严格解析路由（取代签名键门——键闭表/`signature_ok`/≥3 阈值整体删除，不保留为阈值）**
- M1a（awk，既有 brace 扫描器保留、签名逻辑删除）检测行内 `{…}` 候选区；无候选 → 纯 prose 路径（不依赖 python，C1/C2 行为零变化）。
- 有候选 → 内嵌 python（标准库 `json.JSONDecoder.raw_decode`，两文件内嵌、无新文件依赖）逐候选严格解析：解析成功且为 JSON object → record 路径；解析失败 → 该区按 prose 渲染（沿用现行语义：prose 无任何 call/verdict 豁免）。
- python 腿任何失败（缺解释器/非 0/崩溃/乱码）→ 该行 BLOCK（fail-closed，含本来会 PASS 的输入；诊断注明缺 python）。python 为 governance hook 家族既有依赖（post-commit write-guard 已用），非新增外部依赖。

**C-2 记录身份绑定（same identified record）**
- citing record 与 artifact record 的 `id` **逐字符相等**，且 `utc_start`、`utc_end` **瞬时相等**（RFC3339 解析后比较——字符串精度差如同瞬时尾零 `.537239Z` vs `.5372390Z` 判等；非字符串模糊匹配）。
- artifact 候选集 = §3 语料中所有严格解析出的含 `id` 对象。无身份匹配 → 无豁免。

**C-3 同名字段整值包含（same field, complete value）**
- 豁免 span 所在的 citing record 字段值 V，经**闭合显示归一映射**后，须整体（整值，非任意子串）包含于身份匹配 artifact 对象的**同名字段**值：`ext(V) == A[F]` 或 `ext(V) ⊆ A[F]`（连续包含，V 无作者自写字节）。
- 闭合归一映射（仅用于验证比较；**术语/背书扫描永远作用于行原文**，归一永不洗扫描目标）：`｜ → |`；`〈反引号〉 → \``。探测两趟：原文直探 → 归一探。
- 归一映射来源：机器写入 evidence 表时的显示转义（markdown 表格安全），本轮实测由 C3/C5 的 12 字符差（各 3 处反引号 ×4 字符）算术+直证钉死。

**C-4 span 类型 ↔ 承载字段闭映射（从七类真实归纳；扩展需新票+溯源）**
- verdict span `(PASS|BLOCK)｜…` → 仅 `observed`；
- check/pattern span（`check "…"`/`check \"…\"`/`check-quoted …`/`编造\|幻觉` 对）→ 仅 `literal` | `output_as_captured`；
- **结论性字段（`result`/`affected`/`unknowns`/`protection` 类）永不承载任何豁免**——实测 EVD-1463 的 `result` 与 artifact EQUAL-raw，仍不授予任何豁免。

**C-5 豁免执行（M3 修订——逐实例、按位置，非字符串全局替换）**
- R0 的 `${text//"$span"/}` 全局替换形**废弃**：一个字段引用获证不得清掉另一字段/prose/其它 record 中同字面的未获证出现。实现：内嵌 python 在严格解析后按**解析 offset/字段边界构造残文**——span 识别在行原文上定位（闭语法 R0 §5 R2 四类+120 字符上界，保留不动），字段值验证经 ext 归一比较（§1 C-3），但**删除只作用于该获证实例在行原文中的精确字节区间**；同值多处出现时**每个 instance 各自验证、各自豁免**（instance 的豁免仅当其所在字段通过该 record 的 C-1~C-4）。
- 一致性校验：删除区间数 == 验证通过的 span 实例数；offset 漂移/重构失败/计数不匹配 → BLOCK（拒，不降级为全局替换）。
- 位置算术永远基于行原文（ext 归一是变长映射，仅用于验证比较，不参与删除定位——防归一洗位）。
- 删除后：record 残文、其余字段（含 result/affected 全文）、prose 层全文、未获证同字面出现 → 全部继续 risk 检查（否定核+裸词+§4 背书）。**结果/结论永不因来源豁免免检；缺 safe 凭证不得让载荷空过（no payload empty-pass）。**
- 来源管线（format/parse/reader/normalizer/offset 计算）任何错误 → closed（BLOCK），沿 §3 全腿语义。

**闭合后的残余（取代 R0 CH-2 的「推迟」——现在就收紧到位）**：伪造者必须逐字复制真实 artifact 记录的身份（id+双 utc 瞬时）+同名字段整值（或其连续真子串）——所获豁免仅限该引用载荷，与合法引用**信息上不可区分**，且一切作者自写字节永不获豁免。这是任务边界（无新签名权威）内的闭合极限，**非用户 risk acceptance**；可见性面更正见 §2.7。

### 2.6 实测验证表（D-1 要求的真实 field-match；本轮只读直证，非假设）

| 行 | 身份（id+utc 瞬时） | 承载字段 | 整值关系 | 判定 |
|---|---|---|---|---|
| EVD-1463（C3/C4） | ✓ `#1 old-pattern bash replay (defect proof)` + 12:27:10.2692827Z/…7367672Z @ `FIX-444-command-records.json` | `literal` | **EQUAL-ext**（1321→归一 1309 = art 1309） | 4 处术语载荷全可豁免 |
| EVD-1481（C5） | ✓ `R3-adversarial-9-cases` + 12:40:21.5532478Z/…3957955Z @ `FIX-444-reviewer-R0-command-records.json` | `observed`＋`literal` | **EQUAL-normalized**（176=176）＋**EQUAL-ext**（891→879=879，含双方一致的 `<python …>` 占位——占位文本两侧逐字同，非行侧独有变形） | 6 处 verdict 载荷全可豁免 |
| EVD-1483（C6） | ✓ id 逐字同 + utc 瞬时等值（raw `.537239Z` vs `.5372390Z`——机器写入精度差，瞬时相同）@ 同 artifact | `observed` | **EQUAL-raw**（211=211，全角原样两侧一致） | 4 处术语载荷全可豁免 |
| （对照）EVD-1463 `result` | — | 非承载字段 | EQUAL-raw | **不授予任何豁免**（C-4 划界实证） |

三行旧 EVD 零编辑即满足全部凭据——兼容性是实测结论，不是假设「零成本」。

### 2.7 威胁边界更正（Coordinator 指出，R0 §2 措辞错误）

R0 称伪造 incidents「git diff 可见」——**错误**：`.governance/` 是 gitignored，git diff 不自动显示。更正为：伪造面的可见性依赖 (a) 仓内持久 artifact 的存在性本身、(b) 受管 ops ledger（`governance-store-ops.json`）与机器写入链、(c) 独立证据审查（Reviewer/Coordinator 对 artifact↔EVD 的交叉核对，如本轮 §2.6 与 R0 review D-4 的双侧实测）。本设计**不是密码学真实性**、无新签名权威；上述可见性是审查面承诺，不是 Git 机制承诺。

## 3. 语料路径与读取边界（D-5 修复）

- **语料构造**（沿用 R0：行内 refs 提取 ≤8 + `.governance/incidents/*${TASK_ID}*` glob ≤24，总 ≤32；排除 evidence-log 自身；目录闭前缀 `docs/reviews/`、`.governance/incidents/`、`.governance/reports/`；拒绝绝对路径与含 `..` 者）。
- **新增 resolved containment（必改项）**：每个语料文件读取前，内嵌 python `os.path.realpath` 解析（跟进 symlink/junction），要求 resolved 路径仍在 `realpath($REPO_ROOT)` 之下（前缀+分隔符判定）；解析抛错/出仓 → **丢弃该路径 + 计 `path-unresolved` probe-error 诊断**（保守拒绝，不崩溃）。
- **hardlink 语义**：hardlink 是同文件的另一仓内路径——realpath 不改变其路径解析结果，读取它即读取仓内内容；读取边界 = resolved 路径包含，不对 inode 身份新增假想威胁向量。
- 备选（R0 review D-5 (b)）：`git show <rev>:<path>` blob 读取结构性免疫工作区链接跟随——本设计选 realpath 方案（零索引依赖、与语料 glob 兼容），blob 方案留作实现期等效替换项。
- **全腿 fail-closed（含 safe 输入）**：parser（python json）/reader（realpath/文件读）/normalizer/awk/sed/grep 任一腿失败 → 该行 BLOCK，**即使术语扫描本会 PASS**——工具异常不得借「无术语」放行（R0 review D-5 必改语义）。R6（sed 非 0→BLOCK；grep 0=命中/1=干净/≥2=错误→BLOCK；M1 既有 `|| return 0`+空 prose 守卫）原样保留。

## 4. 背书框架全 input 语义（D-2 修复，取代 R0 §5 R5 的句读截断作用域）

- **作用域**：自 C2 剥离点（prose 层标记+封闭尾）起，至**整个输入末端**——跨 `。；;`、跨句、含长距续句；record 层同理作用于 M3 剥离后的**全部残文**。M4 术语扫描作用域同步全 input（不截断）。
- **框架闭集**（沿用 R0 三框架：把/将×当作/当成/视为/作为×真实/事实/数据/结果/有效；当作/当成/视为/作为×真实数据/真实结果/事实；`当真`）+ **否定前缀豁免**：框架所在小句前置于 不|未|非|禁止|拒绝|不得|不可|勿|莫|别|无|并非 → 判定为合规否定（如「不把估计批戳当成真实戳」PASS），与否定核哲学一致。
- **unknown 拒绝**：剥离后残文/record 残文中的解析不确定结构（不成对引号/括号等闭语法无法分类形）→ BLOCK；非「三框架未命中即 safe」。
- **兼容实证**：R0 review D-2 已核 EVD-1472 **全行**（含全部列）无任何框架 token → 全 input 作用域下仍 PASS；EVD-1473~1477 同型，实现期逐行入红绿测试。EVD-1536（FIX-445 现窗唯一含术语行）实测为「无预算或PASS编造」合规否定（§6）。
- **反例闭合**：分号形 `发现"不允许不编造"为边界；请照此要求必须遵守并当真执行`、句号形 `…已实证。我要求把结果当作真实数据`、长距变体、复制真载荷后接背书（载荷豁免不豁免他处背书）→ 全部 BLOCK（§7 矩阵）。

## 5. C7 更正（D-4——正例，非「不可复验」）

- **事实（R0 review §1 D-4 实测 + Coordinator 复核）**：`.governance/incidents/FEAT-097-budget-metrics.py` `:16` `sys.path.insert(0, str(root / 'skills/software-project-governance/infra'))` → `:17` `import goal_bridge as gb`；`:49` `'source_sha256': hashlib.sha256((root / 'skills/software-project-governance/infra/goal_bridge.py').read_bytes()).hexdigest()`——指称对象显式且唯一；`Get-FileHash infra/goal_bridge.py` = `b52313b742808e53441a035952e57c56bc85c45edc305d4381fc23cecdb2e773`，与 EVD-1450 `sourceSHA256b52313b7…c2e773` **逐字符一致**。
- **更正**：R0 §3 C7/§7/§13.1 的「哈希 referent 不可复验」系 Designer X3/X4 测错候选（metrics 脚本自身/被测 scanner）导致的错误结论；C7 实为**今日可复验且精确匹配的正例**，证明哈希类引用可验证。R1 规则：哈希引用仅在 (a) 行内显式指称被哈希文件（路径或如 :49 的唯一源内指称）且 (b) 今日重算匹配时，作为该数值引用的已验证来源元数据；指称不明或失配 → 保守不豁免（不补造历史状态）。正例改文不改变 unknown 保守语义。
- EVD-1450 行术语均为 prose 否定（C1 路径），哈希绑定是其来源元数据正例，不涉豁免。

## 6. live 四任务（D-3 修复）

- `RealEvdStep12ReplayTests` 任务集扩为 **FIX-444 / FEAT-097 / FIX-443 / FIX-445** 四任务全量行、零 skip；FIX-445 行同样过全规则（其语料 refs+task-glob 天然含本票 `.governance/incidents/FIX-445-*` 与 `docs/design/FIX-445-*` 关联 artifact——由 Coordinator 机写）。
- **FIX-445 现窗实测分布**（本轮只读）：15 行（EVD-1536~1550 族）；含术语 1 行 = EVD-1536，形态为 prose 合规否定「…无预算或PASS编造。」（C1 类，has_record=False）→ 预期 PASS。矩阵补此行；后续新增行的类分布由 live replay 机证，不人工宣称。

## 7. 修正后预期矩阵（**设计预期——产品未实现，不称实现通过**）

| # | 输入 | 预期 | 机制（R1 规则引用） |
|---|---|---|---|
| F1/F2/F3 | 伪造三键形（`#1` 短 id/无 utc） | **BLOCK** | C-2 身份绑定失败（不再依赖 anchor 长度偶然） |
| **α（D-1 反例）** | 真 id + `output_as_captured` 含 check span + `result:"复测通过"` | **BLOCK** | C-3 同名字段整值包含失败（artifact 无该字段/不含该值）；result 永不承载（C-4）；「复测通过」结论照检 |
| **β（D-1 反例）** | 真 id + `result:"BLOCK｜韩国编造了数据"` | **BLOCK** | C-4：verdict span 仅 `observed` 承载；result 同值亦不豁免 |
| 前后缀拼接 | 真整值+` ; 我编造了X` 追加 | **BLOCK** | C-3 整值包含失败（作者字节） |
| 字段搬运 | check span 放入 `result`/`affected` | **BLOCK** | C-4 闭映射 |
| n1/n8/F4 | 单/双键包裹 | **BLOCK** | 解析为 object → C-2 失败 → 无豁免（键表已删，非键数判定） |
| 未闭合/坏 JSON 包裹 | `{...` 等 | **BLOCK**（含术语时） | C-1 解析失败 → prose → 无豁免 |
| **分号/句号/长距背书** | §4 三变体 | **BLOCK** | 全 input M5 |
| **复制真载荷后背书** | 已验证 observed + 他处 `当真` | **BLOCK** | 载荷豁免不豁免全 input 背书 |
| **合规否定框架** | `不把估计批戳当成真实戳` | **PASS** | 否定前缀豁免 |
| P1/P2/n7/v-endorse | R3 原攻击集 | **BLOCK** | §4（含尾不匹配 closed-tail 形沿用 R0） |
| FC1~FC6 | mask/sed/grep 故障注入 | BLOCK×6 | R6 原样 + §3 全腿 fail-closed（含 safe 输入） |
| **symlink 出仓语料** | 仓内 symlink→仓外文件 | **BLOCK**（该来源拒绝）+`path-unresolved` 诊断 | §3 resolved containment |
| A1~A5/V2/affirm/mixed/dneg | 旧攻击/拒绝集 | **BLOCK** | 原语义零弱化（R0 通过面） |
| C1（19+1 行，含 EVD-1536） | prose 否定 | **PASS** | 否定核不动；C1/C2 路径不依赖 python |
| C2（6 行） | EVD-1472~1477 | **PASS** | 全 input 无框架（1472 Reviewer 已核；余实现期入测） |
| C3/C4/C5/C6 | EVD-1463/1481/1483 | **PASS** | §2.6 实测身份+同名字段整值 |
| C7 | EVD-1450 | **PASS** | prose 否定 + 哈希正例元数据（§5） |
| live 四任务 | 全量真实窗口 | **PASS（实现后机证）** | §6 |

## 8. 本轮命令收据（R1 轮全量；R0 轮收据已在 transcript 全量返程，不重复）

| id | 命令 | UTC | exit | 结果要点 |
|---|---|---|---|---|
| V1 | pwsh→python here-string（evidence-log 三行记录抽取 + 双 artifact 加载 + id/utc/字段关系判定；完整 body 见 transcript，与本 doc §2.6 一致） | 14:54:53.4291741Z→14:54:53.4982238Z | 0 | 1463/1481 身份 YES；1463 literal FAIL(1321/1309)、1481 observed EQUAL-normalized、1483 身份 NO（暴露 utc 精度差） |
| V2 | 同验证目标的加详版 | 14:56:10.1632330Z→14:56:10.2421221Z | **1** | **SyntaxError（我方残留占位行——解析期失败，零输出，未执行任何检查）；如实记录，不删** |
| V3 | V2 修正（去占位行；walker 仍带 R5 过滤缺陷） | 14:56:22.1015629Z→14:56:22.1654391Z | 0 | 1483：id 逐字同、observed EQUAL-raw 211=211、utc_start raw 差/utc_end 同；1463/1481 literal 段未执行（walker 缺陷） |
| V4 | 终版（通用 walker + 瞬时时间戳比较 + EVD-1536 ascii 上下文） | 14:57:14.2279607Z→14:57:14.2895522Z | 0 | **1463 literal EQUAL-ext(1309=1309)、1481 literal EQUAL-ext(879=879)、1483 utc 瞬时等值 True/True、EVD-1536=「无预算或PASS编造」否定** |

- V4 完整 literal（权威版；V1/V3 为其子集/变体，差异如各自行所述，全部 body 保存在会话 transcript 可得）：
```powershell
$t0=(Get-Date).ToUniversalTime().ToString('o'); $py = @'
import json, re
from datetime import datetime
repo = r"D:/AI/agent/claude/coding/project_management_workflow/"
lines = open(repo + ".governance/evidence-log.md", encoding="utf-8").read().splitlines()
dec = json.JSONDecoder()
def rowrec(l):
    i = l.find('{"', l.find("事实依据"))
    if i < 0: return None
    try: return dec.raw_decode(l[i:])[0]
    except Exception: return None
ext = lambda s: s.replace("\uff5c","|").replace("\u3008\u53cd\u5f15\u53f7\u3009","`")
def load(path):
    data = json.load(open(repo+path, encoding="utf-8")); out=[]
    def w(o):
        if isinstance(o,dict):
            if isinstance(o.get("id"),str): out.append(o)
            for v in o.values(): w(v)
        elif isinstance(o,list):
            for v in o: w(v)
    w(data); return out
inst = lambda ts: datetime.fromisoformat(ts.replace("Z","+00:00"))
for evd, artf in (("EVD-1463",".governance/incidents/FIX-444-command-records.json"),
                  ("EVD-1481",".governance/incidents/FIX-444-reviewer-R0-command-records.json")):
    l = next(l for l in lines if l.startswith("| "+evd+" |"))
    rec = rowrec(l); cands=[a for a in load(artf) if a.get("id")==rec.get("id")]
    for a in cands:
        rv, av = rec.get("literal",""), a.get("literal","")
        rel = "EQUAL-raw" if rv==av else ("EQUAL-ext" if ext(rv)==ext(av) else "FAIL")
        print(evd,"literal:",rel,"len_row",len(rv),"len_art",len(av),"ext_len",len(ext(rv)))
        print("  utc instants equal:", inst(rec["utc_start"])==inst(a["utc_start"]), inst(rec["utc_end"])==inst(a["utc_end"]))
r5row = rowrec(next(l for l in lines if l.startswith("| EVD-1483 |")))
r5art = [a for a in load(".governance/incidents/FIX-444-reviewer-R0-command-records.json") if a.get("id")==r5row.get("id")][0]
print("EVD-1483 utc instants equal:", inst(r5row["utc_start"])==inst(r5art["utc_start"]), inst(r5row["utc_end"])==inst(r5art["utc_end"]))
l1536 = next(l for l in lines if l.startswith("| EVD-1536 |"))
for mm in re.finditer(r"编造|幻觉", l1536):
    s=max(0,mm.start()-40); e=min(len(l1536),mm.end()+40)
    print("  CTX:", ascii(l1536[s:e]))
'@; $py | python -; $code=$LASTEXITCODE; $t1=(Get-Date).ToUniversalTime().ToString('o'); "START=$t0"; "END=$t1"; "EXIT=$code"
```
（V4 中 1483 observed 判定沿用 V3 的 EQUAL-raw 直证；读文件面 = evidence-log + 两 incidents artifact，全只读；另 read 工具读 R0 review 全文 113 行。）

## 9. 蓝军/替代/纪律增量（不重复 R0 §9/§10）

- **CH-2 状态更新：关闭**（§1 残余声明——作者字节永不豁免；信息上不可区分面为边界内极限，非推迟、非 risk acceptance）。
- **新增 CH-6（symlink 向量）**：已由 §3 resolved containment 修复（R0 review D-5 指出 R0 蓝军清单缺此向量）。
- **新增 CH-7（python 可用性）**：record 路径 fail-closed 于缺 python（§1 C-1）；C1/C2 纯 prose 行不依赖 python——基本合规提交在无 python 环境不被新增阻断。
- **W-1~W-3 维持**（R0 review 非阻塞项：框架闭表固有界限、语料 ≤32 权衡、归一映射两形钉死）。
- **纪律更正**：撤除 R0 §13.5 的无记录步数自claim——本 R1 轮事实计数：read×1（R0 review）、只读验证命令 4 次（V1~V4，含 1 次我方 SyntaxError 失败如实保留）、doc 写×1、回执×1；全部在 18 建议预算内，无为填 unknown 的补跑（V2/V3/V4 是同一验证目标的缺陷修正链，非新探索）。

## 10. ADR delta（proposed——Coordinator 写回）

- **决策更新**：豁免凭据由「闭语法 span+anchor 同对象共现」（R0）改为「严格 JSON 解析路由 + 记录身份（id 逐字 + 双 utc 瞬时）+ 同名字段整值包含（闭合显示归一）+ span↔承载字段闭映射」五条件合取；背书框架作用域全 input；语料 realpath 包含；live 四任务；C7 为哈希可验证正例。签名键表删除。
- **可逆性**：不变（git revert 单 commit；无数据迁移）。
- **影响范围**：不变（原两文件；Step-12 门；其它门零弱化）。

## 11. 静止声明

本文件为 R1 修订完整版，可独立审查（canonical 规则全量在 §1~§6，实测依据在 §2.6/§5/§6/§8）。返回 Coordinator 后静止，待同一 Design Reviewer R1 复审（逐条比对 D-1~D-5 已修复/未修复/新引入）；如需再修订另出 R2 版本，本文件 hashbound 后不改。
