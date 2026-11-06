import fsspec, xarray as xr, numpy as np, pandas as pd, json, os
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
dates=pd.date_range('1991-12-27','2003-08-31')
def load(d):
    for t in range(4):
        try:
            with fs.open(f"{p}/sst_{d.strftime('%Y%m%d')}.nc",'rb') as f:
                x=xr.open_dataset(f,engine='h5netcdf')
                x=x.sel(latitude=slice(60.485,61.695),longitude=slice(17.245,18.455)).load()
            return x.analysed_sst.values[0],x.latitude.values,x.longitude.values
        except Exception as e: err=e
    raise err
with ThreadPoolExecutor(16) as ex: res=list(ex.map(load,dates))
# need 2003-01-01..05 included; dates run to 2003-08-31 OK
A=np.stack([r[0] for r in res]).astype('float64'); lat=res[0][1];lon=res[0][2]
print(A.shape,np.nanmin(A),np.nanmax(A),np.isnan(A).mean())
def doy(ix): return np.array([ (d.month-1)*0 for d in ix])
cum=np.array([0,31,60,91,121,152,182,213,244,274,305,335])  # leap-year offsets
DOY=np.array([cum[d.month-1]+d.day for d in dates])
tg=np.where((dates>='2003-06-01'))[0]
sea=np.isfinite(A[tg]).all(0)
print(sea.sum())
base=np.where((dates>='1992-01-01')&(dates<='2002-12-31'))[0]
thr=np.full((366,)+A.shape[1:],np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60: continue
    idx=set()
    for b in base:
        if DOY[b]==d: idx.update(range(b-5,b+6))
    idx=sorted(i for i in idx if 0<=i<len(dates))
    pool=A[idx][:,sea]
    t=np.full(A.shape[1:],np.nan);c=t.copy()
    t[sea]=np.nanquantile(pool,0.9,axis=0,method='hazen');c[sea]=np.nanmean(pool,0)
    thr[d-1]=t;clim[d-1]=c
thr[59]=(thr[58]+thr[60])/2
def sm(x):
    return np.mean([np.roll(x,-k,axis=0) for k in range(-15,16)],axis=0)
thr=sm(thr)
T=A[tg]; D=DOY[tg]
hot=(T>=thr[D-1])&sea
nt=len(tg);mhw=np.zeros_like(hot)
for i in range(hot.shape[1]):
  for j in range(hot.shape[2]):
    h=hot[:,i,j]
    if not h.any(): continue
    runs=[];s=None
    for k in range(nt+1):
        v=h[k] if k<nt else False
        if v and s is None:s=k
        if not v and s is not None:
            if k-s>=5:runs.append([s,k-1])
            s=None
    merged=[]
    for r in runs:
        if merged and r[0]-merged[-1][1]-1<=2: merged[-1][1]=r[1]
        else: merged.append(r)
    for a,b in merged: mhw[a:b+1,i,j]=True
act=mhw.any((1,2));td=dates[tg]
ev=[];s=None
for k in range(nt+1):
    v=act[k] if k<nt else False
    if v and s is None:s=k
    if not v and s is not None: ev.append({"onset":str(td[s].date()),"end":str(td[k-1].date())});s=None
print(ev)
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':td,'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":60.49,"lat_max":61.69,"lon_min":17.25,"lon_max":18.45},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
"target_analysed":{"start":"2003-06-01","end":"2003-08-31"},
"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))