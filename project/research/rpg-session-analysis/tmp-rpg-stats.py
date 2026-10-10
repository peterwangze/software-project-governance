# -*- coding: utf-8 -*-
"""Cost stats from aggregate output."""
import json

txt = open(r'D:\AI\agent\claude\coding\project_management_workflow\.governance\tmp-rpg-agg-out.txt', encoding='utf-8').read()
rows = [json.loads(l) for l in txt.splitlines() if l.startswith('{"session"')]
main = [r for r in rows if 'f3f46901' in r['session']][0]
subs = [r for r in rows if 'f3f46901' not in r['session'] and r['steps'] > 0]

def M(x):
    return round(x / 1e6, 1)

print('subs:', len(subs), '| sub steps:', sum(r['steps'] for r in subs),
      '| sub display:', M(sum(r['usage'].get('totalTokens', 0) for r in subs)), 'M',
      '| uncached-in:', M(sum(r['usage'].get('inputTokens', 0) for r in subs)), 'M',
      '| out:', M(sum(r['usage'].get('outputTokens', 0) for r in subs)), 'M')

big = sorted(subs, key=lambda r: -r['usage'].get('totalTokens', 0))[:12]
print('\n== top-12 subagent sessions ==')
for r in big:
    tid = r['first_user'].split('—')[0].replace('## 任务：', '').strip()[:36]
    print(f"{M(r['usage'].get('totalTokens',0)):>7}M {r['steps']:>4}st  {r['created']}~{r['last'][6:]}  {tid}")

# role groups by task prefix
import collections, re
groups = collections.defaultdict(lambda: [0, 0, 0])
for r in subs:
    m = re.match(r'## 任务：([A-Z]+)-', r['first_user'])
    pref = m.group(1) if m else 'OTHER'
    groups[pref][0] += r['usage'].get('totalTokens', 0)
    groups[pref][1] += r['steps']
    groups[pref][2] += 1
print('\n== by task family ==')
for k, v in sorted(groups.items(), key=lambda kv: -kv[1][0]):
    print(f"{k:<8} {M(v[0]):>8}M {v[1]:>5}st {v[2]:>3} sessions")

# session lifetime sum
import datetime
def dur_min(r):
    def p(s):
        return datetime.datetime.strptime('2026-' + s, '%Y-%m-%d %H:%M:%S')
    return (p(r['last']) - p(r['created'])).total_seconds() / 60
tot_life = sum(dur_min(r) for r in subs)
print('\nsub session-lifetime sum (min, incl. waits):', round(tot_life))
for day in ['10-08', '10-09', '10-10']:
    g = [r for r in subs if r['created'].startswith(day)]
    print(day, '| sessions:', len(g), '| steps:', sum(r['steps'] for r in g),
          '| display:', M(sum(r['usage'].get('totalTokens', 0) for r in g)), 'M',
          '| lifetime h:', round(sum(dur_min(r) for r in g) / 60, 1))
