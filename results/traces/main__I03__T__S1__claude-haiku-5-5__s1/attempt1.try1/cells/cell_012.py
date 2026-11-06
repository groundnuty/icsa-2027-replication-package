
import os, json, warnings
import numpy as np, xarray as xr, fsspec, pandas as pd
warnings.filterwarnings('ignore')
fs = fsspec.filesystem('onedata')
with fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb') as f:
    d=xr.open_dataset(f,engine='h5netcdf')
    lat=d.latitude.values; lon=d.longitude.values
    li=np.where((lat.astype(np.float64)>=54.17)&(lat.astype(np.float64)<=55.37))[0]
    lo=np.where((lon.astype(np.float64)>=13.25)&(lon.astype(np.float64)<=14.45))[0]
    sub=d.isel(latitude=slice(li[0],li[-1]+1), longitude=slice(lo[0],lo[-1]+1))
    seg=sub.sel(time=slice('1991-12-27','2003-01-05')).analysed_sst.load()
    tgt_da=sub.sel(time=slice('2014-06-01','2014-08-31')).analysed_sst.load()
latr=seg.latitude.values; lonr=seg.longitude.values
T=pd.DatetimeIndex(seg.time.values)
X=seg.values.astype(np.float64)
tgt_t=pd.DatetimeIndex(tgt_da.time.values)
Y=tgt_da.values.astype(np.float64)

def doy_of(ts):
    ts=pd.Timestamp(ts)
    if ts.month==2 and ts.day==29: return 60
    n=pd.Timestamp(2001,ts.month,ts.day).dayofyear
    return n+1 if ts.month>2 else n
assert doy_of('2014-12-31')==366 and doy_of('2014-03-01')==61 and doy_of('2014-02-28')==59 and doy_of('2012-02-29')==60 and doy_of('2014-01-01')==1

sea = np.isfinite(Y).all(axis=0)
base_dates=pd.date_range('1992-01-01','2002-12-31')
pool_idx={}
for b in base_dates:
    dd=doy_of(b)
    if dd==60: continue
    i=T.get_loc(b)
    pool_idx.setdefault(dd,set()).update(range(i-5,i+6))
assert min(min(s) for s in pool_idx.values())>=0 and max(max(s) for s in pool_idx.values())<len(T)

thr=np.full((366,)+X.shape[1:],np.nan); clim=np.full_like(thr,np.nan)
for dd in range(1,367):
    if dd==60: continue
    P=X[sorted(pool_idx[dd])]
    thr[dd-1]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[dd-1]=np.nanmean(P,axis=0)
thr[59]=(thr[58]+thr[60])/2; clim[59]=(clim[58]+clim[60])/2
def smooth(a):
    out=np.empty_like(a)
    for i in range(366):
        out[i]=a[[(i+k)%366 for k in range(-15,16)]].mean(axis=0)
    return out
thr_s=smooth(thr)

tdoy=np.array([doy_of(t) for t in tgt_t])
th=thr_s[tdoy-1]
hot=(Y>=th)&np.isfinite(Y)
mhw=np.zeros_like(hot)
nt=hot.shape[0]
for r in range(hot.shape[1]):
    for c in range(hot.shape[2]):
        if not sea[r,c]: continue
        h=hot[:,r,c]; runs=[]; t=0
        while t<nt:
            if h[t]:
                s=t
                while t<nt and h[t]: t+=1
                if t-s>=5: runs.append([s,t-1])
            else: t+=1
        merged=[]
        for s,e in runs:
            if merged and s-merged[-1][1]-1<=2: merged[-1][1]=e
            else: merged.append([s,e])
        for s,e in merged: mhw[s:e+1,r,c]=True
active=mhw.any(axis=(1,2))
events=[]; t=0
while t<nt:
    if active[t]:
        s=t
        while t<nt and active[t]: t+=1
        events.append((str(tgt_t[s].date()), str(tgt_t[t-1].date())))
    else: t+=1
print('sea',sea.sum(),'events',events,'active',active.sum())

os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
    coords={'time':tgt_t.values,'lat':latr,'lon':lonr}).to_netcdf('output/mhw_mask.nc')
rep={'region':{'lat_min':54.17,'lat_max':55.37,'lon_min':13.25,'lon_max':14.45},
 'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
 'target_analysed':{'start':'2014-06-01','end':'2014-08-31'},
 'events':[{'onset':a,'end':b} for a,b in events],
 'complete':True,
 'caveats':('SST read from s2z/sst_s2.nc (1982-2023), the only file covering 1992-2002 and 2014; s1z files cover only 1982-1984. '
   'Threshold pool includes margin days 1991-12-27..31 and 2003-01-01..05 via real-date +-5 windows; Feb 29 uses real-date neighbours. '
   'Cells not finite on all target days are non-sea and masked 0 (land cells are 0). Regional events are maximal runs of active days.')}
json.dump(rep,open('output/report.json','w'),indent=2)
print(xr.open_dataset('output/mhw_mask.nc').mhw.shape, open('output/report.json').read()[:300])
