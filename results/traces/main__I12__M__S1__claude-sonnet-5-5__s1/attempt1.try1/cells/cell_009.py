import os,numpy as np,pandas as pd,xarray as xr,json
p='/data/icsa2027_data_20261101T090944Z/s1z/'
d=xr.open_dataset(p+'sst_20090601.nc',engine='h5netcdf')
lat=d.latitude.values;lon=d.longitude.values
ii=np.where((lat>=56.09-1e-4)&(lat<=57.29+1e-4))[0];jj=np.where((lon>=10.55-1e-4)&(lon<=11.75+1e-4))[0]
B=np.load('/tmp/B.npy');T=np.load('/tmp/T.npy')
bd=pd.date_range('1991-12-27','2003-01-05')
td=pd.date_range('2009-06-01','2009-08-31')
print(np.nanmin(B),np.nanmax(B),np.nanmin(T),np.nanmax(T))
doy=lambda ds:np.array([ (pd.Timestamp(2000,x.month,x.day).dayofyear) for x in ds])
bdoy=doy(bd)
inb=(bd>='1992-01-01')&(bd<='2002-12-31')
idx=np.arange(len(bd))
thr=np.full((366,60,60),np.nan);clim=thr.copy()
for dd in range(1,367):
    if dd==60: continue
    c=idx[inb&(bdoy==dd)]
    s=set()
    for k in c: s.update(range(k-5,k+6))
    s=sorted(x for x in s if 0<=x<len(bd))
    P=B[s]
    thr[dd-1]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[dd-1]=np.nanmean(P,axis=0)
for a in(thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,-k,axis=0) for k in range(-15,16))/31
thr=sm(thr)
sea=np.isfinite(T).all(0)
tdoy=doy(td)
hot=(T>=thr[tdoy-1])&sea
n=len(td);mhw=np.zeros_like(hot)
def runs(v):
    r=[];i=0
    while i<len(v):
        if v[i]:
            j=i
            while j<len(v) and v[j]:j+=1
            r.append((i,j));i=j
        else:i+=1
    return r
for a in range(60):
  for b in range(60):
    if not sea[a,b]:continue
    r=[x for x in runs(hot[:,a,b]) if x[1]-x[0]>=5]
    m=np.zeros(n,bool)
    for s,e in r:m[s:e]=1
    for (s1,e1),(s2,e2) in zip(r,r[1:]):
        if s2-e1<=2:m[e1:s2]=1
    mhw[:,a,b]=m
act=mhw.any((1,2))
ev=[(td[s],td[e-1]) for s,e in runs(act)]
print(sea.sum(),ev)
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':td,'lat':lat[ii],'lon':lon[jj]}).to_netcdf('output/mhw_mask.nc')
f=lambda t:f"{t:%Y-%m-%d}"
json.dump({"region":{"lat_min":56.09,"lat_max":57.29,"lon_min":10.55,"lon_max":11.75},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
"target_analysed":{"start":"2009-06-01","end":"2009-08-31"},
"events":[{"onset":f(a),"end":f(b)} for a,b in ev],"complete":True,
"caveats":"Baseline windows also used 1991-12-27..31 and 2003-01-01..05 as specified."},open('output/report.json','w'))