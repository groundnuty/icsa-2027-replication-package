script = r'''
import numpy as np, datetime as dt, time, os

CACHE='/work/cache'
raw_91=np.load(f'{CACHE}/raw_b1991.npy'); raw=np.load(f'{CACHE}/raw_bmain.npy'); raw_03=np.load(f'{CACHE}/raw_b2003.npy')
raw_t=np.load(f'{CACHE}/raw_target.npy')

def isleap(y): return y%4==0 and (y%100!=0 or y%400==0)
def doy(d):
    o = (d - dt.date(d.year,1,1)).days + 1
    if not isleap(d.year) and (d.month,d.day) >= (3,1):
        o += 1
    return o

allb = np.concatenate([raw_91,raw,raw_03],axis=0)   # dates 1991-12-27 .. 2003-01-05
start_b = dt.date(1991,12,27)
doy_b = np.array([doy(start_b+dt.timedelta(days=int(i))) for i in range(allb.shape[0])])
doy_t = np.array([doy(dt.date(2008,6,1)+dt.timedelta(days=int(i))) for i in range(raw_t.shape[0])])
sea = np.isfinite(raw_t).all(axis=0)

def daterange(a,b):
    d=a
    while d<=b:
        yield d
        d+=dt.timedelta(days=1)

# day-index lists by doy; windows by calendar dates
day_idx = {}       # calendar date -> row index in allb
date_rows = {}
for i in range(allb.shape[0]):
    date_rows[start_b+dt.timedelta(days=i)] = i

t0=time.time()
thr_raw = np.full((366,60,60), np.nan)
clim_raw = np.full((366,60,60), np.nan)
for d in range(1,367):
    if d==60: continue
    # pool = union of +-5 calendar day windows around baseline dates with doy j, for j in neighbours
    rows=set()
    for j in range(max(1,d-5), min(366,d+5)+1):
        if j==60: continue
        for date,ri in date_rows.items():
            if doy_b[ri]==j:
                dd=(date-start_b).days
                for k in range(max(0,dd-5), min(allb.shape[0]-1, dd+5)+1):
                    rows.add(k)
    rows=np.array(sorted(rows),dtype=int)
    block = allb[rows][:, sea]                     # (nrows, nsea) float64
    fin = np.isfinite(block)
    cnt = fin.sum(axis=0).astype(np.int64)
    srt = np.where(fin, block, np.inf)
    srt.sort(axis=0)                               # NaNs->inf pushed to end
    n = cnt.astype(np.float64)
    h = (n - 1.0) * 0.5                            # Hazen plotting position
    gpos = h[:,None] + (np.arange(block.shape[1])[None,:] + 1.0)  # rank g (1-based)
    lo = np.floor(gpos).astype(np.int64); hi = np.ceil(gpos).astype(np.int64)
    np.clip(lo,1,None,out=lo); np.clip(hi,1,None,out=hi)
    idxs = (lo-1)
    v_lo = np.take_along_axis(srt, idxs[None,:], axis=0)[0]
    v_hi = np.take_along_axis(srt, (hi-1)[None,:], axis=0)[0]
    frac = gpos - lo
    q = v_lo + frac*(v_hi - v_lo)
    q[cnt==0]=np.nan
    thr_raw[d-1][sea]=q
    clim_raw[d-1][sea]=np.nanmean(block,axis=0)
print('pools+stats built', f'{time.time()-t0:.1f}s')
np.save(f'{CACHE}/thr_raw.npy',thr_raw); np.save(f'{CACHE}/clim_raw.npy',clim_raw)

# sanity
print('thr finite days check: all non-60 doys finite on sea?', np.all(np.isfinite(thr_raw[[d-1 for d in range(1,367) if d!=60]][:,sea])))
print('thr_raw[59] vs [60] vs [61] sample:', thr_raw[58,0,0], thr_raw[59,0,0], thr_raw[60,0,0])
print('pool row-count examples:')
def nrows(d):
    rows=set()
    for j in range(max(1,d-5), min(366,d+5)+1):
        if j==60: continue
        for date,ri in date_rows.items():
            if doy_b[ri]==j:
                dd=(date-start_b).days
                for k in range(max(0,dd-5), min(allb.shape[0]-1, dd+5)+1):
                    rows.add(k)
    return len(rows)
print('nrows doy 1,2,59,61,366:', nrows(1), nrows(2), nrows(59), nrows(61), nrows(366))
'''
open('/work/stage2.py','w').write(script)
import subprocess
r=subprocess.run(['python','/work/stage2.py'],capture_output=True,text=True)
print(r.stdout[-3000:]); print(r.stderr[-2000:])
