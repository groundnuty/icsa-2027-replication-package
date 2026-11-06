
import xarray as xr, numpy as np, pandas as pd, json, os
d=np.load('/tmp/w/d.npz')
base=d['base']; btime=pd.to_datetime(d['btime']); tv=d['tv']; ttime=pd.to_datetime(d['ttime']); latv=d['lat']; lonv=d['lon']
ny,nx=base.shape[1:]
# doy table via leap year 2000
ref=pd.date_range('2000-01-01','2000-12-31')
md2doy={(t.month,t.day):t.dayofyear for t in ref}
doy_of=lambda idx: np.array([md2doy[(t.month,t.day)] for t in idx])
bdoy=doy_of(btime); tdoy=doy_of(ttime)
# sea cells: finite every target day
sea=np.isfinite(tv).all(axis=0)
print('sea cells', sea.sum(), 'partial-NaN target cells', (np.isfinite(tv).any(axis=0)&~sea).sum())
# baseline partial NaN check
print('baseline all-NaN cells', (~np.isfinite(base).any(axis=0)).sum())
# pools per doy
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
bvals=base
for doy in range(1,367):
    if doy==60: continue
    md=ref[doy-1]
    pool_idx=[]
    for y in range(1992,2003):
        s=pd.Timestamp(year=y,month=md.month,day=md.day)
        m=(btime>=s-pd.Timedelta(days=5))&(btime<=s+pd.Timedelta(days=5))
        pool_idx.append(np.where(m)[0])
    idx=np.unique(np.concatenate(pool_idx))
    P=base[idx]
    thr[doy]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[doy]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a=a[1:367]  # 366 elements, index 0..365 => doy 1..366
    out=np.empty_like(a)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=a[ids].mean(axis=0)
    return out
T=smooth(thr); C=smooth(clim)  # index doy-1
print(np.isnan(T[:,sea]).sum(), np.isnan(C[:,sea]).sum())
