import numpy as np,pandas as pd,json,os
data=np.load('/tmp/data.npy');lat=np.load('/tmp/lat.npy');lon=np.load('/tmp/lon.npy')
idx=pd.date_range('1991-12-27','2003-01-05')
nb=len(idx);base=data[:nb];tgt=data[nb:]
def doy(t): return np.where(t.is_leap_year|True, 0,0)
def mdoy(ts):
    return np.array([ (pd.Timestamp(2000,t.month,t.day).dayofyear) for t in ts])  # 2000 leap
bd=mdoy(idx)
pos={i:k for k,i in enumerate(idx)}
inb=(idx>=pd.Timestamp('1992-01-01'))&(idx<=pd.Timestamp('2002-12-31'))
thr=np.full((366,)+base.shape[1:],np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60: continue
    c=np.where(inb&(bd==d))[0]
    ids=sorted({j for k in c for j in range(k-5,k+6) if 0<=j<nb})
    pool=base[ids]
    thr[d-1]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[d-1]=np.nanmean(pool,axis=0)
for a in(thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,-k,axis=0) for k in range(-15,16))/31
thr=sm(thr)
tidx=pd.date_range('2013-06-01','2013-08-31');td=mdoy(tidx)
sea=np.isfinite(tgt).all(0)
hot=(tgt>=thr[td-1])&sea
T=len(tidx);mhw=np.zeros(hot.shape,bool)
for i in range(60):
  for j in range(60):
    if not sea[i,j]:continue
    h=hot[:,i,j];runs=[];t=0
    while t<T:
        if h[t]:
            s=t
            while t<T and h[t]:t+=1
            if t-s>=5:runs.append([s,t-1])
        else:t+=1
    m=[]
    for r in runs:
        if m and r[0]-m[-1][1]-1<=2:m[-1][1]=r[1]
        else:m.append(r)
    for s,e in m:mhw[s:e+1,i,j]=True
act=mhw.any((1,2));ev=[];t=0
while t<T:
    if act[t]:
        s=t
        while t<T and act[t]:t+=1
        ev.append({"onset":str(tidx[s].date()),"end":str(tidx[t-1].date())})
    else:t+=1
print(sea.sum(),ev)
os.makedirs('output',exist_ok=True)
xr=__import__('xarray')
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':tidx,'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":57.85,"lat_max":59.05,"lon_min":21.01,"lon_max":22.21},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2013-06-01","end":"2013-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))