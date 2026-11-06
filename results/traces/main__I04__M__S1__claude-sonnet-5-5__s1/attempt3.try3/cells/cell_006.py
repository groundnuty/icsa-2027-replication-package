import xarray as xr, numpy as np, datetime as dt, json, os
from concurrent.futures import ThreadPoolExecutor
p='/data/icsa2027_data_20261101T090944Z/s1z/'
d=xr.open_dataset(p+'sst_20200601.nc',engine='h5netcdf')
lat=d.latitude.values;lon=d.longitude.values
li=np.where((lat>=54.39-1e-4)&(lat<=55.59+1e-4))[0];lj=np.where((lon>=18.25-1e-4)&(lon<=19.45+1e-4))[0]
def rd(x):
    a=xr.open_dataset(p+f"sst_{x:%Y%m%d}.nc",engine='h5netcdf')
    v=a.analysed_sst.isel(time=0,latitude=slice(li[0],li[-1]+1),longitude=slice(lj[0],lj[-1]+1)).values.astype('float64');a.close();return v
def load(a,b):
    ds=[a+dt.timedelta(i) for i in range((b-a).days+1)]
    with ThreadPoolExecutor(16) as ex: return ds,np.array(list(ex.map(rd,ds)))
bd,B=load(dt.date(1991,12,27),dt.date(2003,1,5))
td,T=load(dt.date(2020,6,1),dt.date(2020,8,31))
def doy(x):
    return (dt.date(2000,x.month,x.day)-dt.date(2000,1,1)).days+1
idx={x:i for i,x in enumerate(bd)}
thr=np.full((366,60,60),np.nan);clim=thr.copy()
for k in range(1,367):
    if k==60: continue
    ii=[]
    for x in bd:
        if dt.date(1992,1,1)<=x<=dt.date(2002,12,31) and doy(x)==k:
            ii+= [idx[x]+o for o in range(-5,6)]
    pool=B[ii]
    thr[k-1]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[k-1]=np.nanmean(pool,axis=0)
for a in (thr,clim): a[59]=(a[58]+a[60])/2
thr=np.mean([np.roll(thr,-s,axis=0) for s in range(-15,16)],axis=0)
sea=np.isfinite(T).all(0)
dT=np.array([doy(x)-1 for x in td])
hot=(T>=thr[dT])&sea[None]
M=np.zeros(hot.shape,bool)
for i in range(60):
    for j in range(60):
        v=hot[:,i,j]
        if not v.any(): continue
        segs=[];s=None
        for t in range(93):
            if t<92 and v[t]:
                if s is None:s=t
            elif s is not None:
                if t-s>=5:segs.append([s,t-1])
                s=None
        m=[]
        for sg in segs:
            if m and sg[0]-m[-1][1]-1<=2: m[-1][1]=sg[1]
            else: m.append(sg)
        for a,b in m: M[a:b+1,i,j]=True
act=M.any((1,2))
ev=[];s=None
for t in range(93):
    if t<92 and act[t]:
        if s is None:s=t
    elif s is not None: ev.append({"onset":str(td[s]),"end":str(td[t-1])});s=None
print(sea.sum(),ev,M.sum())
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),M.astype('uint8'))},coords={'time':np.array(td,dtype='datetime64[ns]'),'lat':lat[li],'lon':lon[lj]}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":54.39,"lat_max":55.59,"lon_min":18.25,"lon_max":19.45},
"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
"target_analysed":{"start":"2020-06-01","end":"2020-08-31"},
"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))