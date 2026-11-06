import numpy as np,pandas as pd,json,xarray as xr,os
from scipy.ndimage import label
B=np.load('/tmp/B.npy');T=np.load('/tmp/T.npy')
bd=pd.date_range('1991-12-27','2003-01-05');td=pd.date_range('2017-06-01','2017-08-31')
doy=lambda idx:np.array([pd.Timestamp(2000,t.month,t.day).dayofyear for t in idx])
bdoy=doy(bd)
core=np.where((bd>='1992-01-01')&(bd<='2002-12-31'))[0]
thr=np.full((366,60,60),np.nan);clim=thr.copy()
for dd in range(1,367):
    if dd==60: continue
    idx=set()
    for i in core:
        if bdoy[i]==dd: idx.update(range(i-5,i+6))
    P=B[sorted(idx)]
    thr[dd-1]=np.nanquantile(P,0.9,axis=0,method='hazen');clim[dd-1]=np.nanmean(P,axis=0)
for a in (thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,-k,axis=0) for k in range(-15,16))/31
thr=sm(thr)
sea=np.isfinite(T).all(0)
tdoy=doy(td)
hot=(T>=thr[tdoy-1])&sea
mhw=np.zeros(hot.shape,bool)
nt=len(td)
for i in range(60):
  for j in range(60):
    if not sea[i,j]: continue
    h=hot[:,i,j];lab,n=label(h)
    runs=[(np.where(lab==k)[0][0],np.where(lab==k)[0][-1]) for k in range(1,n+1)]
    runs=[r for r in runs if r[1]-r[0]+1>=5]
    m=np.zeros(nt,bool);prev=None
    for s,e in runs:
        m[s:e+1]=True
        if prev is not None and s-prev-1<=2: m[prev:s]=True
        prev=e
    mhw[:,i,j]=m
act=mhw.any((1,2));lab,n=label(act)
ev=[{"onset":f"{td[np.where(lab==k)[0][0]]:%Y-%m-%d}","end":f"{td[np.where(lab==k)[0][-1]]:%Y-%m-%d}"} for k in range(1,n+1)]
print(sea.sum(),ev)
os.makedirs('output',exist_ok=True)
ds=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':td,'lat':np.load('/tmp/B.npy',mmap_mode='r')[0,:,0]*0+xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20170601.nc',engine='h5netcdf').latitude.values[(lambda la:np.where((la>=62.2499)&(la<=63.4501))[0])(xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20170601.nc',engine='h5netcdf').latitude.values)],'lon':xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20170601.nc',engine='h5netcdf').longitude.values[(lambda lo:np.where((lo>=18.7299)&(lo<=19.9301))[0])(xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20170601.nc',engine='h5netcdf').longitude.values)]})
print(ds.lat.values[[0,-1]],ds.lon.values[[0,-1]],ds.mhw.shape)
ds.to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":62.25,"lat_max":63.45,"lon_min":18.73,"lon_max":19.93},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2017-06-01","end":"2017-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))