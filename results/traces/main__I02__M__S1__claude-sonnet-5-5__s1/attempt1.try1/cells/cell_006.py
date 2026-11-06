import os,json,xarray as xr,numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
R='/data/icsa2027_data_20261101T090944Z/s1z/sst_%s.nc'
d=xr.open_dataset(R%'20040601',engine='h5netcdf')
lat=d.latitude.values;lon=d.longitude.values
li=np.where((lat>=54.17-1e-4)&(lat<=55.37+1e-4))[0];lo=np.where((lon>=13.25-1e-4)&(lon<=14.45+1e-4))[0]
def ld(t):
    with xr.open_dataset(R%t.strftime('%Y%m%d'),engine='h5netcdf') as x:
        return x.analysed_sst.values[0,li[0]:li[-1]+1,lo[0]:lo[-1]+1].astype('float64')
bd=pd.date_range('1991-12-27','2003-01-05');td=pd.date_range('2004-06-01','2004-08-31')
with ThreadPoolExecutor(16) as ex:
    B=np.stack(list(ex.map(ld,bd)));T=np.stack(list(ex.map(ld,td)))
def doy(ts): return np.array([pd.Timestamp(2000,t.month,t.day).dayofyear for t in ts])
bdoy=doy(bd)
sea=np.isfinite(T).all(0);print(sea.sum())
core=[i for i,t in enumerate(bd) if 1992<=t.year<=2002]
thr=np.full((366,)+sea.shape,np.nan)
for dd in range(1,367):
    if dd==60: continue
    idx=set()
    for i in core:
        if bdoy[i]==dd: idx.update(range(i-5,i+6))
    idx=sorted(j for j in idx if 0<=j<len(bd))
    thr[dd-1][sea]=np.nanquantile(B[idx][:,sea],0.9,axis=0,method='hazen')
thr[59]=(thr[58]+thr[60])/2
thr=np.mean([np.roll(thr,-k,axis=0) for k in range(-15,16)],axis=0)
tdoy=doy(td)
hot=(T>=thr[tdoy-1])&sea
m=np.zeros(hot.shape,bool)
n=len(td)
for i in range(60):
  for j in range(60):
    if not sea[i,j]: continue
    x=hot[:,i,j];o=np.zeros(n,bool);k=0
    while k<n:
        if x[k]:
            e=k
            while e<n and x[e]: e+=1
            if e-k>=5:o[k:e]=True
            k=e
        else:k+=1
    k=0
    while k<n:
        if not o[k]:
            e=k
            while e<n and not o[e]: e+=1
            if k>0 and e<n and e-k<=2: o[k:e]=True
            k=e
        else:k+=1
    m[:,i,j]=o
act=m.any((1,2))
ev=[];s=None
for i,a in enumerate(act):
    if a and s is None:s=i
    if (not a) and s is not None: ev.append((s,i-1));s=None
if s is not None: ev.append((s,n-1))
evs=[{"onset":str(td[a].date()),"end":str(td[b].date())} for a,b in ev];print(evs)
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),m.astype('uint8'))},coords={'time':td,'lat':lat[li],'lon':lon[lo]}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":54.17,"lat_max":55.37,"lon_min":13.25,"lon_max":14.45},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2004-06-01","end":"2004-08-31"},"events":evs,"complete":True,"caveats":""},open('output/report.json','w'))