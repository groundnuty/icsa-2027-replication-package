
import fsspec, xarray as xr, numpy as np, pandas as pd, os, json, warnings
warnings.filterwarnings('ignore')
fs = fsspec.filesystem('onedata')
f=fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds=xr.open_dataset(f,engine='h5netcdf')
sub=ds.sel(latitude=slice(60.09,61.29), longitude=slice(20.01,21.21))
b=sub.analysed_sst.sel(time=slice('1991-12-27','2003-01-05')).load()
t=sub.analysed_sst.sel(time=slice('2012-06-01','2012-08-31')).load()
bt=pd.DatetimeIndex(b.time.values); tt=pd.DatetimeIndex(t.time.values)
bvals=b.values.astype(np.float64); tvals=t.values.astype(np.float64)
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
            idx.add(date2idx[dd])
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
tdoy=ldoy(tt)-1
print('sea',sea.sum())
print('target SST sea range',np.nanmin(tvals[:,sea]),np.nanmax(tvals[:,sea]),np.nanmean(tvals[:,sea]))
print('baseline range',np.nanmin(bvals),np.nanmax(bvals))
print('thr sea mean at Jun-Aug', thr_s[tdoy][:,sea].mean(), 'clim', clim_s[tdoy][:,sea].mean())
ex=(tvals-thr_s[tdoy])[:,sea]
print('max excess',np.nanmax(ex),'frac hot',np.mean(ex>=0))
print('daily mean SST sea', np.round(np.nanmean(tvals[:,sea],axis=1),2))
print('daily mean thr', np.round(np.nanmean(thr_s[tdoy][:,sea],axis=1),2))
