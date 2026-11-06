import numpy as np, datetime as dt, json, os, warnings
warnings.filterwarnings('ignore')
import xarray as xr
c=np.load('/work/s/coords.npz'); LAT=c['lat']; LON=c['lon']
start=dt.date(1991,12,27); end=dt.date(2012,8,31)
days=[start+dt.timedelta(i) for i in range((end-start).days+1)]
N=len(days)
S=np.empty((N,LAT.size,LON.size))
for i,d in enumerate(days):
    S[i]=np.load(f'/work/s/sub/{d:%Y%m%d}.npz')['sst']
idx={d:i for i,d in enumerate(days)}
def doy(d):
    # fixed leap calendar mapping
    return (d.replace(year=2000)-dt.date(2000,1,1)).days+1
# target
tgt=[dt.date(2012,6,1)+dt.timedelta(i) for i in range(92)]
ti=[idx[d] for d in tgt]
T=S[ti]
sea=np.all(np.isfinite(T),axis=0)
print('sea cells', sea.sum(), 'of', sea.size, 'NaN in region target any:', np.isnan(T).any(axis=0).sum())
# baseline pools
thr=np.full((367,)+sea.shape,np.nan); clim=np.full((367,)+sea.shape,np.nan)
for d in range(1,367):
    if d==60: continue
    md=dt.date(2000,1,1)+dt.timedelta(d-1)
    vals=[]
    for Y in range(1992,2003):
        b=dt.date(Y,md.month,md.day)
        for k in range(-5,6):
            x=b+dt.timedelta(k)
            vals.append(S[idx[x]])
    P=np.stack(vals)
    thr[d]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[d]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a=a[1:367]  # 366 entries, index0=doy1
    out=np.empty_like(a)
    for i in range(366):
        ks=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(a[ks],axis=0)
    return out
thrS=smooth(thr); climS=smooth(clim)
print('nan thr sea cells:', np.isnan(thrS[:,sea]).sum(), 'nan clim', np.isnan(climS[:,sea]).sum())
print(thrS[:,sea].min(), thrS[:,sea].max())