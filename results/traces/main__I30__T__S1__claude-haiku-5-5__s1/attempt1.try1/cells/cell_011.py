
import numpy as np, datetime as dt, json, os
z=np.load('/tmp/sst.npz')
sst=z['sst'][:,0] if z['sst'].ndim==4 else z['sst']
lat=z['lat']; lon=z['lon']; ds_str=z['days']
print(sst.shape, lat[[0,-1]], lon[[0,-1]], ds_str[0], ds_str[-1])
dates=[dt.date(int(s[:4]),int(s[4:6]),int(s[6:])) for s in ds_str]
idx={d:i for i,d in enumerate(dates)}
# leap-style doy
def doy(d):
    ld=dt.date(2000,d.month,d.day)  # leap year
    return ld.timetuple().tm_yday
# check mapping
assert doy(dt.date(2001,2,28))==59 and doy(dt.date(2001,3,1))==61 and doy(dt.date(2000,12,31))==366
# pools
base0,base1=dt.date(1992,1,1),dt.date(2002,12,31)
pool_idx={d:set() for d in range(1,367) if d!=60}
b=base0
while b<=base1:
    d=doy(b)
    if d!=60:
        for k in range(-5,6):
            x=b+dt.timedelta(k)
            pool_idx[d].add(idx[x])
    b+=dt.timedelta(1)
ny,nx=sst.shape[1:]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
for d in pool_idx:
    ii=sorted(pool_idx[d])
    sub=sst[ii]
    with np.errstate(all='ignore'):
        thr[d]=np.nanquantile(sub,0.9,axis=0,method='hazen')
        clim[d]=np.nanmean(sub,axis=0)
thr=thr[1:]; clim=clim[1:]  # index doy-1
thr[59]=(thr[58]+thr[60])/2; clim[59]=(clim[58]+clim[60])/2
def smooth(a):
    out=np.empty_like(a)
    for d in range(366):
        ii=[(d+k)%366 for k in range(-15,16)]
        out[d]=a[ii].mean(axis=0)
    return out
thr_s=smooth(thr); clim_s=smooth(clim)
print(np.isnan(thr_s).sum(), thr_s[150:156,30,30], clim_s[150,30,30])
