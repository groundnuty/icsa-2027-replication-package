import numpy as np, datetime as dt, json, os
import xarray as xr
c=np.load('/tmp/cache.npz')
V=c['V']; LA=c['LA']; LO=c['LO']; dates=[dt.datetime.strptime(s,'%Y%m%d').date() for s in c['dates']]
start=dates[0]
def doy(d): return dt.date(2000,d.month,d.day).timetuple().tm_yday
base_lo,base_hi=dt.date(1992,1,1),dt.date(2002,12,31)
ndate=len(dates)
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
bdates=[d for d in dates if base_lo<=d<=base_hi]
bidx_by_doy={}
for b in bdates:
    bidx_by_doy.setdefault(doy(b),[]).append(b)
for d in range(1,367):
    if d==60: continue
    if d not in bidx_by_doy: continue
    idxs=set()
    for b in bidx_by_doy[d]:
        for k in range(-5,6):
            t=b+dt.timedelta(k)
            idxs.add((t-start).days)
    idxs=sorted(i for i in idxs if 0<=i<ndate)
    pool=V[idxs]  # (n,60,60)
    with np.errstate(all='ignore'):
        thr[d]=np.nanquantile(pool,0.9,axis=0,method='hazen')
        clim[d]=np.nanmean(pool,axis=0)
# check: days with no baseline date at all
missing=[d for d in range(1,367) if d!=60 and d not in bidx_by_doy]
print('missing doy',missing)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a=a[1:367]  # index 0..365 for doy1..366
    out=np.empty_like(a)
    for i in range(366):
        ii=[(i+k)%366 for k in range(-15,16)]
        out[i]=a[ii].mean(axis=0)
    return out
thr_s=smooth(thr); clim_s=smooth(clim)
print(thr_s.shape, np.isnan(thr_s).sum(), np.isnan(clim_s).sum())
print(thr_s[:,30,30][[0,59,152,200]] if True else '')