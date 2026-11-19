"""Compare Chinese decision discovery locally with BM25, BGE and rank fusion.

Optional research dependencies: Python 3.11+, SQLite FTS5 with trigram,
torch and transformers. Acquire the six pinned public model files separately:

    hf download BAAI/bge-small-zh-v1.5 --revision 7999e1d3359715c523056ef9478215996d62a620 --include '*.json' vocab.txt model.safetensors --local-dir MODEL_DIR

Run with --governance-dir SNAPSHOT --model-dir MODEL_DIR. Add --chunks to
compare 256-token passages with 32-token overlap. All ranking runs locally.
Output includes ranks, timings and source locations. Decision bodies and
vectors stay in memory.
"""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
from time import perf_counter


REVISION = "7999e1d3359715c523056ef9478215996d62a620"
MODEL_HASHES = {
    "model.safetensors": "354763b9b1357bc9c44f62c6be2276321081ed2567773608c0d0785b61d5a026",
    "config.json": "3853a7979202c348751b753e36f579c41d8da7d36af617d3d907e1fc9b441f2a",
    "tokenizer.json": "48cea5d44424912a6fd1ea647bf4fe50b55ab8b1e5879c3275f80e339e8fae26",
    "tokenizer_config.json": "e6f3b96db926a37d4039995fbf5ad17de158dfb8f6343d607e4dbaad18d75f5a",
    "vocab.txt": "45bbac6b341c319adc98a532532882e91a9cefc0329aa57bac9ae761c27b291c",
    "special_tokens_map.json": "b6d346be366a7d1d48332dbc9fdf3bf8960b5d879522b7799ddba59e76237ee3",
}
INSTRUCTION = "为这个句子生成表示以用于检索相关文章："

# One named primary decision per positive, chosen from the source decisions
# before running the rankers. Other relevant results have not been judged.
CASES = (
    ("quality-principles", "当初是怎样规定软件修改要防止损坏使用者数据的？", "DEC-150"),
    ("frozen-work", "在哪里决定把尚无真实需求的下一版内部改进先停下来？", "DEC-377"),
    ("post-commit", "提交已经结束以后，面板能否用更省时的检查展示结果？", "DEC-394"),
    ("source-of-truth", "为何移去工作流目录里的重复规则，只留下代理实际能读到的那套？", "DEC-047"),
    ("release-lineage", "当时凭什么认定发布标签与历史版本对不上的隐患可以销项？", "DEC-137"),
    ("budget-advisory", "首次推出会话内容长度上限时，超过上限会不会挡住交付？", "DEC-210"),
    ("absent-product", "报销流程里差旅补助的每日报销上限是多少元？", None),
    ("absent-identifier", "DEC-999999", None),
)


def decisions(root):
    from search import read_records, sources

    root = root.resolve()
    files = {path: kind for path, kind in sources(root).items() if kind == "decision"}
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.encode() + b"\0" + hashlib.sha256((root / path).read_bytes()).digest())
    entries = [r for r in read_records(root, files) if r.entity]
    # Freeze the primary decisions used by the original known-item study.
    excluded = Counter(r.id_role for r in entries if r.id_role != "identifier")
    return [r for r in entries if r.id_role == "identifier"], digest.hexdigest(), excluded


@dataclass(frozen=True)
class Passage:
    record: int
    start: int
    end: int


def passages(tokenizer, records, chunks):
    pieces, texts, truncated = [], [], 0
    for number, record in enumerate(records):
        options = dict(add_special_tokens=False, truncation=True, return_offsets_mapping=True,
                       max_length=256 if chunks else 510, stride=32 if chunks else 0,
                       return_overflowing_tokens=chunks)
        offsets = tokenizer(record.body, **options)["offset_mapping"]
        for span in (offsets if chunks else [offsets]):
            start = span[0][0] if chunks else 0
            end = span[-1][1]
            pieces.append(Passage(number, start, end))
            texts.append(record.body[start:end])
        truncated += int(bool(record.body[end:].strip()))
    return pieces, texts, truncated


def best_per_record(ranking, pieces):
    best = {}
    for index in ranking:
        best.setdefault(pieces[index].record, index)
    return best


def source_region(record, piece):
    def point(offset):
        line = record.start + record.body.count("\n", 0, offset)
        column = offset - record.body.rfind("\n", 0, offset)
        return [line, column]
    return [point(piece.start), point(piece.end - 1)]


def bm25(connection, query):
    # OR the individual trigrams; a single quoted entire question would be a
    # phrase lookup. Bind the expression, using only letter/number spans.
    grams = sorted({word[i:i + 3] for word in re.findall(r"[^\W_]+", query, re.UNICODE)
                    for i in range(len(word) - 2)})
    if not grams:
        return []
    expression = " OR ".join(f'"{g}"' for g in grams)
    return [row[0] for row in connection.execute(
        "SELECT rowid FROM lexical WHERE lexical MATCH ? ORDER BY rank, rowid",
        (expression,))]


