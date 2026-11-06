import numpy as np, datetime as dt
CACHE='/work/cache'
raw_t=np.load(f'{CACHE}/raw_target.npy'); thr=np.load(f'{CACHE}/thr_smooth.npy')
per_cell=np.load(f'{CACHE}/per_cell.npy')
sea=np.isfinite(raw_t).all(axis=0)
doy=[153+k for k in range(92)]
dates=[dt.date(2008,6,1)+dt.timedelta(days=k) for k in range(92)]
hot=(raw_t>=np.stack([thr[d-1] for d in doy])) & sea[None]
act=per_cell.any(axis=(1,2))
# 19 Jun: hot cells but no active -> are those hot cells outside any >=5-run?
k=18
hm=hot[k]; pm=per_cell[k]
print(dates[k], 'hot cells', int(hm.sum()), 'in-MHW cells', int(pm.sum()))
import collections
# how many hot cells belong to a run >=5 (before gap-joining) that ended before/after?
# simpler: check per-cell runs statistics
# cells whose MHW covers 19 Jun: runs containing day 18
print('sample cells hot on 19Jun with their full series (first 5):')
cnt=0
for a,b in zip(*np.where(hm)):
    if not pm[a,b]:
        h=hot[:,a,b]
        # show window
        w=''.join('H' if h[i] else '.' for i in range(10,30))
        print(f'cell({a},{b}) days11-30:', w)
        cnt+=1
        if cnt>=8: break
# distribution of hot-cell counts in mid-June
print()
for k in range(12,28):
    print(dates[k], 'hot', int(hot[k].sum()), 'active', int(act[k]))
