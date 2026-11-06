
code = r'''
import xarray as xr, numpy as np, pandas as pd, json, os
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(p,engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=57.85-1e-6)&(lat<=59.05+1e-6))[0]; lo=np.where((lon>=21.01-1e-6)&(lon<=22.21+1e-6))[0]
sub=ds.analysed_sst.isel(latitude=la,longitude=lo)
ext=sub.sel(time=slice('1991-12-27','2003-01-05')).load()
tgt=sub.sel(time=slice('2013-06-01','2013-08-31')).load()
def doy_of(t):
    t=pd.Timestamp(t)
    if t.month==2 and t.day==29: return 60
    d=t.dayofyear
    if (not t.is_leap_year) and t.month>2: d+=1
    return d
ext_t=pd.DatetimeIndex(ext.time.values)
ext_doy=np.array([doy_of(t) for t in ext_t])
base_dates=pd.date_range('1992-01-01','2002-12-31')
base_doy=np.array([doy_of(t) for t in base_dates])
V=ext.values.astype(np.float64)  # (T,ny,nx)
ny,nx=V.shape[1:]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
for d in range(1,367):
    if d==60: continue
    bd=base_dates[base_doy==d]
    if len(bd)==0: continue
    # window dates: within +-5 days of any baseline date with doy d
    win=set()
    for b in bd:
        for k in range(-5,6):
            win.add(b+pd.Timedelta(days=k))
    idx=np.where(ext_t.isin(pd.DatetimeIndex(sorted(win))))[0]
    pool=V[idx]
    with np.errstate(all='ignore'):
        thr[d]=np.nanquantile(pool,0.9,axis=0,method='hazen')
        clim[d]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    # a: (367,...) index 1..366 used; 0 unused
    b=a[1:367]
    out=np.empty_like(b)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(b[ids],axis=0)
    return out
thr_s=smooth(thr); clim_s=smooth(clim)  # index i -> doy i+1
tgt_doy=np.array([doy_of(t) for t in pd.DatetimeIndex(tgt.time.values)])
T=tgt.values.astype(np.float64)
sea=np.all(np.isfinite(T),axis=0)
print('sea cells',sea.sum(),'of',sea.size, 'baseline sea nan?', np.isnan(V[:,sea]).sum())
thr_t=thr_s[tgt_doy-1]  # (Tt,ny,nx)
hot=(T>=thr_t)&sea[None]
ntg=T.shape[0]
mask=np.zeros_like(hot)
for iy in range(ny):
    for ix in range(nx):
        if not sea[iy,ix]: continue
        h=hot[:,iy,ix]
        # runs
        runs=[];i=0
        while i<ntg:
            if h[i]:
                j=i
                while j+1<ntg and h[j+1]: j+=1
                if j-i+1>=5: runs.append([i,j])
                i=j+1
            else: i+=1
        # join gaps of 1-2 non-hot days
        merged=[]
        for r in runs:
            if merged and r[0]-merged[-1][1]-1<=2:
                merged[-1][1]=r[1]
            else: merged.append(list(r))
        for a,b in merged: mask[a:b+1,iy,ix]=True
active=mask.any(axis=(1,2))
events=[];i=0
while i<ntg:
    if active[i]:
        j=i
        while j+1<ntg and active[j+1]: j+=1
        events.append((i,j)); i=j+1
    else: i+=1
tt=pd.DatetimeIndex(tgt.time.values)
ev=[{"onset":str(tt[a].date()),"end":str(tt[b].date())} for a,b in events]
print('events',ev)
print('mask sum',mask.sum(), 'max thr check', np.nanmax(thr_s[:,sea]), 'sea clim finite', np.isfinite(clim_s[:,sea]).all(), np.isfinite(thr_s[:,sea]).all())
os.makedirs('output',exist_ok=True)
out=xr.Dataset({'mhw':(('time','lat','lon'),mask.astype(np.uint8))},
    coords={'time':tgt.time.values,'lat':tgt.latitude.values,'lon':tgt.longitude.values})
out.to_netcdf('output/mhw_mask.nc')
rep={"region":{"lat_min":57.85,"lat_max":59.05,"lon_min":21.01,"lon_max":22.21},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2013-06-01","end":"2013-08-31"},
 "events":ev,"complete":True,
 "caveats":"Land cells (NaN) are 0 in mask; threshold computed for all cells but used only for sea cells. Coordinates taken as stored float32 values within bounds with 1e-6 tolerance. Baseline windows use ext data 1991-12-27..2003-01-05."}
json.dump(rep,open('output/report.json','w'),indent=1)
print(open('output/report.json').read())
'''
open('/tmp/mhw.py','w').write(code)
import subprocess
r=subprocess.run(['python','/tmp/mhw.py'],capture_output=True,text=True,cwd='/tmp')
print(r.stdout[-6000:], r.stderr[-3000:])
