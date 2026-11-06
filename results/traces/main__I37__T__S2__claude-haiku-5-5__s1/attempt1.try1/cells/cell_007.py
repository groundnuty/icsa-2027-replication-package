
import fsspec, xarray as xr, numpy as np, pandas as pd, os, json, warnings
warnings.filterwarnings('ignore')
fs = fsspec.filesystem('onedata')
f=fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds=xr.open_dataset(f,engine='h5netcdf')
sub=ds.sel(latitude=slice(60.09,61.29), longitude=slice(20.01,21.21))
b=sub.analysed_sst.sel(time=slice('1991-12-27','2003-01-05')).load()
t=sub.analysed_sst.sel(time=slice('2012-06-01','2012-08-31')).load()
os.makedirs('output',exist_ok=True)
bt=pd.DatetimeIndex(b.time.values)
tt=pd.DatetimeIndex(t.time.values)
bvals=b.values.astype(np.float64)
tvals=t.values.astype(np.float64)
NLAT,NLON=b.shape[1],b.shape[2]
def ldoy(dates): return np.array([pd.Timestamp(2000,d.month,d.day).dayofyear for d in dates])
bdoy=ldoy(bt)
base_mask=(bt>=pd.Timestamp('1992-01-01'))&(bt<=pd.Timestamp('2002-12-31'))
date2idx={d:i for i,d in enumerate(bt)}
thr=np.full((366,NLAT,NLON),np.nan); clim=np.full((366,NLAT,NLON),np.nan)
for d in range(1,367):
    if d==60: continue
    anchors=bt[base_mask & (bdoy==d)]
    idx=set()
    for a in anchors:
        for k in range(-5,6):
            dd=a+pd.Timedelta(days=k)
            if dd in date2idx: idx.add(date2idx[dd])
            else: raise RuntimeError(f"missing {dd}")
    idx=sorted(idx)
    pool=bvals[idx]
    thr[d-1]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[d-1]=np.nanmean(pool,axis=0)
thr[59]=(thr[58]+thr[60])/2; clim[59]=(clim[58]+clim[60])/2
def smooth(a):
    out=np.empty_like(a)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(a[ids],axis=0)
    return out
thr_s=smooth(thr); clim_s=smooth(clim)
sea=np.all(np.isfinite(tvals),axis=0)
print('sea cells',sea.sum(),'of',sea.size,'thr NaN in sea',np.isnan(thr_s[:,sea]).sum())
tdoy=ldoy(tt)-1
T=len(tt)
mask=np.zeros((T,NLAT,NLON),np.uint8)
for i,j in zip(*np.where(sea)):
    hot=tvals[:,i,j]>=thr_s[tdoy,i,j]
    runs=[]; k=0
    while k<T:
        if hot[k]:
            s=k
            while k<T and hot[k]: k+=1
            if k-s>=5: runs.append([s,k-1])
        else: k+=1
    merged=[]
    for r in runs:
        gap=r[0]-merged[-1][1]-1 if merged else None
        if merged and 1<=gap<=2: merged[-1][1]=r[1]
        else: merged.append(list(r))
    for s,e in merged: mask[s:e+1,i,j]=1
active=mask.reshape(T,-1).any(axis=1)
events=[]; k=0
while k<T:
    if active[k]:
        s=k
        while k<T and active[k]: k+=1
        events.append({"onset":str(tt[s].date()),"end":str(tt[k-1].date())})
    else: k+=1
print(events)
print('mhw cell-days',int(mask.sum()))
