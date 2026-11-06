script = r'''
import numpy as np, datetime as dt, time

CACHE='/work/cache'
raw_91=np.load(f'{CACHE}/raw_b1991.npy'); raw=np.load(f'{CACHE}/raw_bmain.npy'); raw_03=np.load(f'{CACHE}/raw_b2003.npy')

def isleap(y): return y%4==0 and (y%100!=0 or y%400==0)
def doy(d):
    o = (d - dt.date(d.year,1,1)).days + 1
    if not isleap(d.year) and (d.month,d.day) >= (3,1):
        o += 1
    return o

allb = np.concatenate([raw_91,raw,raw_03],axis=0)
start_b = dt.date(1991,12,27)
nb = allb.shape[0]
doy_b = np.array([doy(start_b+dt.timedelta(days=int(i))) for i in range(nb)])
sea = np.isfinite(np.load(f'{CACHE}/raw_target.npy')).all(axis=0)
rows_by_doy = {j: np.where(doy_b==j)[0] for j in range(1,367)}

t0=time.time()
thr_raw = np.full((366,60,60), np.nan)
clim_raw = np.full((366,60,60), np.nan)
poolsizes = np.zeros(367, dtype=np.int64)
for d in range(1,367):
    if d==60: continue
    rowset = set()
    for j in range(max(1,d-5), min(366,d+5)+1):
        if j==60: continue
        for ri in rows_by_doy[j]:
            rowset.update(range(max(0,ri-5), min(nb-1, ri+5)+1))
    rows=np.fromiter(sorted(rowset),dtype=np.int64)
    block = allb[rows][:, sea]
    fin = np.isfinite(block)
    cnt = fin.sum(axis=0).astype(np.int64)
    srt = np.where(fin, block, np.inf)
    srt.sort(axis=0, kind='stable')
    n = cnt.astype(np.float64)
    gpos = np.arange(1.0, block.shape[0]+1)[:,None] + ((n-1.0)*0.5)[None,:]
    g0 = gpos[0]
    lo = np.clip(np.floor(g0),1,None).astype(np.int64)
    hi = np.clip(np.ceil(g0),1,None).astype(np.int64)
    cols = np.arange(block.shape[1])
    v_lo = srt[lo, cols]; v_hi = srt[hi, cols]
    frac = g0 - lo
    q = v_lo + frac*(v_hi-v_lo)
    q[cnt==0]=np.nan
    thr_raw[d-1][sea]=q
    clim_raw[d-1][sea]=np.nanmean(block,axis=0)
    poolsizes[d]=int(cnt.min())
print('pools+stats built', f'{time.time()-t0:.1f}s')
np.save(f'{CACHE}/thr_raw.npy',thr_raw); np.save(f'{CACHE}/clim_raw.npy',clim_raw)

rng = np.random.default_rng(0)
checks=[]
for d in [1, 59, 61, 183, 244, 366]:
    rowset=set()
    for j in range(max(1,d-5), min(366,d+5)+1):
        if j==60: continue
        for ri in rows_by_doy[j]:
            rowset.update(range(max(0,ri-5), min(nb-1, ri+5)+1))
    rows=np.fromiter(sorted(rowset),dtype=np.int64)
    block = allb[rows][:, sea]
    seacols = np.where(sea.ravel())[0]
    for c in rng.integers(0, seacols.size, size=4):
        col = seacols[c]
        vals = block[:,c]; vals = vals[np.isfinite(vals)]
        mine = float(thr_raw[d-1].ravel()[col])
        ref = float(np.quantile(vals, 0.9, method='hazen'))
        checks.append((d,int(c),mine,ref,abs(mine-ref)))
print('max |mine-np.hazen| =', max(x[4] for x in checks))
print('poolsizes min/max over doys:', poolsizes[poolsizes>0].min(), poolsizes.max())
print('poolsizes[1,2,59,61,183,366]:', poolsizes[[1,2,59,61,183,366]])
print('thr_raw[59] vs [60](nan) vs [61] sample cell:', thr_raw[58,30,30], thr_raw[59,30,30], thr_raw[60,30,30])
print('clim similar:', clim_raw[58,30,30], clim_raw[59,30,30], clim_raw[60,30,30])
'''
open('/work/stage2.py','w').write(script)
import subprocess
r=subprocess.run(['python','/work/stage2.py'],capture_output=True,text=True)
print(r.stdout[-3000:]); print(r.stderr[-2000:])
