script = r'''
import numpy as np, datetime as dt, time

CACHE='/work/cache'
raw_91=np.load(f'{CACHE}/raw_b1991.npy'); raw=np.load(f'{CACHE}/raw_bmain.npy'); raw_03=np.load(f'{CACHE}/raw_b2003.npy')
raw_t=np.load(f'{CACHE}/raw_target.npy')

def doy(d):  # 1..366 by month/day
    return (dt.date(d.year,d.month,d.day)-dt.date(d.year,1,1)).days + 1

# all baseline data in one block with date index offset
N91,N,N03 = raw_91.shape[0], raw.shape[0], raw_03.shape[0]
allb = np.concatenate([raw_91,raw,raw_03],axis=0)
def dnum(d): return (d-dt.date(1991,12,27)).days
d1b, d2b = dnum(dt.date(1991,12,27)), dnum(dt.date(2002,12,31))
doy_b = np.array([doy(dt.date(1991,12,27)+dt.timedelta(days=int(i))) for i in range(allb.shape[0])])
print('baseline block', allb.shape, doy_b[:3], doy_b[-3:])

# group baseline day-indices by doy
from collections import defaultdict
bydoy=defaultdict(list)
for i,dv in enumerate(doy_b):
    bydoy[int(dv)].append(i)

# dates of target (2008) for doy mapping
doy_t = np.array([doy(dt.date(2008,6,1)+dt.timedelta(days=int(i))) for i in range(raw_t.shape[0])])
print('target doys', doy_t.min(), doy_t.max())

# need target cells that are finite on all target days
sea = np.isfinite(raw_t).all(axis=0)
print('sea cells', sea.sum(), 'of', sea.size)

# build per-DOY pools over sea cells
vals_doy = {}
t0=time.time()
for d in range(1,367):
    idx=[]
    for j in range(max(1,d-5), min(366,d+5)+1):
        if j==60: continue
        if j in bydoy: idx.extend(bydoy[j])
    idx=np.array(idx,dtype=int)
    block = allb[idx][:, sea]          # (nidx, nsea)
    vals_doy[d]=block[np.isfinite(block)]
print('pools built', f'{time.time()-t0:.1f}s')
tot=sum(v.size for v in vals_doy.values())
print('total pool values', tot)
for d in [1,2,59,61,183,366]:
    print('pool size doy',d,vals_doy[d].size)
# check doy60 pool is only from 29feb dates
print('leap dates in baseline:', sum(1 for i in range(allb.shape[0]) if doy_b[i]==60))
'''
open('/work/stage2_check.py','w').write(script)
import subprocess
r=subprocess.run(['python','/work/stage2_check.py'],capture_output=True,text=True)
print(r.stdout[-3000:]); print(r.stderr[-2000:])
