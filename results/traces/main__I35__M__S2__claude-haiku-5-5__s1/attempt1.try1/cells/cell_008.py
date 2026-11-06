
import xarray as xr, numpy as np, pandas as pd, os, json
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(p,engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
li=np.where((lat>=59.93-1e-6)&(lat<=61.13+1e-6))[0]; lj=np.where((lon>=18.69-1e-6)&(lon<=19.89+1e-6))[0]
sub=ds.analysed_sst.isel(latitude=li,longitude=lj)
b=sub.sel(time=slice('1991-12-27','2003-01-05')).load()
t=sub.sel(time=slice('2009-06-01','2009-08-31')).load()
def doy_of(dates):
    d=pd.DatetimeIndex(dates)
    m2000=pd.DatetimeIndex(pd.to_datetime(pd.DataFrame({'year':2000,'month':d.month,'day':d.day})))
    return np.asarray(m2000.dayofyear)
bt=pd.DatetimeIndex(b.time.values); bdoy=doy_of(bt)
bvals=b.values.astype(np.float64)
ny,nx=bvals.shape[1:]
base_mask=(bt>=pd.Timestamp('1992-01-01'))&(bt<=pd.Timestamp('2002-12-31'))
Bdates=bt[base_mask]; Bdoy=bdoy[base_mask]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
for d in range(1,367):
    if d==60: continue
    idx=[]
    for B in Bdates[Bdoy==d]:
        w=pd.date_range(B-pd.Timedelta(days=5),B+pd.Timedelta(days=5))
        idx.extend(bt.get_indexer(w))
    idx=np.unique(np.array(idx)); assert (idx>=0).all()
    pool=bvals[idx]
    with np.errstate(all='ignore'):
        thr[d]=np.nanpercentile(pool,90,axis=0,method='hazen')
        clim[d]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a366):
    out=np.empty_like(a366)
    for d in range(1,367):
        ids=[((d-1+k)%366) for k in range(-15,16)]
        out[d-1]=np.mean(a366[ids],axis=0)
    return out
T=smooth(thr[1:])
tt=pd.DatetimeIndex(t.time.values); tdoy=doy_of(tt)
tv=t.values.astype(np.float64)
sea=np.all(np.isfinite(tv),axis=0)
print('sea cells',sea.sum(),'of',sea.size, 'thr nan in sea', np.isnan(T[tdoy-1][:,sea]).sum())
hot=(tv>=T[tdoy-1]) & sea[None]
mhw=np.zeros(tv.shape,bool); nT=tv.shape[0]
for i in range(ny):
    for j in range(nx):
        if not sea[i,j]: continue
        h=hot[:,i,j]; ev=[]; k=0
        while k<nT:
            if h[k]:
                s=k
                while k<nT and h[k]: k+=1
                if k-s>=5: ev.append([s,k-1])
            else: k+=1
        merged=[]
        for e in ev:
            if merged and e[0]-merged[-1][1]-1 in (1,2): merged[-1][1]=e[1]
            else: merged.append(list(e))
        for s,e in merged: mhw[s:e+1,i,j]=True
active=mhw.any(axis=(1,2))
events=[]; k=0
while k<nT:
    if active[k]:
        s=k
        while k<nT and active[k]: k+=1
        events.append({"onset":str(tt[s].date()),"end":str(tt[k-1].date())})
    else: k+=1
print(events, int(mhw.sum()), int(active.sum()))
os.makedirs('output',exist_ok=True)
out=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
    coords={'time':t.time.values,'lat':t.latitude.values,'lon':t.longitude.values})
out.to_netcdf('output/mhw_mask.nc')
rep={"region":{"lat_min":59.93,"lat_max":61.13,"lon_min":18.69,"lon_max":19.89},
     "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
     "target_analysed":{"start":"2009-06-01","end":"2009-08-31"},
     "events":events,"complete":True,
     "caveats":"Land/no-data cells (NaN in target period) are not sea cells and are set to 0. Pool includes window extension days 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05. Event end is the last active day."}
json.dump(rep,open('output/report.json','w'),indent=2)
print(xr.open_dataset('output/mhw_mask.nc').mhw.shape)
