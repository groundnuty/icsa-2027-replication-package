import xarray as xr,numpy as np,pandas as pd,os,json
d=xr.open_dataset('/work/s.nc',engine='h5netcdf')
lat=slice(54.45-1e-4,55.65+1e-4);lon=slice(16.05-1e-4,17.25+1e-4)
a=d.analysed_sst.sel(latitude=lat,longitude=lon)
full=a.sel(time=slice('1991-12-27','2003-01-05')).load()
tg=a.sel(time=slice('2021-06-01','2021-08-31')).load()
T=pd.DatetimeIndex(full.time.values);X=full.values.astype('float64')
def doy(ix):
    return np.where(ix.is_leap_year,ix.dayofyear,ix.dayofyear+(ix.month>2))
dd=doy(T)
base=np.where((T>='1992-01-01')&(T<='2002-12-31'))[0]
ny,nx=X.shape[1:]
thr=np.full((366,ny,nx),np.nan)
for k in range(1,367):
    if k==60: continue
    idx=set()
    for i in base[dd[base]==k]:
        for o in range(-5,6):
            if 0<=i+o<len(T): idx.add(i+o)
    P=X[sorted(idx)]
    thr[k-1]=np.nanquantile(P,0.9,axis=0,method='hazen')
thr[59]=(thr[58]+thr[60])/2
thr=np.mean([np.roll(thr,-s,axis=0) for s in range(-15,16)],axis=0)
Y=tg.values.astype('float64');tt=pd.DatetimeIndex(tg.time.values)
sea=np.isfinite(Y).all(0)
hot=(Y>=thr[doy(tt)-1])&sea
nt=len(tt);m=np.zeros_like(hot)
for i in range(ny):
  for j in range(nx):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];s=None
    for n in range(nt+1):
        if n<nt and h[n]:
            if s is None:s=n
        elif s is not None:
            if n-s>=5: runs.append([s,n-1])
            s=None
    mer=[]
    for r_ in runs:
        if mer and r_[0]-mer[-1][1]-1<=2: mer[-1][1]=r_[1]
        else: mer.append(r_)
    for s,e in mer: m[s:e+1,i,j]=True
act=m.any((1,2));ev=[];s=None
for n in range(nt+1):
    if n<nt and act[n]:
        if s is None:s=n
    elif s is not None: ev.append({"onset":str(tt[s].date()),"end":str(tt[n-1].date())});s=None
print(sea.sum(),ev,len(base))
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),m.astype('uint8'))},coords={'time':tg.time.values,'lat':tg.latitude.values,'lon':tg.longitude.values}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":54.45,"lat_max":55.65,"lon_min":16.05,"lon_max":17.25},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2021-06-01","end":"2021-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))