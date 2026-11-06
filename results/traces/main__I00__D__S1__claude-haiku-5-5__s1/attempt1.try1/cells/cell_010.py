script = r'''
import fsspec, os, json, numpy as np, xarray as xr, pandas as pd, warnings
warnings.filterwarnings("ignore")
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
dates=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2004-06-01','2004-08-31'))
def get(d):
    s=d.strftime('%Y%m%d'); loc=f'/work/d/sst_{s}.nc'
    if not os.path.exists(loc):
        fs.get(f'icsa2027_data_20261101T090944Z/s1z/sst_{s}.nc',loc)
    with xr.open_dataset(loc,engine='h5netcdf') as ds:
        lat=ds.latitude.values; lon=ds.longitude.values
        il=np.where((lat>=54.13-1e-4)&(lat<=55.33+1e-4))[0]
        jl=np.where((lon>=14.67-1e-4)&(lon<=15.87+1e-4))[0]
        v=ds.analysed_sst.isel(latitude=il,longitude=jl).values.astype(np.float64)
        return v, lat[il], lon[jl]
with ThreadPoolExecutor(8) as ex:
    res=list(ex.map(get,dates))
lat=res[0][1]; lon=res[0][2]
arr=np.stack([r[0][0] for r in res])
dt=pd.DatetimeIndex(dates)
doy=np.array([pd.Timestamp(2000,m,d).day_of_year for m,d in zip(dt.month,dt.day)])
is_base=(dt>=pd.Timestamp('1992-01-01'))&(dt<=pd.Timestamp('2002-12-31'))
base_dates=dt[is_base]
pos={d:i for i,d in enumerate(dt)}
ny=arr.shape[1:]
thr=np.full((367,)+ny,np.nan); clim=np.full((367,)+ny,np.nan)
for d in range(1,367):
    if d==60: continue
    bsel=base_dates[doy[is_base]==d]
    if len(bsel)==0: continue
    idx=sorted({pos[b+pd.Timedelta(days=k)] for b in bsel for k in range(-5,6)})
    pool=arr[idx]
    thr[d]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[d]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    out=np.full_like(a,np.nan)
    for d in range(1,367):
        ids=[((d-1+k)%366)+1 for k in range(-15,16)]
        out[d]=np.sum(a[ids],axis=0)/31.0
    return out
thr_s=smooth(thr); clim_s=smooth(clim)
tsel=np.where((dt>=pd.Timestamp('2004-06-01'))&(dt<=pd.Timestamp('2004-08-31')))[0]
tgt=arr[tsel]; tdt=dt[tsel]; tdoy=doy[tsel]
sea=np.all(np.isfinite(tgt),axis=0)
T=len(tsel)
print('sea',sea.sum(),'T',T,tdt[0].date(),tdt[-1].date())
ys,xs=np.where(sea)
mhw=np.zeros((T,)+ny,np.uint8)
hotv=tgt[:,ys,xs]>=thr_s[tdoy][:,ys,xs]
print('nan thr sea', np.isnan(thr_s[tdoy][:,ys,xs]).sum())
for c in range(len(ys)):
    h=hotv[:,c]; runs=[]; t=0
    while t<T:
        if h[t]:
            s=t
            while t<T and h[t]: t+=1
            if t-s>=5: runs.append([s,t-1])
        else: t+=1
    merged=[]
    for r in runs:
        if merged and r[0]-merged[-1][1]-1<=2: merged[-1][1]=r[1]
        else: merged.append(r)
    for s,e in merged: mhw[s:e+1,ys[c],xs[c]]=1
active=mhw.reshape(T,-1).any(axis=1)
events=[]; t=0
while t<T:
    if active[t]:
        s=t
        while t<T and active[t]: t+=1
        events.append({"onset":str(tdt[s].date()),"end":str(tdt[t-1].date())})
    else: t+=1
print(events)
print('cell-days',int(mhw.sum()),'active days',int(active.sum()))
os.makedirs('/work/output',exist_ok=True) if False else None
os.makedirs('output',exist_ok=True)
ds=xr.Dataset({'mhw':(('time','lat','lon'),mhw)},
    coords={'time':tdt.values,'lat':lat,'lon':lon})
ds['mhw'].attrs={'long_name':'marine heatwave flag per cell'}
ds.to_netcdf('output/mhw_mask.nc',engine='h5netcdf')
rep={"region":{"lat_min":54.13,"lat_max":55.33,"lon_min":14.67,"lon_max":15.87},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2004-06-01","end":"2004-08-31"},
 "events":events,"complete":True,
 "caveats":"Sea cells=3301 of 3600 region grid cells (finite SST all target days). Region grid cells taken from file coords 54.14-55.32 N, 14.68-15.86 E (0.02 deg grid). Threshold/climatology from 1992-2002 with +/-5-day windows that reach 1991-12-27 and 2003-01-05. Climatology computed but not used for hot-day test (method uses threshold). Non-sea cells set to 0."}
json.dump(rep,open('output/report.json','w'),indent=2)
print(open('output/report.json').read())
'''
open('/work/run.py','w').write(script)
import subprocess
r=subprocess.run(['python','/work/run.py'],capture_output=True,text=True,cwd='/work')
print(r.stdout[-6000:]); print(r.stderr[-3000:])