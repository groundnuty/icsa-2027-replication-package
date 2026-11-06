import xarray as xr,numpy as np,pandas as pd,json,os
p="/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds=xr.open_dataset(p,engine="h5netcdf")
la=ds.latitude.values;lo=ds.longitude.values
li=np.where((la>=54.13-1e-4)&(la<=55.33+1e-4))[0];oi=np.where((lo>=14.67-1e-4)&(lo<=15.87+1e-4))[0]
sub=ds.analysed_sst.isel(latitude=slice(li[0],li[-1]+1),longitude=slice(oi[0],oi[-1]+1))
s=sub.sel(time=slice("1991-12-27","2003-01-05")).load()
tg=sub.sel(time=slice("2008-06-01","2008-08-31")).load()
T=pd.DatetimeIndex(s.time.values);X=s.values.astype(np.float64)
def doy(ix):
    m=ix.month.values;d=ix.day.values
    cum=np.array([0,31,60,91,121,152,182,213,244,274,305,335])
    return cum[m-1]+d
bd=pd.date_range("1992-01-01","2002-12-31");bdoy=doy(bd)
pos={t:i for i,t in enumerate(T)}
thr=np.full((366,60,60),np.nan)
for d in range(1,367):
    if d==60: continue
    idx=set()
    for b in bd[bdoy==d]:
        for k in range(-5,6):
            idx.add(pos[b+pd.Timedelta(days=k)])
    thr[d-1]=np.nanquantile(X[sorted(idx)],0.9,axis=0,method="hazen")
thr[59]=(thr[58]+thr[60])/2
thr=np.mean([np.roll(thr,-k,axis=0) for k in range(-15,16)],axis=0)
tt=pd.DatetimeIndex(tg.time.values);Y=tg.values.astype(np.float64)
sea=np.isfinite(Y).all(0)
hot=(Y>=thr[doy(tt)-1])&sea
n=len(tt);mh=np.zeros_like(hot)
for i in range(60):
  for j in range(60):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];k=0
    while k<n:
        if h[k]:
            e=k
            while e+1<n and h[e+1]:e+=1
            if e-k+1>=5:runs.append([k,e])
            k=e+1
        else:k+=1
    mg=[]
    for r in runs:
        if mg and r[0]-mg[-1][1]-1<=2: mg[-1][1]=r[1]
        else: mg.append(r)
    for a,b in mg: mh[a:b+1,i,j]=True
act=mh.any((1,2));ev=[];k=0
while k<n:
    if act[k]:
        e=k
        while e+1<n and act[e+1]:e+=1
        ev.append({"onset":str(tt[k].date()),"end":str(tt[e].date())});k=e+1
    else:k+=1
print(sea.sum(),ev)
os.makedirs("output",exist_ok=True)
xr.Dataset({"mhw":(("time","lat","lon"),mh.astype(np.uint8))},coords={"time":tg.time.values,"lat":tg.latitude.values,"lon":tg.longitude.values}).to_netcdf("output/mhw_mask.nc")
json.dump({"region":{"lat_min":54.13,"lat_max":55.33,"lon_min":14.67,"lon_max":15.87},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2008-06-01","end":"2008-08-31"},"events":ev,"complete":True,"caveats":""},open("output/report.json","w"))