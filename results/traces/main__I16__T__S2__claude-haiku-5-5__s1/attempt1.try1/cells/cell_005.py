
script = r'''
import fsspec, xarray as xr, numpy as np, pandas as pd, json, os
fs = fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(fs.open(p,'rb'),engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=56.63)&(lat<=57.83))[0]; lo=np.where((lon>=20.23)&(lon<=21.43))[0]
sub=ds.isel(latitude=slice(la[0],la[-1]+1),longitude=slice(lo[0],lo[-1]+1))
b=sub.analysed_sst.sel(time=slice('1991-12-27','2003-01-05')).load()
t=sub.analysed_sst.sel(time=slice('2008-06-01','2008-08-31')).load()
bt=pd.DatetimeIndex(b.time.values); tt=pd.DatetimeIndex(t.time.values)
def doy(dates):
    d2000=pd.to_datetime(dict(year=2000,month=dates.month,day=dates.day))
    return np.asarray(d2000.dayofyear)
bdoy=doy(bt); tdoy=doy(tt)
B=b.values.astype(np.float64)
ny,nx=B.shape[1:]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
bd_in=(bt>=pd.Timestamp('1992-01-01'))&(bt<=pd.Timestamp('2002-12-31'))
for d in range(1,367):
    if d==60: continue
    Ds=bt[bd_in & (bdoy==d)]
    if len(Ds)==0: continue
    idx=set()
    for D in Ds:
        m=np.where((bt>=D-pd.Timedelta(days=5))&(bt<=D+pd.Timedelta(days=5)))[0]
        idx.update(m.tolist())
    pool=B[sorted(idx)]
    thr[d]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[d]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a1=a[1:367]
    out=np.empty_like(a1)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(a1[ids],axis=0)
    return out
thrS=smooth(thr)  # index d-1
climS=smooth(clim)
T=t.values.astype(np.float64)
sea=np.all(np.isfinite(T),axis=0)
print('sea cells',sea.sum(),'of',sea.size)
print('baseline doy coverage: days with pool', np.sum(~np.isnan(thrS[:,0,0])))
hot=np.zeros(T.shape,bool)
thr_t=thrS[tdoy-1]  # (nt,ny,nx)
with np.errstate(invalid='ignore'):
    hot=(T>=thr_t)&np.isfinite(thr_t)
hot&=sea[None]
nt=T.shape[0]
mhw=np.zeros((nt,ny,nx),bool)
def runs(x):
    # returns list of (start,end) inclusive of True runs
    r=[];s=None
    for i,v in enumerate(x):
        if v and s is None: s=i
        if not v and s is not None: r.append((s,i-1)); s=None
    if s is not None: r.append((s,len(x)-1))
    return r
for j in range(ny):
    for i in range(nx):
        if not sea[j,i]: continue
        h=hot[:,j,i]
        segs=[r for r in runs(h) if r[1]-r[0]+1>=5]
        if not segs: continue
        merged=[list(segs[0])]
        for s,e in segs[1:]:
            gap=s-merged[-1][1]-1
            if gap<=2: merged[-1][1]=e
            else: merged.append([s,e])
        for s,e in merged: mhw[s:e+1,j,i]=True
active=mhw.any(axis=(1,2))
events=[]
for s,e in runs(active):
    events.append({"onset":str(tt[s].date()),"end":str(tt[e].date())})
print('events',events)
print('active days',active.sum(),'sea',sea.sum(),'mhw cell-days',mhw.sum())
os.makedirs('output',exist_ok=True)
out=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
    coords={'time':t.time.values,'lat':sub.latitude.values,'lon':sub.longitude.values})
out['mhw'].attrs={'long_name':'marine heatwave flag'}
out.to_netcdf('output/mhw_mask.nc')
rep={"region":{"lat_min":56.63,"lat_max":57.83,"lon_min":20.23,"lon_max":21.43},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":str(tt.min().date()),"end":str(tt.max().date())},
 "events":events,"complete":True,
 "caveats":"Grid subset of 60x60 cells (lat 56.64-57.82, lon 20.24-21.42, the grid points inside bounds). Land/NaN cells excluded from sea-cell set. Day-of-year via fixed leap-year mapping. Baseline pool from 1991-12-27..2003-01-05 windows."}
json.dump(rep,open('output/report.json','w'),indent=2)
print(json.dumps(rep)[:800])
'''
open('run.py','w').write(script)
import subprocess
r=subprocess.run(['python','run.py'],capture_output=True,text=True)
print(r.stdout[-6000:], r.stderr[-3000:])
