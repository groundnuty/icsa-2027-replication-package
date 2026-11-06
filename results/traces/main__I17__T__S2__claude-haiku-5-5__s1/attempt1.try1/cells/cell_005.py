
script = r'''
import fsspec, xarray as xr, numpy as np, pandas as pd, json, os
fs = fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(fs.open(p,'rb'),engine='h5netcdf')
sub=ds.sel(latitude=slice(56.63,57.83), longitude=slice(20.23,21.43))
b=sub.analysed_sst.sel(time=slice('1991-12-27','2003-01-05')).load()
t=sub.analysed_sst.sel(time=slice('2010-06-01','2010-08-31')).load()
bt=pd.DatetimeIndex(b.time.values); tt=pd.DatetimeIndex(t.time.values)
bv=b.values.astype(np.float64); tv=t.values.astype(np.float64)
lat=sub.latitude.values; lon=sub.longitude.values
sea=np.all(np.isfinite(tv),axis=0)
print("grid",len(lat),len(lon),"sea cells:",sea.sum(), "target nan:",np.isnan(tv).sum())

def doy_of(d):
    d=pd.DatetimeIndex(d)
    x=np.array([ (pd.Timestamp(2001,m,1)+pd.Timedelta(days=dd-1)).dayofyear if not (m==2 and dd==29) else 60
                 for m,dd in zip(d.month,d.day)])
    # 2001 is non-leap: Feb dd -> proper doy; Mar onward correct
    return x
bdoy=doy_of(bt); tdoy=doy_of(tt)
print("check doy:", doy_of(pd.DatetimeIndex(['2004-02-28','2004-02-29','2004-03-01','2004-12-31'])))

# baseline dates: 1992-01-01..2002-12-31
inbase=(bt>=pd.Timestamp('1992-01-01'))&(bt<=pd.Timestamp('2002-12-31'))
base_idx=np.where(inbase)[0]
thr=np.full((367,)+bv.shape[1:],np.nan)  # index by doy 1..366
clim=np.full_like(thr,np.nan)
for d in range(1,367):
    if d==60: continue
    # baseline dates with doy d
    cand=base_idx[bdoy[base_idx]==d]
    if len(cand)==0: continue
    pool_idx=[]
    for i in cand:
        c=bt[i]
        for k in range(-5,6):
            tgt=c+pd.Timedelta(days=k)
            pool_idx.append(tgt)
    pool_idx=pd.DatetimeIndex(pool_idx).unique()
    # map to indices in bt
    pos=bt.get_indexer(pool_idx)
    assert (pos>=0).all()
    pool=bv[pos]
    with np.errstate(all='ignore'):
        thr[d]=np.nanquantile(pool,0.9,axis=0,method='hazen')
        clim[d]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2
clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a366=a[1:367]  # days 1..366 -> index 0..365
    out=np.empty_like(a366)
    for d in range(366):
        idx=[(d+k)%366 for k in range(-15,16)]
        out[d]=np.mean(a366[idx],axis=0)
    r=np.full_like(a,np.nan); r[1:367]=out; return r
thrS=smooth(thr); climS=smooth(clim)
nb=np.isfinite(thrS[1:367]).all(axis=0)
print("baseline range:", bt[base_idx].min(), bt[base_idx].max(), "cells with valid thr:", nb.sum())

# per-cell hot
T=len(tt)
hot=np.zeros((T,)+tv.shape[1:],bool)
for i in range(T):
    thrd=thrS[tdoy[i]]
    with np.errstate(invalid='ignore'):
        hot[i]=tv[i]>=thrd   # NaN -> False
hot &= sea[None]
mhw=np.zeros_like(hot)
ny,nx=sea.shape
for y in range(ny):
    for x in range(nx):
        if not sea[y,x]: continue
        h=hot[:,y,x]
        # runs
        runs=[]; i=0
        while i<T:
            if h[i]:
                j=i
                while j+1<T and h[j+1]: j+=1
                if j-i+1>=5: runs.append([i,j])
                i=j+1
            else: i+=1
        # join gaps 1-2 days
        merged=[]
        for r in runs:
            if merged and (r[0]-merged[-1][1]-1) in (1,2):
                merged[-1][1]=r[1]
            else: merged.append(list(r))
        for s,e in merged: mhw[s:e+1,y,x]=True
active=mhw.any(axis=(1,2))
events=[]; i=0
while i<T:
    if active[i]:
        j=i
        while j+1<T and active[j+1]: j+=1
        events.append({"onset":str(tt[i].date()),"end":str(tt[j].date())})
        i=j+1
    else: i+=1
print("events:",events)
print("mhw cell-days:",mhw.sum(), "sea cells with any mhw:", mhw.any(axis=0).sum())
os.makedirs('output',exist_ok=True)
out=xr.Dataset({"mhw":(("time","lat","lon"),mhw.astype(np.uint8))},
               coords={"time":t.time.values,"lat":lat,"lon":lon})
out.to_netcdf('output/mhw_mask.nc')
report={"region":{"lat_min":56.63,"lat_max":57.83,"lon_min":20.23,"lon_max":21.43},
        "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
        "target_analysed":{"start":"2010-06-01","end":"2010-08-31"},
        "events":events,"complete":True,
        "caveats":("Region has 60x60 grid cells (lat 56.64-57.82, lon 20.24-21.42), all within bounds. Sea cells are those finite on all target days. "
                   "Per-cell MHW joining applied within each cell. Land cells are NaN and never hot. "
                   f"Sea cells with any MHW day: {int(mhw.any(axis=0).sum())}. Baseline threshold uses full 1992-2002 pool with +-5-day windows including the extended edge days.")}
json.dump(report,open('output/report.json','w'),indent=2)
print("written")
'''
open('/tmp/mhw.py','w').write(script)
import subprocess
r=subprocess.run(['python','/tmp/mhw.py'],capture_output=True,text=True)
print(r.stdout[-6000:], r.stderr[-3000:])
