import numpy as np, pandas as pd, json, os, xarray as xr
c=np.load('/tmp/sst_cache.npz')
A=c['A']; days=pd.to_datetime(c['days']); lat=c['lat']; lon=c['lon']
ext=pd.date_range('1991-12-27','2003-01-05')
assert (days[:len(ext)]==ext).all()
SST_b=A[:len(ext)]           # baseline-extended block, dates ext
T=A[len(ext):]               # target block
tdays=days[len(ext):]
# doy by month-day
def doy(ts):
    md=[]
    out=[]
    for t in ts:
        if t.month==2 and t.day==29: out.append(60); continue
        dd=pd.Timestamp(year=2000,month=t.month,day=t.day)  # leap year reference
        out.append(dd.dayofyear if not (t.month>2 and False) else dd.dayofyear)
    return np.array(out)
doy_ext=doy(ext)
# leap-year reference gives Feb29=60, Mar1=61, Dec31=366 -> correct mapping
assert doy(pd.DatetimeIndex(['2001-03-01']))[0]==61 and doy(pd.DatetimeIndex(['2001-12-31']))[0]==366
bl_mask=(ext>=pd.Timestamp('1992-01-01'))&(ext<=pd.Timestamp('2002-12-31'))
bl_idx=np.where(bl_mask)[0]
ny,nx=lat.size,lon.size
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
import warnings; warnings.filterwarnings('ignore')
for dd in range(1,367):
    if dd==60: continue
    bdates=[i for i in bl_idx if doy_ext[i]==dd]
    if not bdates: continue
    pool_idx=set()
    for b in bdates:
        for k in range(-5,6):
            j=b+k
            if 0<=j<len(ext): pool_idx.add(j)
    pidx=sorted(pool_idx)
    # ensure dates exist in ext range (window extension covered)
    pool=SST_b[pidx]
    thr[dd]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[dd]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(x):
    base=x[1:367]  # days 1..366 -> index 0..365
    out=np.empty_like(base)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(base[ids],axis=0)
    return out
thr366=smooth(thr); clim366=smooth(clim)
# target doys
tdoy=doy(tdays)
thr_t=thr366[tdoy-1]
# sea cells
sea=np.all(np.isfinite(T),axis=0)
print('sea cells',sea.sum(),'of',sea.size, 'thr nan in sea:',np.isnan(thr_t[:,sea]).sum())
hot=(T>=thr_t)&sea[None]
nT=T.shape[0]
mhw_cell=np.zeros((nT,ny,nx),bool)
for iy,ix in zip(*np.where(sea)):
    h=hot[:,iy,ix]
    # runs of hot
    runs=[];s=None
    for t in range(nT+1):
        v=h[t] if t<nT else False
        if v and s is None: s=t
        if not v and s is not None:
            if t-s>=5: runs.append([s,t-1])
            s=None
    # join gaps of 1-2 non-hot days
    merged=[]
    for r in runs:
        if merged and r[0]-merged[-1][1]-1 in (1,2):
            merged[-1][1]=r[1]
        else: merged.append(list(r))
    for s_,e_ in merged: mhw_cell[s_:e_+1,iy,ix]=True
active=mhw_cell.reshape(nT,-1).any(axis=1)
events=[];s=None
for t in range(nT+1):
    v=active[t] if t<nT else False
    if v and s is None: s=t
    if not v and s is not None:
        events.append({"onset":str(tdays[s].date()),"end":str(tdays[t-1].date())}); s=None
print(len(events), events)
print('MHW cell-days', mhw_cell.sum(), 'active days', active.sum())
