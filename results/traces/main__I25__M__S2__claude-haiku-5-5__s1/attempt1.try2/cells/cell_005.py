
import pandas as pd, json, os, warnings
import xarray as xr, numpy as np
warnings.filterwarnings('ignore')
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(p,engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=57.57)&(lat<=58.77))[0]; lo=np.where((lon>=10.25)&(lon<=11.45))[0]
sub=ds.isel(latitude=la,longitude=lo)
base=sub.sel(time=slice('1991-12-27','2003-01-05')).analysed_sst.load()
tgt=sub.sel(time=slice('2016-06-01','2016-08-31')).analysed_sst.load()
bt=pd.DatetimeIndex(base.time.values)
def doy(d): return pd.Timestamp(2000,d.month,d.day).dayofyear  # 2000 leap: Feb29->60
bdoy=np.array([doy(d) for d in bt])
print(doy(pd.Timestamp('2001-03-01')), doy(pd.Timestamp('2001-02-28')), doy(pd.Timestamp('2001-12-31')))
# baseline dates within 1992-2002
inb=(bt>=pd.Timestamp('1992-01-01'))&(bt<=pd.Timestamp('2002-12-31'))
vals=base.values.reshape(len(bt),-1).astype(np.float64)
thr=np.full((367,vals.shape[1]),np.nan); clim=np.full_like(thr,np.nan)
for d in range(1,367):
    if d==60: continue
    bdates=bt[inb & (bdoy==d)]
    if len(bdates)==0: print('no base',d); continue
    sel=np.zeros(len(bt),bool)
    for b in bdates:
        sel|=(np.abs((bt-b).days)<=5)
    pool=vals[sel]
    thr[d]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[d]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a=a[1:367]  # index 0..365 for doy1..366
    out=np.empty_like(a)
    for i in range(366):
        idx=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(a[idx],axis=0)
    return out
thr_s=smooth(thr); clim_s=smooth(clim)  # index doy-1
print(np.isnan(thr_s).sum(), thr_s[100].min(), thr_s[100].max())
# target
tt=pd.DatetimeIndex(tgt.time.values); tdoy=np.array([doy(d) for d in tt])
tv=tgt.values.reshape(len(tt),-1).astype(np.float64)
sea=np.all(np.isfinite(tv),axis=0)
print('sea cells',sea.sum(),'of',tv.shape[1])
thr_t=thr_s[tdoy-1]
hot=(tv>=thr_t)&sea[None,:]
hot&=np.isfinite(thr_t)
mhw=np.zeros_like(hot)
for c in np.where(sea)[0]:
    h=hot[:,c]; n=len(h)
    # runs
    runs=[]; i=0
    while i<n:
        if h[i]:
            j=i
            while j<n and h[j]: j+=1
            if j-i>=5: runs.append([i,j-1])
            i=j
        else: i+=1
    # join gaps of 1-2 days
    merged=[]
    for r in runs:
        if merged and (r[0]-merged[-1][1]-1) in (1,2): merged[-1][1]=r[1]
        else: merged.append(list(r))
    for s,e in merged: mhw[s:e+1,c]=True
active=mhw.any(axis=1)
events=[]; i=0; n=len(active)
while i<n:
    if active[i]:
        j=i
        while j<n and active[j]: j+=1
        events.append({'onset':str(tt[i].date()),'end':str(tt[j-1].date())}); i=j
    else: i+=1
print(events)
print('mhw cell-days',mhw.sum())
