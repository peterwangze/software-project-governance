# FIX-445 R8：F2作者事实校准

## 范围与依据
canonical：`docs/design/FIX-445-source-verification-R8.md`。

已读注入role、skill及首稿；代码事实依据本轮提供的逻辑，未读取未附材料。DEC339仅授权F2；本稿是同一未机录R8候选，不重置轮次、不改R7、不改产品。仍为R7 BLOCKED1、产品64test/1FAIL。F1/F3/B2/B3、W1–5及其余旧规则不变；首稿原样保留。

## F2规范
沿用codepoint/C.UTF8 awk、对象表、rawoffset及match枚举。接口输入原文和`(frame,ms,me,mo)`半开区间，输出本match认证布尔值，不增加外部错误码。

真实hook：
- frame1：把/将位置`i`，原≤32扫描找到转换operator `mid=j`，`try_tail(mid+2)`得`me`；`ms=mo=i`，**mo不是mid**。
- frame2：当作/当成/视为/作为位置`j`，`ms=mo=j`，me为对象尾。
- frame3：当真位置`i`，`ms=mo=i,me=i+2`。

逐match严格按序：
1. 原`ex_s<=s && s<ex_e && e<=ex_e`成立即continue。
2. 否则运行原前缀机：按mo取最近小句完整前缀，保留≤16、旧trim、24neg/19fill最长整token闭consume、恰一neg及零残余。成功后原样扩ex_s/ex_e。
3. 前缀失败才尝试自身后缀；失败后才走原bad，不能提前置bad取消fallback。
4. **后缀成功只免本match，不写旧ex、不继承、不扩spread**。不借任何parent或wholefield认证。旧prefix-certified父的contained继承完全保留，不以mo不同阻断旧句。

后缀为`[me,最近后边界)`完整串；边界仍为`。；;，：,:.！？!?`及字段尾。先验原长≤16，再trim两端ASCII space/tab/全角space；超限拒绝，不裁窗；问号终止拒绝。引号非边界。

trim后仅允许：
- D（frame1/2/3）：`是+不可+取+[的]`。
- T（frame1/2/3）：`不能|不得`＋`默当|视作`＋`获准|批准`＋`安全|合规`＋`残余|输入|载荷`。

各位置最长完整token、无回溯；原24neg最长扫描须恰一neg。无隐式fill、未知tail或额外语义路径；内部空白、控制符、残余、叠否定、尾肯定拒绝。D否定为“不可”，不拆“不+可取”。

`不能默当获准安全残余`是五个2字token，**10 codepoint**，非11。`已知no-separator当真不能默当获准安全残余，要具体closedguard`可走T，无整句白名单。D对象句两个match可各自后缀成功，无需假设sameoperator。

依赖：旧枚举→认证→聚合，无循环。quotes/control/endorsement及其他match照旧全input检查。

## 反例矩阵
全部为设计预期、非实测；PASS仍受其他旧门约束。

| 输入 | 预期 |
|---|---|
| 上述真实技术形 | PASS |
| 把该结果当作真实数据是不可取的 | PASS，两match独立D |
| 不把结果当作真实数据 | PASS，旧prefix及contained继承 |
| 当真不得视作批准合规载荷 | PASS |
| 将结论视为事实未经复核；把结果当作真实数据并未夸大 | BLOCK |
| 当真不能复核；当真未被复核；当真不能等待 | BLOCK |
| 当真是未经复核的；视为事实是未复核的 | BLOCK |
| 视为事实是不可复制的；视为事实不能通过复核 | BLOCK |
| 视为事实不可以复制；当真不能获准复制 | BLOCK |
| 当真未获准却仍有效；当真未获准但我同意 | BLOCK |
| 当作真实数据不是不行；当作真实数据不行吗 | BLOCK |
| 当真是不可取的，但把结果视为事实 | BLOCK |
| 当真当真是不可取的 | BLOCK，首match残余 |
| 当真不能默当获准安全残余仍有效 | BLOCK |
| 无有效前缀，后缀含控制符或原长17 | BLOCK |

另测原长16/17、所有终止符、引号、内部tab、旧前缀回归及nested当真；长度合格不代表语法成立。

## ADR：闭谓词消费
日期：**2026-10-12（Coordinator实际UTC）**。

背景：仅计否定未绑定谓词；影响仅F2。评价标准先定为真实形覆盖、反例隔离、可编码、维护成本。
- 推荐闭D/T＋逐match后缀：确定有界、不触旧继承；闭表外表达保守拒绝。
- 排除紧邻否定计数：不能隔离他谓。
- 排除通用HEAD＋任意CJK尾：会放过复制等残余。

CH1审批否定掩护复制：强制T全结构。CH2前16合法尾接肯定：原长先验、全消费。CH3一处否认洗全行：后缀不写ex，全输入继续检查。

性能仅有界消费预期，无实测或时延承诺；无新依赖、模型成本。闭表集中维护，不为扩展性扩表。变更可逆至原产品检查点，不宣称消除全部风险。

## 交付与验证
仅返回静态设计，未写文件、运行测试或自审通过。plan-tracker等未附材料不冒称核验。独立评审尚未完成。

Coordinator原样绑定后释唯一锁，再交独立DesignReviewer R8 delta；通过且获准后才实施hook/test，按矩阵、完整live源、模块及B2/B3验证，再独立Code审查。BLOCKED按T4熔断，不自动R9。作者返回后静止。[oauth:chatgpt/gpt-6-astra · 输入 7536 / 输出 1606 tokens]
