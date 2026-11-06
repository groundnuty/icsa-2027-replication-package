import json,os,xarray as xr,numpy as np,pandas as pd
b=xr.open_dataarray("/tmp/b.nc");t=xr.open_dataarray("/tmp/t.nc")
B=b.values.astype(np.float64);T=t.values.astype(np.float64)
bt=pd.DatetimeIndex(b.time.values)
def doy(i): 
    return np.array([ (pd.Timestamp(2000,x.month,x.day).dayofyear) for x in i])
bd=doy(bt)
sea=np.isfinite(T).all(0)
base=np.where((bt>=pd.Timestamp("1992-01-01"))&(bt<=pd.Timestamp("2002-12-31")))[0]
thr=np.full((366,)+sea.shape,np.nan)
for d in range(1,367):
    if d==60: continue
    idx=np.concatenate([np.arange(i-5,i+6) for i in base if bd[i]==d])
    P=B[idx][:,sea]
    thr[d-1][sea]=np.nanquantile(P,0.9,axis=0,method="hazen")
def fin(a):
    a[59]=(a[58]+a[60])/2
    return np.mean([a[(np.arange(366)+s)%366] for s in range(-15,16)],axis=0)
thr=fin(thr)
td=doy(pd.DatetimeIndex(t.time.values))
hot=(T>=thr[td-1])&sea
nt=len(td);M=np.zeros(hot.shape,bool)
for i in range(hot.shape[1]):
  for j in range(hot.shape[2]):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];s=None
    for k in range(nt+1):
        if k<nt and h[k]: 
            if s is None:s=k
        elif s is not None:
            if k-s>=5:runs.append([s,k-1])
            s=None
    m=[]
    for r in runs:
        if m and r[0]-m[-1][1]-1<=2:m[-1][1]=r[1]
        else:m.append(r)
    for a,e in m:M[a:e+1,i,j]=True
act=M.any((1,2));ev=[];s=None
dates=pd.DatetimeIndex(t.time.values)
for k in range(nt+1):
    if k<nt and act[k]:
        if s is None:s=k
    elif s is not None:
        ev.append({"onset":str(dates[s].date()),"end":str(dates[k-1].date())});s=None
print(sea.sum(),ev)
os.makedirs("output",exist_ok=True)
xr.Dataset({"mhw":(("time","lat","lon"),M.astype(np.uint8))},coords={"time":t.time.values,"lat":t.latitude.values,"lon":t.longitude.values}).to_netcdf("output/mhw_mask.nc")
json.dump({"region":{"lat_min":58.69,"lat_max":59.89,"lon_min":18.69,"lon_max":19.89},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2010-06-01","end":"2010-08-31"},"events":ev,"complete":True,"caveats":""},open("output/report.json","w"))