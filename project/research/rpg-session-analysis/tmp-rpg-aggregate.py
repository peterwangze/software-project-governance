# -*- coding: utf-8 -*-
"""Aggregate RPG project DSH sessions: usage, tool histograms, timeline."""
import zstandard, json, os, collections, sys, datetime, glob

base = r'C:\Users\peter\.dsh\sessions'
proj = [d for d in os.listdir(base) if '50CF' in d][0]
projdir = os.path.join(base, proj)
files = sorted(glob.glob(os.path.join(projdir, '*', 'session.v3.jsonl.zstd')))

def load(fp):
    try:
        txt = zstandard.ZstdDecompressor().stream_reader(open(fp, 'rb')).readall()
        out = []
        for ln in txt.splitlines():
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
        return out
    except Exception as e:
        return []

def ts(t):
    try:
        return datetime.datetime.fromtimestamp(t / 1000).strftime('%m-%d %H:%M:%S')
    except Exception:
        return '?'

USAGE_KEYS = ['totalTokens', 'inputTokens', 'outputTokens', 'cacheReadTokens']
grand = collections.Counter()
rows = []
main_extra = {}
for fp in files:
    evs = load(fp)
    name = os.path.basename(os.path.dirname(fp))
    first_t = last_t = None
    steps = turns = 0
    tools = collections.Counter()
    usage_sum = collections.Counter()
    compactions = 0
    usage_sample = None
    user_first = None
    pwsh_cmds = []
    subagent_spawn = 0
    for o in evs:
        ty = o.get('type')
        t = o.get('time')
        if t:
            first_t = first_t or t
            last_t = t
        if ty == 'step/start':
            steps += 1
        elif ty == 'turn/start':
            turns += 1
        elif ty == 'compaction/end':
            compactions += 1
        elif ty == 'tool/call':
            d = o.get('data') or {}
            nm = d.get('name') or d.get('tool') or '?'
            tools[nm] += 1
            if nm == 'pwsh':
                try:
                    args = json.loads(d.get('arguments') or '{}')
                    pwsh_cmds.append(args.get('command', ''))
                except Exception:
                    pass
            if nm in ('task', 'subagent', 'subagent_fork'):
                subagent_spawn += 1
        elif ty == 'user/message':
            if user_first is None:
                d = o.get('data') or {}
                msg = d.get('message') or d
                c = msg.get('content') if isinstance(msg, dict) else None
                if isinstance(c, list):
                    txts = [x.get('text', '') for x in c if isinstance(x, dict) and x.get('type') == 'text']
                    user_first = (txts[0] if txts else '')[:160]
                elif isinstance(c, str):
                    user_first = c[:160]
        elif ty == 'assistant/message':
            d = o.get('data') or {}
            u = d.get('usage')
            if isinstance(u, dict):
                if usage_sample is None:
                    usage_sample = dict(u)
                for k in USAGE_KEYS:
                    if isinstance(u.get(k), (int, float)):
                        usage_sum[k] += u[k]
    for k in USAGE_KEYS:
        grand[k] += usage_sum[k]
    sleep_cnt = sum(1 for c in pwsh_cmds if 'Start-Sleep' in c)
    verify_cnt = sum(1 for c in pwsh_cmds if 'verify_workflow' in c)
    wg_cnt = sum(1 for c in pwsh_cmds if 'write-guard' in c)
    rows.append({
        'session': name[:20], 'file_MB': round(os.path.getsize(fp) / 1048576, 1),
        'created': ts(first_t), 'last': ts(last_t), 'turns': turns, 'steps': steps,
        'tools': dict(tools.most_common(6)), 'usage': {k: v for k, v in usage_sum.items() if v},
        'compactions': compactions, 'sleep': sleep_cnt, 'verify': verify_cnt, 'writeguard': wg_cnt,
        'spawn': subagent_spawn, 'first_user': (user_first or '')[:120],
    })
    if 'f3f46901' in name:
        main_extra = {'tools_all': dict(tools), 'usage_sample': usage_sample, 'pwsh_total': len(pwsh_cmds)}

print('=== USAGE SAMPLE (main) ===')
print(json.dumps(main_extra.get('usage_sample'), ensure_ascii=False))
print('=== MAIN tools_all ===')
print(json.dumps(main_extra.get('tools_all'), ensure_ascii=False))
print()
print('=== PER-SESSION ROWS (sorted by created) ===')
for r in sorted(rows, key=lambda x: x['created']):
    print(json.dumps(r, ensure_ascii=False))
print()
print('=== GRAND TOTALS usage ===')
print(json.dumps(dict(grand), ensure_ascii=False))
print('sessions:', len(rows))
