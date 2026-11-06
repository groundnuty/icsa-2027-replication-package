import xarray as xr,numpy as np,pandas as pd,os,json
p="/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds=xr.open_dataset(p,engine="h5netcdf");t=ds.time.values
la=ds.latitude.values;lo=ds.longitude.values
li=np.where((la>=64.51-1e-4)&(la<=65.71+1e-4))[0];oi=np.where((lo>=21.97-1e-4)&(lo<=23.17+1e-4))[0]
sub=ds.analysed_sst.isel(latitude=slice(li[0],li[-1]+1),longitude=slice(oi[0],oi[-1]+1))
tt=pd.DatetimeIndex(t)
b0=np.searchsorted(tt,pd.Timestamp("1991-12-27"));b1=np.searchsorted(tt,pd.Timestamp("2003-01-05"),side="right")
base=sub.isel(time=slice(b0,b1)).values.astype("float64");bt=tt[b0:b1]
tg=sub.sel(time=slice("2019-06-01","2019-08-31")).load()
def doy(d):
    d=pd.DatetimeIndex(d);return np.array([(pd.Timestamp(2000,m,dd).dayofyear) for m,dd in zip(d.month,d.day)])
D=doy(bt)
isb=(bt>=pd.Timestamp("1992-01-01"))&(bt<=pd.Timestamp("2002-12-31"))
ny=base.shape[1:]
thr=np.full((366,)+ny,np.nan)
for d in range(1,367):
    if d==60: continue
    ii=set()
    for c in np.where(isb&(D==d))[0]:
        for o in range(-5,6):
            j=c+o
            if 0<=j<len(bt): ii.add(j)
    thr[d-1]=np.nanquantile(base[sorted(ii)],0.9,axis=0,method="hazen")
thr[59]=(thr[58]+thr[60])/2
thr=sum(np.roll(thr,-k,axis=0) for k in range(-15,16))/31
tv=tg.values.astype("float64");sea=np.isfinite(tv).all(0)
Dt=doy(tg.time.values)
hot=(tv>=thr[Dt-1])&sea
T=hot.shape[0];mh=np.zeros_like(hot)
for i in range(hot.shape[1]):
  for j in range(hot.shape[2]):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];k=0
    while k<T:
        if h[k]:
            e=k
            while e<T and h[e]:e+=1
            if e-k>=5:runs.append([k,e])
            k=e
        else:k+=1
    m=[]
    for r in runs:
        if m and r[0]-m[-1][1]<=2:m[-1][1]=r[1]
        else:m.append(r)
    for a,b in m:mh[a:b,i,j]=True
act=mh.any((1,2));ev=[];k=0
while k<T:
    if act[k]:
        e=k
        while e<T and act[e]:e+=1
        ev.append({"onset":str(tg.time.values[k])[:10],"end":str(tg.time.values[e-1])[:10]});k=e
    else:k+=1
print(sea.sum(),ev)
os.makedirs("output",exist_ok=True)
xr.Dataset({"mhw":(("time","lat","lon"),mh.astype("uint8"))},coords={"time":tg.time.values,"lat":la[li],"lon":lo[oi]}).to_netcdf("output/mhw_mask.nc")
json.dump({"region":{"lat_min":64.51,"lat_max":65.71,"lon_min":21.97,"lon_max":23.17},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2019-06-01","end":"2019-08-31"},"events":ev,"complete":True,"caveats":"Baseline windows used 1991-12-27..2003-01-05 as specified."},open("output/report.json","w"))