def rrf(*rankings):
    scores = defaultdict(float)
    for ranking in rankings:
        for place, index in enumerate(ranking[:60], 1):
            scores[index] += 1 / (60 + place)
    return sorted(scores, key=lambda i: (-scores[i], i))


def run(root, model_dir, chunks=False):
    import torch
    import transformers
    from transformers import AutoModel, AutoTokenizer

    records, digest, excluded = decisions(root)
    ids = {r.entity for r in records}
    missing = {target for _, _, target in CASES if target} - ids
    if missing:
        raise ValueError("snapshot missing labeled targets: " + ", ".join(sorted(missing)))
    for name, expected in MODEL_HASHES.items():
        with (model_dir / name).open("rb") as handle:
            if hashlib.file_digest(handle, "sha256").hexdigest() != expected:
                raise ValueError(f"expected {name} from revision {REVISION}")
    torch.set_num_threads(min(torch.get_num_threads(), 4))
    stamp = perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    model = AutoModel.from_pretrained(model_dir, local_files_only=True, use_safetensors=True).eval()
    model_load = perf_counter() - stamp

    @torch.inference_mode()
    def embed(texts):
        inputs = tokenizer(texts, padding=True, truncation=True, max_length=512, return_tensors="pt")
        cls = model(**inputs).last_hidden_state[:, 0]
        return torch.nn.functional.normalize(cls, dim=1)

    stamp = perf_counter()
    pieces, texts, truncated = passages(tokenizer, records, chunks)
    tokenize_s = perf_counter() - stamp
    stamp = perf_counter()
    vectors = torch.cat([embed(texts[i:i + 8]) for i in range(0, len(texts), 8)])
    dense_build = perf_counter() - stamp
    cases = []
    hits = {method: [] for method in ("bm25", "bge", "rrf")}
    with closing(sqlite3.connect(":memory:")) as conn:
        stamp = perf_counter()
        conn.execute("CREATE VIRTUAL TABLE lexical USING fts5(body, tokenize='trigram')")
        conn.executemany("INSERT INTO lexical(rowid,body) VALUES (?,?)", enumerate(texts))
        conn.commit()
        lexical_build = perf_counter() - stamp
        for name, query, target in CASES:
            stamp = perf_counter()
            lexical = best_per_record(bm25(conn, query), pieces)
            lex_ms = (perf_counter() - stamp) * 1000
            stamp = perf_counter()
            scores = torch.mv(vectors, embed([INSTRUCTION + query])[0])
            dense = best_per_record(scores.argsort(descending=True, stable=True).tolist(), pieces)
            semantic_ms = (perf_counter() - stamp) * 1000
            case = {"name": name, "target": target, "lexical_ms": round(lex_ms, 2),
                    "dense_ms": round(semantic_ms, 2), "top_dense_cosine": round(scores.max().item(), 4)}
            best = {"bm25": lexical, "bge": dense}
            for method, ranked in [("bm25", list(lexical)), ("bge", list(dense)),
                                   ("rrf", rrf(list(lexical), list(dense)))]:
                place = next((i for i, n in enumerate(ranked, 1) if records[n].entity == target), None)
                if target:
                    hits[method].append(place)
                case[method] = {"rank": place, "top": [
                    [records[n].entity, records[n].path, records[n].start] for n in ranked[:3]]}
                if chunks:
                    case[method]["source_spans"] = [
                        {"sha256": records[n].digest, "end_line": records[n].end,
                         "matched_region": {m: source_region(records[n], pieces[indexes[n]])
                                            for m, indexes in best.items() if n in indexes}}
                        for n in ranked[:3]]
            cases.append(case)
    return {"corpus_sha256": digest, "occurrences": len(records), "distinct_ids": len(ids),
            "excluded_nonprimary_candidates": dict(excluded),
            "passages": len(pieces), "max_tokens": 256 if chunks else 510,
            "overlap_tokens": 32 if chunks else 0, "tokenization_s": round(tokenize_s, 3),
            "model_revision": REVISION, "python": sys.version.split()[0], "torch": torch.__version__,
            "transformers": transformers.__version__, "sqlite": sqlite3.sqlite_version,
            "model_load_s": round(model_load, 3), "embedding_s": round(dense_build, 3),
            "fts_build_s": round(lexical_build, 3), "model_bytes": (model_dir / "model.safetensors").stat().st_size,
            "in_memory_vector_bytes": vectors.numel() * vectors.element_size(), "truncated": truncated,
            "threads": torch.get_num_threads(), "device": str(vectors.device),
            "hit_counts": {m: {f"top{k}": sum(n is not None and n <= k for n in ranks) for k in (1, 3, 5)}
                           for m, ranks in hits.items()}, "cases": cases}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--governance-dir", required=True, type=Path)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--chunks", action="store_true", help="index all overlapping passages and rank records by their best passage")
    args = parser.parse_args()
    print(json.dumps(run(args.governance_dir, args.model_dir, args.chunks), ensure_ascii=False, indent=2))
