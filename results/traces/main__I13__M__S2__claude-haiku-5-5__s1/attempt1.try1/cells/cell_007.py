
import xarray as xr, numpy as np, pandas as pd, os, json
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(p,engine='h5netcdf')
sub=ds.sel(latitude=slice(56.09,57.29), longitude=slice(10.55,11.75))
b0,b1=pd.Timestamp('1991-12-27'),pd.Timestamp('2003-01-05')
bsel=sub.analysed_sst.sel(time=slice(b0,b1))
base=bsel.load().values.astype(np.float64)
btime=pd.DatetimeIndex(bsel.time.values)
tsel=sub.analysed_sst.sel(time=slice('2021-06-01','2021-08-31'))
tgt=tsel.load().values.astype(np.float64)
ttime=pd.DatetimeIndex(tsel.time.values)
cum=[0,31,60,91,121,152,182,213,244,274,305,335]
def doy(t): return cum[t.month-1]+t.day
bd=[t for t in btime if pd.Timestamp('1992-01-01')<=t<=pd.Timestamp('2002-12-31')]
idx={t:i for i,t in enumerate(btime)}
ny,nx=base.shape[1:]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
for d in range(1,367):
    if d==60: continue
    dates=set()
    for b in bd:
        if doy(b)==d:
            for k in range(-5,6): dates.add(b+pd.Timedelta(days=k))
    dates=sorted(t for t in dates if t in idx)
    pool=base[[idx[t] for t in dates]]
    thr[d]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[d]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2
thr=thr[1:367]
def smooth(a):
    out=np.empty_like(a)
    for d in range(366):
        ii=[(d+k)%366 for k in range(-15,16)]
        out[d]=a[ii].mean(axis=0)
    return out
thrS=smooth(thr)
sea=np.all(np.isfinite(tgt),axis=0)
T=len(ttime)
doys=np.array([doy(t) for t in ttime])-1
th=thrS[doys]
hot=(tgt>=th)&sea[None]
mhw=np.zeros((T,ny,nx),dtype=bool)
for i in range(ny):
    for j in range(nx):
        if not sea[i,j]: continue
        h=hot[:,i,j]
        runs=[];t=0
        while t<T:
            if h[t]:
                s=t
                while t<T and h[t]: t+=1
                if t-s>=5: runs.append([s,t-1])
            else: t+=1
        merged=[]
        for r in runs:
            if merged and r[0]-merged[-1][1]-1<=2: merged[-1][1]=r[1]
            else: merged.append(r[:])
        for s,e in merged: mhw[s:e+1,i,j]=True
active=mhw.any(axis=(1,2))
events=[];t=0
while t<T:
    if active[t]:
        s=t
        while t<T and active[t]: t+=1
        events.append({"onset":str(ttime[s].date()),"end":str(ttime[t-1].date())})
    else: t+=1
print(events, mhw.sum(), active.sum(), sea.sum(), np.isnan(tgt[:, ~sea]).all() if (~sea).any() else None)
os.makedirs('output',exist_ok=True)
out=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
    coords={'time':ttime.values,'lat':sub.latitude.values,'lon':sub.longitude.values})
out.to_netcdf('output/mhw_mask.nc')
rep={"region":{"lat_min":56.09,"lat_max":57.29,"lon_min":10.55,"lon_max":11.75},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2021-06-01","end":"2021-08-31"},
 "events":events,"complete":True,
 "caveats":"Region grid is 60x60 native cells (about 0.02 deg). 3296 cells are sea cells (finite on all target days); other cells set to 0. Baseline pools have 121 values per day of year. Computed in float64 from float32 stored values."}
json.dump(rep,open('output/report.json','w'),indent=2)
print(open('output/report.json').read()[:300])
