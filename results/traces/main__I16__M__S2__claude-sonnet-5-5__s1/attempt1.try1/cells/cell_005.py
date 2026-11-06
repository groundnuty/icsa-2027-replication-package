import xarray as xr,numpy as np,pandas as pd,os,json
p="/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
d=xr.open_dataset(p,engine="h5netcdf")
la=d.latitude.values;lo=d.longitude.values
i=np.where((la>=56.63-1e-4)&(la<=57.83+1e-4))[0];j=np.where((lo>=20.23-1e-4)&(lo<=21.43+1e-4))[0]
sub=d.analysed_sst.isel(latitude=slice(i[0],i[-1]+1),longitude=slice(j[0],j[-1]+1))
t=d.time.values
b0=np.searchsorted(t,np.datetime64("1991-12-27"));b1=np.searchsorted(t,np.datetime64("2003-01-05"),side="right")
base=sub.isel(time=slice(b0,b1)).values.astype("float64")
tg=sub.sel(time=slice("2008-06-01","2008-08-31")).load()
tt=pd.DatetimeIndex(t[b0:b1])
cum=np.cumsum([0,31,29,31,30,31,30,31,31,30,31,30])
doy=cum[tt.month-1]+tt.day
inb=(tt>="1992-01-01")&(tt<="2002-12-31")
ny,nx=60,60
thr=np.full((366,ny,nx),np.nan);clm=thr.copy()
for dd in range(1,367):
    if dd==60: continue
    c=np.where(inb&(doy==dd))[0]
    idx=np.unique(np.concatenate([np.arange(k-5,k+6) for k in c]))
    pool=base[idx]
    thr[dd-1]=np.nanquantile(pool,0.9,axis=0,method="hazen")
thr[59]=(thr[58]+thr[60])/2
thr=sum(np.roll(thr,-k,axis=0) for k in range(-15,16))/31
v=tg.values.astype("float64")
sea=np.isfinite(v).all(0)
tl=pd.DatetimeIndex(tg.time.values)
tdoy=cum[tl.month-1]+tl.day
hot=(v>=thr[tdoy-1])&sea[None]
core=np.zeros_like(hot);m=None
for a in range(ny):
    for b in range(nx):
        x=hot[:,a,b];n=len(x);k=0
        while k<n:
            if x[k]:
                e=k
                while e<n and x[e]: e+=1
                if e-k>=5: core[k:e,a,b]=True
                k=e
            else:k+=1
m=core.copy()
for a in range(ny):
    for b in range(nx):
        idx=np.where(core[:,a,b])[0]
        for p0,p1 in zip(idx[:-1],idx[1:]):
            if p1-p0-1 in(1,2): m[p0:p1,a,b]=True
act=m.any((1,2))
ev=[];k=0
while k<len(act):
    if act[k]:
        e=k
        while e+1<len(act) and act[e+1]: e+=1
        ev.append({"onset":str(tl[k].date()),"end":str(tl[e].date())});k=e+1
    else:k+=1
print(sea.sum(),ev)
os.makedirs("output",exist_ok=True)
xr.Dataset({"mhw":(("time","lat","lon"),m.astype("uint8"))},coords={"time":tg.time.values,"lat":la[i],"lon":lo[j]}).to_netcdf("output/mhw_mask.nc")
json.dump({"region":{"lat_min":56.63,"lat_max":57.83,"lon_min":20.23,"lon_max":21.43},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2008-06-01","end":"2008-08-31"},"events":ev,"complete":True,"caveats":""},open("output/report.json","w"))