
code = r'''
import xarray, numpy as np, pandas as pd, json, os
ds = xarray.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
ilat=np.where((lat>=54.45-1e-6)&(lat<=55.65+1e-6))[0]; ilon=np.where((lon>=16.05-1e-6)&(lon<=17.25+1e-6))[0]
t=ds.time.values
m=((t>=np.datetime64('1991-12-27'))&(t<=np.datetime64('2003-01-05')))|((t>=np.datetime64('2021-06-01'))&(t<=np.datetime64('2021-08-31')))
tidx=np.where(m)[0]
sub=ds.analysed_sst.isel(time=tidx, latitude=ilat, longitude=ilon).load()
dates = pd.DatetimeIndex(t[tidx])
A = sub.values.astype(np.float64)
T,NY,NX = A.shape
def doy(d):
    if d.month==2 and d.day==29: return 60
    return pd.Timestamp(2001, d.month, d.day).dayofyear
doys = np.array([doy(d) for d in dates])
anchor_dates = pd.date_range('1992-01-01','2002-12-31')
date_to_i = {d:i for i,d in enumerate(dates)}
pm = {d: [] for d in range(1,367)}
for a in anchor_dates:
    d = doy(a)
    if d==60: continue
    for k in range(-5,6):
        v = a + pd.Timedelta(days=k)
        if v in date_to_i: pm[d].append(date_to_i[v])
pm = {d: np.unique(np.array(v,dtype=int)) for d,v in pm.items() if len(v)}
print('pools', len(pm), min(len(v) for v in pm.values()), 60 in pm)
# sea cells
tgt = (dates>=pd.Timestamp('2021-06-01'))&(dates<=pd.Timestamp('2021-08-31'))
ti_t = np.where(tgt)[0]
sea = np.all(np.isfinite(A[ti_t]),axis=0)
print('sea cells', sea.sum(), 'of', NY*NX)
thr = np.full((367,NY,NX), np.nan); clim = np.full((367,NY,NX), np.nan)
import warnings; warnings.filterwarnings('ignore')
for d,idx in pm.items():
    P = A[idx]  # (n,NY,NX)
    thr[d] = np.nanquantile(P, 0.9, axis=0, method='hazen')
    clim[d] = np.nanmean(P, axis=0)
thr[60] = (thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(x):  # x: (366,...) index 0..365 for doy 1..366
    out = np.empty_like(x)
    for i in range(366):
        ids = [(i+k)%366 for k in range(-15,16)]
        out[i] = np.mean(x[ids],axis=0)
    return out
thr366 = smooth(thr[1:367]); clim366 = smooth(clim[1:367])
np.savez('/work/thr.npz', thr=thr366, clim=clim366, sea=sea, ti=ti_t, tidx=tidx)
print('done thr nan', np.isnan(thr366[:,sea]).sum())
'''
open('/work/s1.py','w').write(code)
import subprocess
r=subprocess.run(['python','/work/s1.py'],capture_output=True,text=True); print(r.stdout[-3000:], r.stderr[-3000:])
