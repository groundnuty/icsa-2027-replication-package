"""Power for a 10-point paired difference from the data's own per-region spread.
Usage: python power.py <final-dir> [coded-rows.jsonl]  (needs numpy and scipy)
"""
import json,sys,collections,statistics as st,random
import numpy as np
from scipy.stats import wilcoxon
D=sys.argv[1]
rows=[json.loads(l) for l in open(sys.argv[2] if len(sys.argv)>2 else D+'/h3/scored_rows_coded.jsonl')]
m=[r for r in rows if r.get('block')=='main']
lab=lambda r:r.get('label_after_inspection') or r.get('label')
def val(r,outcome):
    if outcome=='omission':
        if not r.get('finished'): return None
        L=lab(r); return 1.0 if L=='omitting' else 0.0 if L=='complete' else None
    v=r.get(outcome); return None if v is None else float(v)
def region_diffs(outcome,layout,a,b):
    cell=collections.defaultdict(list)
    for r in m:
        u=r['run']
        if u['layout']!=layout or u['option'] not in(a,b): continue
        v=val(r,outcome)
        if v is None: continue
        cell[(r['region_id'],u['model'],u['option'])].append(v)
    regs=collections.defaultdict(list)
    for (g,mo,o) in list(cell):
        if o!=a: continue
        if (g,mo,b) in cell: regs[g].append(st.mean(cell[(g,mo,a)])-st.mean(cell[(g,mo,b)]))
    return np.array([st.mean(v) for g,v in sorted(regs.items())])
rng=np.random.default_rng(20271106)
def power(d,shift=0.10,B=4000,alpha=0.05/3):
    c=d-d.mean(); hits=0; hits05=0
    for _ in range(B):
        s=rng.choice(c,size=len(c),replace=True)+shift
        p=wilcoxon(s).pvalue
        hits+=p<alpha; hits05+=p<0.05
    return hits/B, hits05/B
def power_norm(sd,n=25,shift=0.10,B=4000,alpha=0.05/3):
    h=0
    for _ in range(B):
        s=rng.normal(shift,sd,n); h+=wilcoxon(s).pvalue<alpha
    return h/B
print('registered check, normal SD 0.10:',power_norm(0.10),' SD 0.15:',power_norm(0.15))
for outcome in('omission','coverage_target'):
    for layout in('S1','S2'):
        for a,b in(('T','D'),('T','M'),('D','M')):
            d=region_diffs(outcome,layout,a,b)
            pe,p05=power(d)
            print(outcome,layout,f'{a}-{b}','n_regions',len(d),'mean',round(d.mean(),3),'SD',round(d.std(ddof=1),3),'power@10pt Holm-first',round(pe,3),'at .05',round(p05,3),'normal-SD power',power_norm(d.std(ddof=1),B=2000))
