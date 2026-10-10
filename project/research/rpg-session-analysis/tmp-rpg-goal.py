# -*- coding: utf-8 -*-
"""Extract goal changes + turn timing from RPG main session."""
import zstandard, json, os, datetime, collections

base = r'C:\Users\peter\.dsh\sessions'
proj = [d for d in os.listdir(base) if '50CF' in d][0]
main = os.path.join(base, proj, 'session-f3f46901-b553-4901-8a21-8f8c5f0c18cd', 'session.v3.jsonl.zstd')
txt = zstandard.ZstdDecompressor().stream_reader(open(main, 'rb')).readall()
events = [json.loads(ln) for ln in txt.splitlines() if ln.strip()]

def ts(t):
    return datetime.datetime.fromtimestamp(t / 1000).strftime('%m-%d %H:%M:%S')

print('== goal/change events ==')
for o in events:
    if o.get('type') == 'goal/change':
        print(ts(o.get('time')), json.dumps(o.get('data'), ensure_ascii=False)[:400])

print('== session/end-seed ==')
for o in events:
    if o.get('type') == 'session/end-seed':
        print(ts(o.get('time')), json.dumps(o.get('data'), ensure_ascii=False)[:300])

print('== turn boundaries (turn/start) ==')
turns = [o for o in events if o.get('type') == 'turn/start']
print('turn count:', len(turns))

# active time via gap-cap 180s between consecutive events
times = [o['time'] for o in events if 'time' in o]
times.sort()
active = 0
gap = 0
for a, b in zip(times, times[1:]):
    d = (b - a) / 1000
    if d <= 180:
        active += d
    else:
        gap += d
print('wall span min:', round((times[-1] - times[0]) / 60000, 1), '| active(gap<=180s) min:', round(active / 60, 1), '| idle min:', round(gap / 60, 1))

# per-day-hour step histogram
hist = collections.Counter()
for o in events:
    if o.get('type') == 'step/start':
        hist[datetime.datetime.fromtimestamp(o['time'] / 1000).strftime('%d-%H')] += 1
print('== steps per hour ==')
for k in sorted(hist):
    print(k, hist[k])

# ask_user_question timing + first user messages (real user inputs)
print('== user messages (non-splice) ==')
n = 0
for o in events:
    if o.get('type') == 'user/message':
        d = o.get('data') or {}
        msg = d.get('message') or d
        c = msg.get('content') if isinstance(msg, dict) else None
        text = ''
        if isinstance(c, list):
            text = ' '.join(x.get('text', '') for x in c if isinstance(x, dict) and x.get('type') == 'text')
        elif isinstance(c, str):
            text = c
        if text.strip() and not text.startswith('##'):
            print(ts(o.get('time')), '|', text[:200].replace('\n', ' '))
            n += 1
            if n > 15:
                break
