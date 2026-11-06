import numpy as np, datetime as dt, calendar
from numpy.lib.stride_tricks import sliding_window_view

z=np.load('/work/extracted.npz', allow_pickle=False)
ext=z['ext']; tgt=z['tgt']
EXT=[dt.date.fromisoformat(s) for s in z['ext_dates']]
TGT=[dt.date.fromisoformat(s) for s in z['tgt_dates']]
r=np.load('/work/results.npz')
sea=r['sea']; thr_raw=r['thr_raw']; clim_raw=r['clim_raw']; thr_sm=r['thr_sm']; clim_sm=r['clim_sm']
sea_idx=r['sea_idx']; mhw=r['mhw']; hot=r['hot']
ext_sea = ext.reshape(ext.shape[0], -1)[:, sea_idx]
tgt_sea = tgt.reshape(tgt.shape[0], -1)[:, sea_idx]

def doy_of(d):
    y=d.timetuple().tm_yday
    if calendar.isleap(d.year): return y
    return y+1 if y>=60 else y

# ---- independent pool builder by explicit date arithmetic (no index reuse)
ext_by_date={d:i for i,d in enumerate(EXT)}
def pool_dates(d0):  # d0 = 0-based doy
    out=[]
    for y in range(1992,2003):
        # baseline date in year y with this doy
        bd = dt.date(y,1,1)+dt.timedelta(days=d0 if d0<59 else d0-1)
        # careful: if d0>=59 (i.e., >=Mar1 in mapped numbering), Jan1 + (d0-1) days? verify:
        dd = dt.date(y,1,1)
        # find calendar date with doy_of == d0+1
        cand=dd
        while doy_of(cand)!=d0+1: cand+=dt.timedelta(days=1)
        for o in range(-5,6):
            cd=cand+dt.timedelta(days=o)
            out.append(ext_by_date[cd])
    return out

def hazen_manual(v, p=0.9):
    v=np.sort(np.asarray(v,dtype=np.float64))
    n=len(v)
    pos=(np.arange(1,n+1)-0.5)/n
    if p<=pos[0]: return v[0]
    if p>=pos[-1]: return v[-1]
    i=np.searchsorted(pos,p)
    return v[i-1] + (p-pos[i-1])/(pos[i]-pos[i-1])*(v[i]-v[i-1])

rng=np.random.default_rng(0)
test_doys=[0, 59, 60, 152, 153, 182, 212, 243, 244, 364, 365, 58, 61]
test_cells=[0, 1, 500, 1500, 3300, 3301]
ok=True
for d0 in test_doys:
    di = pool_dates(d0) if d0!=59 else None
    for ci in test_cells:
        if d0!=59:
            vals = ext_sea[di, ci].astype(np.float64)
            t_ref = hazen_manual(vals); c_ref = vals.mean()
        else:
            t_ref = 0.5*(thr_raw[58,ci]+thr_raw[60,ci]); c_ref = 0.5*(clim_raw[58,ci]+clim_raw[60,ci])
        dt_=abs(thr_raw[d0,ci]-t_ref); dc=abs(clim_raw[d0,ci]-c_ref)
        if dt_>1e-9 or dc>1e-9:
            ok=False; print('MISMATCH doy0',d0,'cell',ci, thr_raw[d0,ci], t_ref, clim_raw[d0,ci], c_ref)
print('raw threshold/climatology brute-force check (12 doys x 6 cells):', 'ALL OK' if ok else 'FAILED')

# ---- smoothing check: independent direct loop
ok=True
for d0 in [0, 15, 59, 152, 182, 365]:
    window=[(d0+k)%366 for k in range(-15,16)]
    t_ref=thr_raw[window,:].mean(axis=0)
    c_ref=clim_raw[window,:].mean(axis=0)
    if np.abs(thr_sm[d0]-t_ref).max()>1e-12 or np.abs(clim_sm[d0]-c_ref).max()>1e-12:
        ok=False; print('SMOOTH MISMATCH at doy0', d0)
print('circular 31-day smoothing check:', 'ALL OK' if ok else 'FAILED')

# ---- hot-day check for a few days
ok=True
for t in [0, 25, 30, 66, 70, 91]:
    d0=(doy_of(TGT[t])-1)
    h=(tgt_sea[t].astype(np.float64)>=thr_sm[d0])
    if not np.array_equal(h, hot[t]): ok=False; print('HOT MISMATCH day', TGT[t])
print('hot-day comparison check:', 'ALL OK' if ok else 'FAILED')

# ---- stats
print('mhw mask days per cell: max', int(mhw.sum(axis=0).max()), 'mean', round(float(mhw.sum()/mhw.shape[1]),3))
print('cells with mhw on >=1 day:', int((mhw.sum(axis=0)>0).sum()))
print('per-cell MHW total cell-days:', int(mhw.sum()))
# distribution of per-cell MHW lengths
seg_lens=[]
for c in range(mhw.shape[1]):
    col=mhw[:,c]; hp=np.concatenate(([False],col,[False])); d=np.diff(hp.astype(np.int8))
    st=np.where(d==1)[0]; en=np.where(d==-1)[0]-1
    for s,e in zip(st,en): seg_lens.append(int(e-s+1))
import collections
print('n per-cell segments:', len(seg_lens), 'length hist:', dict(sorted(collections.Counter(seg_lens).items())))
