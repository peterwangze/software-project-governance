#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deep dive: time-to-first-user-interaction for governance turns.

For every turn that starts with a /governance user message (or governance
skill injection), measure:
  - t0 = user/message time
  - t_first_ask = time of first ask_user_question tool/call
  - work_before_ask = tool calls + LLM output before first ask
  - the ordered bootstrap sequence (tool name + duration + result size)
Also aggregate across all sessions: how much turn time is user-wait vs
agent work; LLM output token share.
"""
import zstandard, json, glob, os, sys, io, datetime
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
SESSIONS_ROOT = os.path.join(os.environ['USERPROFILE'], '.dsh', 'sessions')

def load_events(path):
    d = zstandard.ZstdDecompressor()
    text = d.stream_reader(open(path, 'rb')).read().decode('utf-8', errors='replace')
    evs = []
    for l in text.splitlines():
        l = l.strip()
        if l:
            try:
                evs.append(json.loads(l))
            except Exception:
                pass
    return evs

def fmt(ms):
    if ms is None: return '-'
    s = ms / 1000.0
    return f"{int(s//60)}m{s%60:04.1f}s" if s >= 60 else f"{s:.1f}s"

def main():
    files = glob.glob(os.path.join(SESSIONS_ROOT, '**', 'session.v3.jsonl.zstd'), recursive=True)
    print(f"# {len(files)} session files")
    rows = []
    for f in files:
        try:
            evs = load_events(f)
        except Exception:
            continue
        # walk events, associate to turns by sequence
        turns = []
        cur = None
        pending_calls = {}
        title = ''
        for ev in evs:
            t = ev.get('type'); data = ev.get('data', {})
            if t == 'session/title':
                title = data.get('title', '')
            elif t == 'turn/start':
                cur = {'start': ev['time'], 'end': None, 'user_texts': [],
                       'seq': [], 'first_ask': None, 'out_tok': 0, 'in_tok': 0,
                       'cache_tok': 0, 'assistant_texts': 0}
                turns.append(cur)
            if cur is None:
                continue
            turn_field = data.get('turn')
            if t == 'turn/end':
                cur['end'] = ev['time']
            elif t == 'user/message':
                txt = '\n'.join(c.get('text', '') for c in data.get('content', []) if c.get('type') == 'text')
                cur['user_texts'].append((ev['time'], txt))
            elif t == 'assistant/message':
                u = data.get('usage') or {}
                cur['out_tok'] += u.get('outputTokens', 0) or 0
                cur['in_tok'] += u.get('inputTokens', 0) or 0
                cur['cache_tok'] += u.get('cacheReadTokens', 0) or 0
                for c in (data.get('message', {}).get('content') or []):
                    if c.get('type') == 'text':
                        cur['assistant_texts'] += len(c.get('text', ''))
            elif t == 'tool/call':
                pending_calls[data.get('callId')] = {'name': data.get('name'), 't': ev['time'], 'turn': cur,
                                                      'args': (data.get('arguments') or '')[:160]}
            elif t == 'tool/result':
                cid = (data.get('message', {}) or {}).get('source', {}).get('callId')
                if cid in pending_calls:
                    rec = pending_calls.pop(cid)
                    rec['dur'] = ev['time'] - rec['t']
                    rec['size'] = len(json.dumps(data.get('message', {}).get('content') or [], ensure_ascii=False))
                    rec['turn']['seq'].append(rec)
                    if rec['name'] == 'ask_user_question' and rec['turn']['first_ask'] is None:
                        rec['turn']['first_ask'] = rec['t']
        # select governance turns: first user text contains /governance command
        for tr in turns:
            if not tr['user_texts']:
                continue
            t0, txt = tr['user_texts'][0]
            head = txt[:800]
            is_gov = head.strip().startswith('/governance') or 'name="governance"' in head
            if not is_gov:
                continue
            ws = f.replace('\\', '/').split('/')[-3]
            rows.append((ws, title, f, tr))

    print(f"\n# governance turns found: {len(rows)}")
    print(f"\n{'workspace':<28} {'user→ask':>9} {'turn总时长':>10} {'pre-ask工具':>10} {'pre-ask out_tok':>14}  title")
    for ws, title, f, tr in rows:
        t0 = tr['user_texts'][0][0]
        fa = tr['first_ask']
        t2ask = (fa - t0) if fa else None
        total = (tr['end'] - t0) if tr['end'] else None
        pre_tools = [r for r in tr['seq'] if fa and r['t'] < fa]
        # tokens before first ask: proportional estimate via assistant msgs before ask
        pre_out = 0
        for r in tr['seq']:
            pass
        print(f"{ws:<28} {fmt(t2ask):>9} {fmt(total):>10} {len(pre_tools):>10} {'':>14}  {title[:30]!r}")

    # detail for the worst 3 by t2ask
    rows.sort(key=lambda x: -(x[3]['first_ask'] or x[3]['user_texts'][0][0]) + x[3]['user_texts'][0][0])
    rows.sort(key=lambda x: -((x[3]['first_ask'] or x[3]['user_texts'][0][0]) - x[3]['user_texts'][0][0]))
    for ws, title, f, tr in rows[:3]:
        t0 = tr['user_texts'][0][0]
        fa = tr['first_ask']
        print('\n' + '=' * 90)
        print(f"DETAIL [{ws}] {title!r}")
        print(f"user t0={datetime.datetime.fromtimestamp(t0/1000)}  first_ask={fmt(fa - t0) if fa else 'NEVER'}  "
              f"turn_total={fmt(tr['end']-t0) if tr['end'] else '-'}  steps≈{len(tr['seq'])}")
        print(f"turn totals: in={tr['in_tok']} cache={tr['cache_tok']} out={tr['out_tok']} assistant_chars={tr['assistant_texts']}")
        print("  pre-first-ask tool sequence (name / dur / result-size):")
        for r in tr['seq']:
            if fa and r['t'] < fa:
                arg = r['args'].replace('\n', ' ')[:100]
                print(f"    {fmt(r['dur']):>8} {r['size']:>8}B  {r['name']:<16} {arg}")

if __name__ == '__main__':
    main()
