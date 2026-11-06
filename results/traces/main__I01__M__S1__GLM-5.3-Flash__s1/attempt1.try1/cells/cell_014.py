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
doy_b = np.array([doy(start_b+dt.timedelta(days=int(i))) for i in range(allb.shape[0])])
sea = np.isfinite(np.load(f'{CACHE}/raw_target.npy')).all(axis=0)
nb = allb.shape[0]

# rows by doy
rows_by_doy = {j: np.where(doy_b==j)[0] for j in range(1,367)}

t0=time.time()
thr_raw = np.full((366,60,60), np.nan)
clim_raw = np.full((366,60,60), np.nan)
for d in range(1,367):
    if d==60: continue
    rowset = set()
    for j in range(max(1,d-5), min(366,d+5)+1):
        if j==60: continue
        for ri in rows_by_doy[j]:
            for k in range(max(0,ri-5), min(nb-1, ri+5)+1):
                rowset.add(k)
    rows=np.fromiter(sorted(rowset),dtype=int)
    block = allb[rows][:, sea]
    fin = np.isfinite(block)
    cnt = fin.sum(axis=0).astype(np.int64)
    srt = np.where(fin, block, np.inf)
    srt.sort(axis=0)
    n = cnt.astype(np.float64)
    gpos = ((n-1.0)*0.5)[:,None] + np.arange(1,block.shape[1]+1)[None,:]
    lo = np.clip(np.floor(gpos),1,None).astype(np.int64)
    hi = np.clip(np.ceil(gpos),1,None).astype(np.int64)
    v_lo = np.take_along_axis(srt, lo-1, axis=0)[0]  # lo shape (nsea,1) -> need (1,nsea)
    clim_raw[d-1][sea]=np.nanmean(block,axis=0)
print('done partial')
'''
open('/work/tmp_fix.py','w').write(script)
print('patching shapes')
r'''
The issue: lo has shape (nsea,1) because gpos = (nsea,1)+(1,nsea) -> (nsea,nsea)! That is the real bug:
gpos = ((n-1)*0.5)[:,None] + arange(1,nsea+1)[None,:] gives (nsea, nsea) - wrong.

Correct: gpos[j, c] = (n[c]-1)/2 + (j+1) for rank j. So build gpos with shape (nrows, nsea):
gpos = np.arange(1,nrows+1)[:,None] + ((n-1.0)*0.5)[None,:]
Then lo/hi are (nrows,nsea); take_along_axis along axis=0 gives first row.
'''
