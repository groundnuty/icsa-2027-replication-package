import xarray as xr,numpy as np,pandas as pd,json,os
p="/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
d=xr.open_dataset(p,engine="h5netcdf")
la=d.latitude.values;lo=d.longitude.values
li=np.where((la>=59.93-1e-4)&(la<=61.13+1e-4))[0];oi=np.where((lo>=18.69-1e-4)&(lo<=19.89+1e-4))[0]
s=d.analysed_sst.isel(latitude=slice(li[0],li[-1]+1),longitude=slice(oi[0],oi[-1]+1))
tt=pd.DatetimeIndex(d.time.values)
bi=np.where((tt>="1991-12-27")&(tt<="2003-01-05"))[0]
B=s.isel(time=slice(bi[0],bi[-1]+1)).values.astype("float64")
ti=np.where((tt>="2009-06-01")&(tt<="2009-08-31"))[0]
T=s.isel(time=slice(ti[0],ti[-1]+1)).values.astype("float64")
bt=tt[bi]
def mdoy(x):
    dd=x.dayofyear.values.copy()
    leap=x.is_leap_year; return np.where((~leap)&(x.month>2),dd+1,dd)
bd=mdoy(bt)
inb=(bt>="1992-01-01")&(bt<="2002-12-31")
thr=np.full((366,60,60),np.nan)
for k in range(1,367):
    if k==60: continue
    idx=np.where(inb&(bd==k))[0]
    ii=np.unique(np.concatenate([np.arange(i-5,i+6) for i in idx]))
    ii=ii[(ii>=0)&(ii<len(bt))]
    pool=B[ii]
    thr[k-1]=np.nanquantile(pool.reshape(len(ii),-1),0.9,axis=0,method="hazen").reshape(60,60)
def fix(a):
    a[59]=(a[58]+a[60])/2
    ext=np.concatenate([a[-15:],a,a[:15]])
    c=np.cumsum(np.concatenate([np.zeros((1,)+a.shape[1:]),ext]),axis=0)
    return (c[31:]-c[:-31])/31
thr=fix(thr)
sea=np.isfinite(T).all(0)
td=mdoy(tt[ti])
hot=(T>=thr[td-1])&sea
n=len(td);mhw=np.zeros(hot.shape,bool)
for y in range(60):
  for x in range(60):
    if not sea[y,x]: continue
    h=hot[:,y,x];runs=[];i=0
    while i<n:
        if h[i]:
            j=i
            while j<n and h[j]: j+=1
            if j-i>=5: runs.append([i,j])
            i=j
        else: i+=1
    m=[]
    for r in runs:
        if m and r[0]-m[-1][1]<=2: m[-1][1]=r[1]
        else: m.append(r)
    for a,b in m: mhw[a:b,y,x]=1
act=mhw.any((1,2));ev=[];i=0
D=tt[ti]
while i<n:
    if act[i]:
        j=i
        while j+1<n and act[j+1]: j+=1
        ev.append({"onset":str(D[i].date()),"end":str(D[j].date())});i=j+1
    else:i+=1
print(sea.sum(),ev)
os.makedirs("output",exist_ok=True)
xr.Dataset({"mhw":(("time","lat","lon"),mhw.astype("uint8"))},coords={"time":D,"lat":la[li],"lon":lo[oi]}).to_netcdf("output/mhw_mask.nc")
json.dump({"region":{"lat_min":59.93,"lat_max":61.13,"lon_min":18.69,"lon_max":19.89},"baseline_analysed":{"start":"1991-12-27","end":"2003-01-05"},"target_analysed":{"start":"2009-06-01","end":"2009-08-31"},"events":ev,"complete":True,"caveats":""},open("output/report.json","w"))