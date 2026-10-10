# -*- coding: utf-8 -*-
"""Probe structure of DSH session.v3.jsonl.zstd (RPG main session)."""
import zstandard, json, os, collections, sys

base = r'C:\Users\peter\.dsh\sessions'
proj = [d for d in os.listdir(base) if '50CF' in d][0]
main = os.path.join(base, proj, 'session-f3f46901-b553-4901-8a21-8f8c5f0c18cd', 'session.v3.jsonl.zstd')
raw = open(main, 'rb').read()
dctx = zstandard.ZstdDecompressor()
reader = dctx.stream_reader(open(main, 'rb'))
txt = reader.readall()
lines = txt.splitlines()
print('total lines:', len(lines))
types = collections.Counter()
for ln in lines:
    try:
        o = json.loads(ln)
    except Exception:
        types['<bad>'] += 1
        continue
    types[o.get('type', '?')] += 1
print('types:', dict(types))

shown = 0
for ln in lines:
    s = ln.decode('utf-8', 'replace') if isinstance(ln, bytes) else ln
    if '"usage"' in s:
        print('--- SAMPLE USAGE LINE (trunc 1500):')
        print(s[:1500])
        shown += 1
        if shown >= 2:
            break
