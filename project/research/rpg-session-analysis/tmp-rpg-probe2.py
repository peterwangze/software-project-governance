# -*- coding: utf-8 -*-
"""Probe: find where usage/cost data lives in session events."""
import zstandard, json, os

base = r'C:\Users\peter\.dsh\sessions'
proj = [d for d in os.listdir(base) if '50CF' in d][0]
main = os.path.join(base, proj, 'session-f3f46901-b553-4901-8a21-8f8c5f0c18cd', 'session.v3.jsonl.zstd')
txt = zstandard.ZstdDecompressor().stream_reader(open(main, 'rb')).readall()
events = [json.loads(ln) for ln in txt.splitlines() if ln.strip()]

# 1) keys of assistant/message data
for o in events:
    if o.get('type') == 'assistant/message':
        d = o.get('data') or {}
        print('assistant/message data keys:', sorted(d.keys()))
        msg = d.get('message') or {}
        print('message keys:', sorted(msg.keys()) if isinstance(msg, dict) else type(msg))
        for k in msg:
            if 'usage' in k.lower() or 'token' in k.lower():
                print('  FOUND msg key:', k, '=', json.dumps(msg[k])[:300])
        break

# 2) request/header sample
for o in events:
    if o.get('type') == 'request/header':
        print('request/header:', json.dumps(o, ensure_ascii=False)[:600])
        break

# 3) any event containing token-like keys
import collections
keyhits = collections.Counter()
for o in events:
    for k in (o.get('data') or {}):
        if 'usage' in k.lower() or 'token' in k.lower() or 'cost' in k.lower():
            keyhits[(o.get('type'), k)] += 1
print('token-ish keys by event type:', dict(keyhits))

# 4) step/end sample
for o in events:
    if o.get('type') == 'step/end':
        print('step/end:', json.dumps(o, ensure_ascii=False)[:500])
        break
