#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze DSH session traces: governance turn cost breakdown.

Scans all session.v3.jsonl.zstd under ~/.dsh/sessions, finds turns whose user
message is a /governance invocation (or governance bootstrap heavy turns), and
produces per-turn cost metrics:
  - total turn duration, step count, tool call count
  - LLM time vs tool time vs harness overhead
  - per-tool-call durations (top offenders)
  - per-step token usage (input / cacheRead / output)
  - tool result payload sizes (which reads blow up context)
Also prints a workspace-level summary of the biggest sessions.
"""
import zstandard, json, glob, os, sys, io
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SESSIONS_ROOT = os.path.join(os.environ['USERPROFILE'], '.dsh', 'sessions')

def load_session(path):
    d = zstandard.ZstdDecompressor()
    raw = d.stream_reader(open(path, 'rb')).read()
    text = raw.decode('utf-8', errors='replace')
    events = []
    for l in text.splitlines():
        l = l.strip()
        if not l:
            continue
        try:
            events.append(json.loads(l))
        except Exception:
            pass
    return events

def ts(ev):
    return ev.get('time', 0)

def fmt_dur(ms):
    if ms is None:
        return '-'
    s = ms / 1000.0
    if s < 60:
        return f"{s:.1f}s"
    return f"{int(s//60)}m{s%60:.0f}s"

def fmt_tok(n):
    if n is None:
        return '-'
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1000:
        return f"{n/1000:.1f}K"
    return str(n)

def text_of(msg_data):
    parts = []
    for c in msg_data.get('content', []):
        if c.get('type') == 'text':
            parts.append(c.get('text', ''))
    return '\n'.join(parts)

def analyze_session(path):
    events = load_session(path)
    if not events:
        return None
    sess = events[0] if events[0].get('type') == 'session' else {}
    cwd = sess.get('cwd', '')
    title = ''
    turns = defaultdict(lambda: {
        'start': None, 'end': None, 'steps': 0, 'user_text': '',
        'tool_calls': [], 'llm_times': [], 'usages': [], 'assistant_chars': 0,
        'first_assistant_time': None,
    })
    title_ev = [e for e in events if e.get('type') == 'session/title']
    if title_ev:
        title = title_ev[-1].get('data', {}).get('title', '')

    # pair tool/call -> tool/result; track current turn by sequence position
    pending = {}
    current_turn = None
    for ev in events:
        t = ev.get('type')
        data = ev.get('data', {})
        turn = data.get('turn')
        if turn is None:
            turn = current_turn
        else:
            current_turn = turn
        if t == 'turn/start':
            turns[turn]['start'] = ts(ev)
        elif t == 'turn/end':
            turns[turn]['end'] = ts(ev)
        elif t == 'user/message':
            turns[turn]['user_text'] = text_of(data)
            turns[turn]['user_time'] = ts(ev)
        elif t == 'step/start':
            turns[turn]['steps'] += 1
        elif t == 'assistant/message':
            tr = turns[turn]
            if tr['first_assistant_time'] is None:
                tr['first_assistant_time'] = ts(ev)
            usage = data.get('usage') or {}
            tr['usages'].append(usage)
            for c in (data.get('message', {}).get('content') or []):
                if c.get('type') == 'text':
                    tr['assistant_chars'] += len(c.get('text', ''))
        elif t == 'tool/call':
            pending[data.get('callId')] = {
                'turn': turn, 'name': data.get('name'), 't_call': ts(ev),
                'args': data.get('arguments', '')[:300],
            }
        elif t == 'tool/result':
            cid = None
            msg = data.get('message', {})
            src = msg.get('source', {})
            cid = src.get('callId')
            if cid and cid in pending:
                rec = pending.pop(cid)
                content = msg.get('content') or []
                size = len(json.dumps(content, ensure_ascii=False))
                rec['t_result'] = ts(ev)
                rec['dur_ms'] = ts(ev) - rec['t_call']
                rec['result_size'] = size
                turns[rec['turn']]['tool_calls'].append(rec)
    return {
        'path': path, 'cwd': cwd, 'title': title, 'turns': dict(turns),
    }

def turn_metrics(tr):
    total = None
    if tr['end'] and tr['start']:
        total = tr['end'] - tr['start']
    tool_ms = sum(r['dur_ms'] for r in tr['tool_calls'])
    llm_ms = 0
    # llm time approximated by sum of usage step gaps is unreliable; use
    # assistant/message stream timing if present — fallback: total - tool
    in_tok = sum(u.get('inputTokens', 0) or 0 for u in tr['usages'])
    cache_tok = sum(u.get('cacheReadTokens', 0) or 0 for u in tr['usages'])
    out_tok = sum(u.get('outputTokens', 0) or 0 for u in tr['usages'])
    return {
        'total_ms': total, 'steps': tr['steps'],
        'tools': len(tr['tool_calls']), 'tool_ms': tool_ms,
        'in_tok': in_tok, 'cache_tok': cache_tok, 'out_tok': out_tok,
        'assistant_chars': tr['assistant_chars'],
    }

def is_governance_turn(tr):
    txt = (tr.get('user_text') or '').strip()
    head = txt[:600]
    return (txt.startswith('/governance') or txt == '/governance'
            or 'name="governance"' in head or '<skill_content name="governance"' in head
            or head.startswith('/governance'))

def main():
    files = glob.glob(os.path.join(SESSIONS_ROOT, '**', 'session.v3.jsonl.zstd'), recursive=True)
    print(f"# scanning {len(files)} session files")
    gov_turns = []
    session_summaries = []
    for f in files:
        try:
            s = analyze_session(f)
        except Exception as e:
            continue
        if not s or not s['turns']:
            continue
        ws = s['cwd'].replace('\\', '/').split('/')[-1]
        tot_ms = 0
        tot_steps = 0
        tot_tools = 0
        tot_out = 0
        tot_in = 0
        for n, tr in s['turns'].items():
            m = turn_metrics(tr)
            tot_ms += m['total_ms'] or 0
            tot_steps += m['steps']
            tot_tools += m['tools']
            tot_out += m['out_tok']
            tot_in += m['in_tok']
            if is_governance_turn(tr) and m['total_ms']:
                gov_turns.append((ws, s['title'], n, m, tr, f))
        if tot_ms > 60_000 or tot_steps > 10:
            session_summaries.append((tot_ms, tot_steps, tot_tools, tot_in, tot_out, ws, s['title'], f))

    print("\n# == All /governance turns (duration desc) ==")
    gov_turns.sort(key=lambda x: -(x[3]['total_ms'] or 0))
    for ws, title, n, m, tr, f in gov_turns[:25]:
        print(f"\n--- [{ws}] title={title!r} turn={n}")
        print(f"    total={fmt_dur(m['total_ms'])}  steps={m['steps']}  tool_calls={m['tools']}")
        print(f"    tool_time={fmt_dur(m['tool_ms'])}  ({100*m['tool_ms']/max(1,m['total_ms']):.0f}% of turn)")
        print(f"    llm_time≈{fmt_dur((m['total_ms'] or 0) - m['tool_ms'])}")
        print(f"    tokens: in={fmt_tok(m['in_tok'])} cache={fmt_tok(m['cache_tok'])} out={fmt_tok(m['out_tok'])}")
        print(f"    assistant_chars={m['assistant_chars']}")
        # top tool offenders
        tcs = sorted(tr['tool_calls'], key=lambda r: -r['dur_ms'])
        if tcs:
            print("    top tools by duration:")
            for r in tcs[:8]:
                arg = r['args'].replace('\n', ' ')[:110]
                print(f"      {fmt_dur(r['dur_ms']):>8}  {r['result_size']:>9}B  {r['name']:<18} {arg}")
        # tool name distribution
        names = defaultdict(lambda: [0, 0])
        for r in tr['tool_calls']:
            names[r['name']][0] += 1
            names[r['name']][1] += r['dur_ms']
        dist = sorted(names.items(), key=lambda kv: -kv[1][1])
        print("    tool distribution (count / total time):")
        for name, (c, ms) in dist[:12]:
            print(f"      {name:<20} x{c:<3} {fmt_dur(ms)}")

    print("\n\n# == Biggest sessions overall (any content) ==")
    session_summaries.sort(key=lambda x: -x[0])
    print(f"{'duration':>10} {'steps':>6} {'tools':>6} {'in_tok':>9} {'out_tok':>8}  workspace / title")
    for tot_ms, steps, tools, tin, tout, ws, title, f in session_summaries[:20]:
        print(f"{fmt_dur(tot_ms):>10} {steps:>6} {tools:>6} {fmt_tok(tin):>9} {fmt_tok(tout):>8}  {ws} / {title!r}")

if __name__ == '__main__':
    main()
