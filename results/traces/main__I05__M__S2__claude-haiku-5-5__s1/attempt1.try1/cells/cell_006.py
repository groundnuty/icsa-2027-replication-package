
import xarray as xr, numpy as np, pandas as pd, json
z=np.load('/tmp/w/cache.npz')
bv=z['b'].astype(np.float64); bt=pd.DatetimeIndex(z['bt']); tv=z['t'].astype(np.float64); tt=pd.DatetimeIndex(z['tt'])
lat=z['lat']; lon=z['lon']
def doy(ts): return np.array([pd.Timestamp(2000,d.month,d.day).dayofyear for d in ts])
bdoy=doy(bt)
ntime,nlat,nlon=bv.shape
flat=bv.reshape(ntime,-1)
# baseline dates within 1992-01-01..2002-12-31
inbase=(bt>=pd.Timestamp('1992-01-01'))&(bt<=pd.Timestamp('2002-12-31'))
thr=np.full((367,flat.shape[1]),np.nan); clim=np.full((367,flat.shape[1]),np.nan)
for d in range(1,367):
    if d==60: continue
    xs=np.where(inbase&(bdoy==d))[0]
    if len(xs)==0: continue
    # date-based pool: all dates within +-5 days of any such baseline date
    sel=set()
    for i in xs:
        for k in range(-5,6): sel.add(i+k)   # bt is daily contiguous index
    sel=sorted(j for j in sel if 0<=j<ntime)
    pool=flat[sel]  # (n, cells)
    with np.errstate(all='ignore'):
        thr[d]=np.nanquantile(pool,0.9,axis=0,method='hazen')
        clim[d]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a=a[1:367]  # days 1..366 index 0..365
    out=np.empty_like(a)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=a[ids].mean(axis=0)
    return out
thrS=smooth(thr); climS=smooth(clim)
print(np.isnan(thrS[:,sea.ravel()]).sum(), thrS[:,0][:5], climS[:,0][:5])
