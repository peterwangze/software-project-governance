# 治理记录的写入与查找

AUDIT-165，2026-11-19。以本项目冻结的热账和归档为样本，先复用现行查找入口，再按真实需求试点结构化读写。完整方法、失败案例、问题标注与上游来源保存在固定版本，逐题结果可在对应的冻结样本上复算。[完整研究报告](https://github.com/peterwangze/software-project-governance/blob/b900d373b9483837b1957caecb9065cf3728029c/docs/research/process-records-storage-retrieval-2026-11-19.md) · [实验代码与公开夹具](https://github.com/peterwangze/software-project-governance/tree/b900d373b9483837b1957caecb9065cf3728029c/benchmarks/process-records)

| 事务 | 取舍与依据 |
| --- | --- |
| 把发现、附件和任务状态一起交付 | 多行原文可用现行附件入口。原生两条命令之间中断时，证据已落盘，任务仍在开发。SQLite 单事务在相同故障处回滚，重试只产生一次效果。先在新项目试一笔跨记录验收，测真实填写成本。 |
| 按编号、用词或关系找原件 | 日常优先用现有归档指针和 rg。160 个源文件共 6.93 MB，现行指针答对全部 5 道编号题。原文、rg 和 SQLite 三类方法均答对原题 8/9，找到 10/11 个标注出处，另找齐三道重号与补记题的 7 处原件。SQLite 长连接约 0.07 ms，每次重验全部来源约 67 ms，rg 约 54 ms。两个汉字的查询需要字面回退。重复查找多的项目可试可删除的只读索引。 |
| 只有模糊问法，或要跨周期统计 | 六道中文改写题中，BM25、BGE 和融合排名均未将指定原件排到首位，两个无答案问题也有语义候选。排名仅供人工回查。统计可按需导出给 DuckDB。6,791 个真实文本片段从 JSONL 的 8.46 MB 压到 Parquet 的 2.03 MB，两种格式的 4,895 组计数完全相同，小夹具的 Parquet 反而更大。 |

## 试点次序和采用条件

1. **先试只读检索。** 保留 Markdown／JSON 权威态，源文件或权威切换后重验。返回原件的路径、行号、指纹和修订角色。DEC-214 的主记录与两份勘误、补记应能分别打开。用实际查找频次、遗漏和回源总耗时决定是否保留索引。
2. **再试一笔写入。** 同一请求携带操作号、预期修订、状态、证据和附件指纹。先复验中断重试、并发冲突、一致读取与导出恢复，再用 Codex 和 DSH 的同类事务比较手填字段、修正次数和成品验收。DSH 沿用已授权的单项直修入口。
3. **有迁移需求再切换权威。** 核对所有读写方，逐条裁定重号和未解析记录，核验历史与附件并演练备份恢复。试点不可用时，使用现有 CLI 和归档指针。

## 复跑

从包含固定提交的仓库根目录建立独立工作树。以下命令在新检出中使用公开夹具。检索需要支持 FTS5/trigram 的 Python SQLite，rg 在 PATH 中时加入对照。写入需要 Pydantic 2.12.5 和支持 STRICT 与 JSON 的 SQLite。统计需要 DuckDB 1.5.6，可用装有相应依赖的解释器分别运行。

```sh
git worktree add --detach ../spg-records-lab b900d373b9483837b1957caecb9065cf3728029c
cd ../spg-records-lab
python -X utf8 benchmarks/process-records/search.py bench
python -X utf8 -m unittest discover -s benchmarks/process-records -p test_search.py
python -X utf8 benchmarks/process-records/write.py
python -X utf8 benchmarks/process-records/cold_projection.py
```

复验项目九题及三道追加题，需要对应的本机冻结 `.governance` 目录。在同一检出中运行 `python -X utf8 benchmarks/process-records/search.py --source "<冻结的治理目录>" bench --cases project --repeats 5`。语义对照另需固定的六个模型文件、torch 与 transformers。语料指纹、版本及参数见[完整复跑条件](https://github.com/peterwangze/software-project-governance/blob/b900d373b9483837b1957caecb9065cf3728029c/docs/research/process-records-storage-retrieval-2026-11-19.md#复跑)。
