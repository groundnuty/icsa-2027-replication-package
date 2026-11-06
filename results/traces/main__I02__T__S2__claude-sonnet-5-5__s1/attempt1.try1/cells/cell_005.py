
import xarray as xr,numpy as np,pandas as pd,json,os
b=xr.open_dataarray("/tmp/b.nc");t=xr.open_dataarray("/tmp/t.nc")
B=b.values.astype(np.float64);T=t.values.astype(np.float64)
bt=pd.DatetimeIndex(b.time.values)
def doy(i): 
    return np.array([ (pd.Timestamp(2000,m,d).dayofyear) for m,d in zip(i.month,i.day)])
bd=doy(bt)
inb=(bt>="1992-01-01")&(bt<="2002-12-31")
sea=np.isfinite(T).all(0)
ny,nx=sea.shape
thr=np.full((366,ny,nx),np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60: continue
    idx=np.where(inb&(bd==d))[0]
    s=set()
    for i in idx: s.update(range(max(0,i-5),min(len(bt),i+6)))
    pool=B[sorted(s)]
    thr[d-1]=np.nanquantile(pool,0.9,axis=0,method="hazen")
    clim[d-1]=np.nanmean(pool,axis=0)
for a in(thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,k,axis=0) for k in range(-15,16))/31
thr=sm(thr)
td=doy(pd.DatetimeIndex(t.time.values))
hot=(T>=thr[td-1])&sea
nt=len(td);mhw=np.zeros(hot.shape,bool)
for y in range(ny):
  for x in range(nx):
    if not sea[y,x]: continue
    h=hot[:,y,x];runs=[];i=0
    while i<nt:
        if h[i]:
            j=i
            while j<nt and h[j]:j+=1
            if j-i>=5: runs.append([i,j])
            i=j
        else:i+=1
    m=[]
    for r in runs:
        if m and r[0]-m[-1][1]<=2: m[-1][1]=r[1]
        else:m.append(r)
    for a,c in m: mhw[a:c,y,x]=True
act=mhw.any((1,2))
dates=pd.DatetimeIndex(t.time.values);ev=[];i=0
while i<nt:
    if act[i]:
        j=i
        while j+1<nt and act[j+1]:j+=1
        ev.append({"onset":str(dates[i].date()),"end":str(dates[j].date())});i=j+1
    else:i+=1
print(ev,sea.sum())
os.makedirs("output",exist_ok=True)
o=xr.Dataset({"mhw":(("time","lat","lon"),mhw.astype(np.uint8))},coords={"time":t.time.values,"lat":t.latitude.values,"lon":t.longitude.values})
o.to_netcdf("output/mhw_mask.nc")
json.dump({"region":{"lat_min":54.17,"lat_max":55.37,"lon_min":13.25,"lon_max":14.45},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
"target_analysed":{"start":"2004-06-01","end":"2004-08-31"},
"events":ev,"complete":True,"caveats":""},open("output/report.json","w"))
