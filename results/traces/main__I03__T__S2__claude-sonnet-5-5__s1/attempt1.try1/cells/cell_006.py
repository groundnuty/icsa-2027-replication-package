import xarray as xr,numpy as np,pandas as pd,json,os
base=xr.open_dataarray("/tmp/b.nc");tg=xr.open_dataarray("/tmp/t.nc")
T=pd.DatetimeIndex(base.time); B=base.values.astype(np.float64)
def doy(t): return np.array([pd.Timestamp(2000,x.month,x.day).dayofyear for x in t])
D=doy(T)
tgt=tg.values.astype(np.float64)
sea=np.isfinite(tgt).all(0)
core=np.where((T>="1992-01-01")&(T<="2002-12-31"))[0]
thr=np.full((366,)+sea.shape,np.nan)
for d in range(1,367):
    if d==60: continue
    idx=set()
    for i in core:
        if D[i]==d: idx.update(range(max(0,i-5),min(len(T),i+6)))
    P=B[sorted(idx)]
    thr[d-1]=np.nanquantile(P,0.9,axis=0,method="hazen")
thr[59]=(thr[58]+thr[60])/2
thr=sum(np.roll(thr,-k,axis=0) for k in range(-15,16))/31
dates=pd.DatetimeIndex(tg.time);Dt=doy(dates)
hot=(tgt>=thr[Dt-1])&sea
n=len(Dt);m=np.zeros_like(hot)
for i in range(60):
  for j in range(60):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];s=None
    for t in range(n+1):
        if t<n and h[t]:
            if s is None:s=t
        elif s is not None:
            if t-s>=5:runs.append([s,t-1])
            s=None
    mm=[]
    for r in runs:
        if mm and r[0]-mm[-1][1]-1<=2: mm[-1][1]=r[1]
        else: mm.append(r)
    for a,b in mm:m[a:b+1,i,j]=True
act=m.any((1,2));ev=[];s=None
for t in range(n+1):
    if t<n and act[t]:
        if s is None:s=t
    elif s is not None:
        ev.append({"onset":str(dates[s].date()),"end":str(dates[t-1].date())});s=None
print(sea.sum(),ev)
os.makedirs("output",exist_ok=True)
xr.Dataset({"mhw":(("time","lat","lon"),m.astype(np.uint8))},coords={"time":tg.time.values,"lat":tg.latitude.values,"lon":tg.longitude.values}).to_netcdf("output/mhw_mask.nc")
json.dump({"region":{"lat_min":54.17,"lat_max":55.37,"lon_min":13.25,"lon_max":14.45},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2014-06-01","end":"2014-08-31"},"events":ev,"complete":True,"caveats":""},open("output/report.json","w"))