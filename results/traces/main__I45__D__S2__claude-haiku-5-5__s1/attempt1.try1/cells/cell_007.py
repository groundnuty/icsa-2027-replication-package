
script = r'''
import numpy as np, xarray as xr, pandas as pd, os, json, warnings
warnings.filterwarnings('ignore')
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=63.31-1e-6)&(lat<=64.51+1e-6))[0]; lo=np.where((lon>=21.31-1e-6)&(lon<=22.51+1e-6))[0]
sub=ds.analysed_sst.sel(time=slice('1991-12-27','2009-08-31')).isel(latitude=la,longitude=lo).load()
times = pd.DatetimeIndex(sub.time.values)
vals = sub.values.astype(np.float64)
def doy(ts):
    return np.array([pd.Timestamp(2000,t.month,t.day).day_of_year for t in ts])
tpos = {t:i for i,t in enumerate(times)}
base = pd.date_range('1992-01-01','2002-12-31')
pools = {d:[] for d in range(1,367) if d!=60}
bd = doy(base)
for b,d in zip(base,bd):
    if d==60: continue
    for k in range(-5,6):
        pools[d].append(tpos[b+pd.Timedelta(days=k)])
thr_raw=np.full((367,)+vals.shape[1:],np.nan); clim_raw=np.full_like(thr_raw,np.nan)
for d,idx in pools.items():
    P = vals[idx]
    thr_raw[d]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim_raw[d]=np.nanmean(P,axis=0)
thr=thr_raw[1:].copy(); clim=clim_raw[1:].copy()
thr[59]=(thr[58]+thr[60])/2; clim[59]=(clim[58]+clim[60])/2
def smooth(a):
    out=np.empty_like(a)
    for d in range(366):
        ii=[(d+k)%366 for k in range(-15,16)]
        out[d]=np.mean(a[ii],axis=0)
    return out
thrS=smooth(thr); climS=smooth(clim)
tgt = (times>=pd.Timestamp('2009-06-01'))&(times<=pd.Timestamp('2009-08-31'))
ti = np.where(tgt)[0]; ttimes=times[ti]
T = vals[ti]
finite_all = np.all(np.isfinite(T),axis=0)
'''
open('/work/common.py','w').write(script)
diag = r'''
exec(open('/work/common.py').read())
print('sea cells',finite_all.sum())
print('NaN thr raw sea:', np.isnan(thr[:,finite_all]).sum(), 'clim raw sea:', np.isnan(clim[:,finite_all]).sum())
print('NaN thrS sea:', np.isnan(thrS[:,finite_all]).sum(), 'climS sea:', np.isnan(climS[:,finite_all]).sum())
bidx=[tpos[t] for t in pd.date_range('1991-12-27','2003-01-05') if t in tpos]
print('sea cells with NaN in baseline-extended:', np.isnan(vals[:,finite_all]).any(axis=0).sum() if False else '')
nanb = np.isnan(vals[:, finite_all]).sum(axis=0)
print('NaN counts per sea cell (whole series):', np.unique(nanb)[:10])
'''
open('/work/diag.py','w').write(diag)
import subprocess
print(subprocess.run(['python','/work/diag.py'],capture_output=True,text=True))
