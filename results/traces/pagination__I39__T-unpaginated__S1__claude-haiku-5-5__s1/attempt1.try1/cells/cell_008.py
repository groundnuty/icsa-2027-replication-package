
import numpy as np, pickle, datetime as dt, json, os
import xarray as xr
dates,arr,lat,lon=pickle.load(open('/tmp/sst.pkl','rb'))
dates=[d for d in dates]
idx={d:i for i,d in enumerate(dates)}
# region selection
latm=(lat>=60.49)&(lat<=61.69); lonm=(lon>=17.25)&(lon<=18.45)
print(latm.sum(), lonm.sum(), lat[latm][[0,-1]], lon[lonm][[0,-1]])
sub=arr[:,latm][:,:,lonm]; LAT=lat[latm]; LON=lon[lonm]
ny=sub.shape[1]; nx=sub.shape[2]
mdays=[31,29,31,30,31,30,31,31,30,31,30,31]
doy_of={}
off=0
for m,L in enumerate(mdays,1):
    for dd in range(1,L+1):
        doy_of[(m,dd)]=off+dd
    off+=L
def doy(d): return doy_of[(d.month,d.day)]
base=[d for d in dates if dt.date(1992,1,1)<=d<=dt.date(2002,12,31)]
tgt=[d for d in dates if dt.date(2010,6,1)<=d<=dt.date(2010,8,31)]
print(len(base), len(tgt))
# sea cells
tidx=[idx[d] for d in tgt]
finite_all=np.all(np.isfinite(sub[tidx]),axis=0)
print('sea cells', finite_all.sum(), 'of', ny*nx)
# pools
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
pools={}
for d in base:
    k=doy(d)
    if k==60: continue
    pools.setdefault(k,set())
    for off_ in range(-5,6):
        t=d+dt.timedelta(off_)
        if t in idx: pools[k].add(idx[t])
for k in range(1,367):
    if k==60: continue
    ii=sorted(pools[k])
    x=sub[ii]
    with np.errstate(all='ignore'):
        thr[k]=np.nanquantile(x,0.9,axis=0,method='hazen')
        clim[k]=np.nanmean(x,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a=a[1:367]  # 366 array indices 0..365 -> doy 1..366
    out=np.empty_like(a)
    for i in range(366):
        ids=[(i+j)%366 for j in range(-15,16)]
        out[i]=np.mean(a[ids],axis=0)
    return out
T=smooth(thr); C=smooth(clim)  # index i -> doy i+1
print('pool sizes', {k:len(pools[k]) for k in [1,59,61,366]})
print(np.isfinite(T[:,finite_all]).all(), np.isfinite(C[:,finite_all]).all())
