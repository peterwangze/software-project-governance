#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug: dump user/message texts of sessions titled /governance."""
import zstandard, json, glob, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def load(path):
    d = zstandard.ZstdDecompressor()
    return d.stream_reader(open(path, 'rb')).read().decode('utf-8', errors='replace')

files = glob.glob(r'C:\Users\peter\.dsh\sessions\**\session.v3.jsonl.zstd', recursive=True)
for f in files:
    try:
        text = load(f)
    except Exception:
        continue
    lines = [x for x in text.splitlines() if x.strip()]
    title = ''
    for l in lines:
        j = json.loads(l)
        if j.get('type') == 'session/title':
            title = j.get('data', {}).get('title', '')
    if 'governance' not in title.lower():
        continue
    ws = os.path.basename(os.path.dirname(os.path.dirname(f)))
    print('=' * 70)
    print('FILE:', ws, '|', os.path.basename(os.path.dirname(f)), '| title:', title)
    for l in lines:
        j = json.loads(l)
        if j.get('type') == 'user/message':
            data = j.get('data', {})
            turn = data.get('turn')
            content = data.get('content', [])
            kinds = [c.get('type') for c in content]
            texts = []
            for c in content:
                if c.get('type') == 'text':
                    texts.append(c.get('text', ''))
            joined = '\n'.join(texts)
            import datetime
            t = datetime.datetime.fromtimestamp(j['time'] / 1000).strftime('%m-%d %H:%M')
            print(f"  [{t}] turn={turn} kinds={kinds} len={len(joined)}")
            print('    HEAD:', joined[:160].replace('\n', ' ⏎ '))
