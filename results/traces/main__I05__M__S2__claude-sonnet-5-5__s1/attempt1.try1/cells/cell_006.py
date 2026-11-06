import xarray as xr,numpy as np,pandas as pd,os,json
b=xr.open_dataarray("/tmp/b.nc");t=xr.open_dataarray("/tmp/t.nc")
B=b.values.astype(np.float64);T=t.values.astype(np.float64)
bt=pd.DatetimeIndex(b.time.values)
def doy(i): 
    return np.array([ (pd.Timestamp(2000,x.month,x.day).dayofyear) for x in i])
idx=np.arange(len(bt))
bd=doy(bt)
inbase=(bt>="1992-01-01")&(bt<="2002-12-31")
ny=B.shape[1:]
thr=np.full((366,)+ny,np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60: continue
    c=idx[inbase&(bd==d)]
    ii=np.concatenate([c+k for k in range(-5,6)])
    ii=ii[(ii>=0)&(ii<len(bt))]
    pool=B[ii]
    thr[d-1]=np.nanquantile(pool,0.9,axis=0,method="hazen")
    clim[d-1]=np.nanmean(pool,axis=0)
for a in (thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,-k,axis=0) for k in range(-15,16))/31
thr=sm(thr)
td=pd.DatetimeIndex(t.time.values);dd=doy(td)
sea=np.isfinite(T).all(0)
hot=(T>=thr[dd-1])&sea
mhw=np.zeros_like(hot)
nt=len(td)
for i in range(ny[0]):
  for j in range(ny[1]):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];k=0
    while k<nt:
        if h[k]:
            s=k
            while k<nt and h[k]:k+=1
            if k-s>=5:runs.append([s,k-1])
        else:k+=1
    m=[]
    for r in runs:
        if m and r[0]-m[-1][1]-1<=2:m[-1][1]=r[1]
        else:m.append(r)
    for s,e in m:mhw[s:e+1,i,j]=True
act=mhw.any((1,2))
ev=[];k=0
while k<nt:
    if act[k]:
        s=k
        while k<nt and act[k]:k+=1
        ev.append({"onset":str(td[s].date()),"end":str(td[k-1].date())})
    else:k+=1
print(sea.sum(),ev)
os.makedirs("output",exist_ok=True)
o=xr.Dataset({"mhw":(("time","lat","lon"),mhw.astype(np.uint8))},coords={"time":t.time.values,"lat":t.latitude.values,"lon":t.longitude.values})
o.to_netcdf("output/mhw_mask.nc")
json.dump({"region":{"lat_min":54.39,"lat_max":55.59,"lon_min":18.25,"lon_max":19.45},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
"target_analysed":{"start":"2021-06-01","end":"2021-08-31"},
"events":ev,"complete":True,"caveats":""},open("output/report.json","w"))