#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspect DSH session trace event structures (UTF-8 safe output)."""
import zstandard, json, glob, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

f = glob.glob(r'C:\Users\peter\.dsh\sessions\--D-AI-agent-deepseek-plugins-router--\*\session.v3.jsonl.zstd')[0]
d = zstandard.ZstdDecompressor()
text = d.stream_reader(open(f, 'rb')).read().decode('utf-8', errors='replace')
lines = [x for x in text.splitlines() if x.strip()]
shown = set()
for l in lines:
    j = json.loads(l)
    t = j.get('type')
    if t in ('step/end', 'tool/call', 'tool/result', 'request/context', 'request/header',
             'turn/start', 'turn/end', 'user/message', 'assistant/message') and t not in shown:
        shown.add(t)
        s = json.dumps(j, ensure_ascii=False)
        print('===', t, '===')
        print(s[:1800])
        print()
