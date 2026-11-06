
code = r'''
import xarray as xr, numpy as np, pandas as pd, json, os, warnings
warnings.filterwarnings('ignore')
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(p,engine='h5netcdf')
sub=ds.sel(latitude=slice(58.69,59.89),longitude=slice(18.69,19.89))
b=sub.analysed_sst.sel(time=slice('1991-12-27','2003-01-05')).load()
tg=sub.analysed_sst.sel(time=slice('2010-06-01','2010-08-31')).load()
lat=sub.latitude.values; lon=sub.longitude.values
ref=pd.date_range('2000-01-01','2000-12-31')
doy_of_md={(d.month,d.day):i+1 for i,d in enumerate(ref)}
def doy(ts): return doy_of_md[(ts.month,ts.day)]
bdates=pd.date_range('1991-12-27','2003-01-05')
bvals=b.values.astype(np.float64)
bidx={d:i for i,d in enumerate(bdates)}
bl=pd.date_range('1992-01-01','2002-12-31')
pool_idx={d:set() for d in range(1,367)}
for bd in bl:
    dd=doy(bd)
    if dd==60: continue
    for k in range(-5,6):
        pool_idx[dd].add(bidx[bd+pd.Timedelta(days=k)])
thr=np.full((367,)+bvals.shape[1:],np.nan); clim=np.full_like(thr,np.nan)
for d in range(1,367):
    if d==60: continue
    idx=sorted(pool_idx[d])
    P=bvals[idx]
    thr[d]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[d]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(A):
    arr=A[1:367]
    out=np.empty_like(arr)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(arr[ids],axis=0)
    return out
T=smooth(thr); C=smooth(clim)
print('pool sizes', len(pool_idx[1]), len(pool_idx[59]), len(pool_idx[61]), len(pool_idx[366]))
print('NaN in T', np.isnan(T).sum(), 'NaN in C', np.isnan(C).sum())
sea=np.isfinite(tg.values).all(axis=0)
S=tg.values.astype(np.float64)  # (92,lat,lon)
tdates=pd.DatetimeIndex(tg.time.values)
tdoy=np.array([doy(t) for t in tdates])
Tday=T[tdoy-1]  # (92,lat,lon)
hot=(S>=Tday)&sea[None]
hot=np.where(np.isnan(Tday),False,hot)
nt,nla,nlo=hot.shape
mhw=np.zeros_like(hot)
for i in range(nla):
    for j in range(nlo):
        if not sea[i,j]: continue
        h=hot[:,i,j]
        # runs of hot days
        runs=[]; k=0
        while k<nt:
            if h[k]:
                s=k
                while k<nt and h[k]: k+=1
                if k-s>=5: runs.append([s,k-1])
            else: k+=1
        # join runs separated by 1 or 2 non-hot days
        merged=[]
        for r in runs:
            if merged and (r[0]-merged[-1][1]-1)<=2:
                merged[-1][1]=r[1]
            else: merged.append(list(r))
        for s,e in merged: mhw[s:e+1,i,j]=True
active=mhw.any(axis=(1,2))
events=[]; k=0
while k<nt:
    if active[k]:
        s=k
        while k<nt and active[k]: k+=1
        events.append({"onset":str(tdates[s].date()),"end":str(tdates[k-1].date())})
    else: k+=1
print('active days', active.sum(), 'events', events)
print('sea cells', sea.sum(), 'mhw cell-days', mhw.sum())
os.makedirs('output',exist_ok=True)
out=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
    coords={'time':tg.time.values,'lat':lat,'lon':lon})
out['mhw'].attrs={'long_name':'marine heatwave flag'}
out.to_netcdf('output/mhw_mask.nc')
rep={"region":{"lat_min":58.69,"lat_max":59.89,"lon_min":18.69,"lon_max":19.89},
     "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
     "target_analysed":{"start":"2010-06-01","end":"2010-08-31"},
     "events":events,"complete":True,
     "caveats":"Land cells (NaN SST) set to 0; sea cells defined as finite on all target days. Day-of-year mapping by fixed leap-year (2000) month/day table. Baseline pools use calendar windows (+/-5 days) around 1992-2002 dates; edges use 1991-12-27 to 2003-01-05 data."}
json.dump(rep,open('output/report.json','w'),indent=2)
print('written')
'''
open('/tmp/mhw.py','w').write(code)
import subprocess
r=subprocess.run(['python','/tmp/mhw.py'],capture_output=True,text=True,cwd='/tmp')
print(r.stdout[-6000:], r.stderr[-3000:])
