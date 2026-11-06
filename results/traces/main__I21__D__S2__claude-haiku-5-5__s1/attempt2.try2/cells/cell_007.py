
script = r'''
import xarray as xr, numpy as np, pandas as pd, json
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=57.33-1e-6)&(lat<=58.53+1e-6))[0]; lo=np.where((lon>=9.03-1e-6)&(lon<=10.23+1e-6))[0]
sub = ds.analysed_sst.isel(latitude=la, longitude=lo).sel(time=slice('1991-12-27','2021-08-31')).load()
Tpd = pd.DatetimeIndex(sub.time.values.astype('datetime64[D]'))
A = sub.values.astype(np.float64)
latr = lat[la]; lonr = lon[lo]
def doy_of(dates):
    return np.array([d.replace(year=2000).timetuple().tm_yday for d in dates.to_pydatetime()])
D = doy_of(Tpd)
isbase = (Tpd>=pd.Timestamp('1992-01-01'))&(Tpd<=pd.Timestamp('2002-12-31'))
assert ((Tpd>=pd.Timestamp('1991-12-27'))&(Tpd<=pd.Timestamp('2003-01-05'))).sum()==(pd.Timestamp('2003-01-05')-pd.Timestamp('1991-12-27')).days+1
thr_raw = np.full((367,60,60), np.nan); clim_raw=np.full((367,60,60), np.nan)
bidx = np.where(isbase)[0]
for d in range(1,367):
    if d==60: continue
    bdates = bidx[D[bidx]==d]
    widx = np.array(sorted({bi+k for bi in bdates for k in range(-5,6)}))
    assert widx.min()>=0 and widx.max()<len(Tpd)
    pool = A[widx]
    # check pool dates are within ±5 calendar days (index contiguity assumed daily)
    with np.errstate(all='ignore'):
        thr_raw[d] = np.nanpercentile(pool, 90, axis=0, method='hazen')
        clim_raw[d] = np.nanmean(pool, axis=0)
thr_raw[60]=(thr_raw[59]+thr_raw[61])/2; clim_raw[60]=(clim_raw[59]+clim_raw[61])/2
thr_raw=thr_raw[1:]; clim_raw=clim_raw[1:]
def smooth(x):
    out=np.empty_like(x)
    for i in range(366):
        idx=[(i+k)%366 for k in range(-15,16)]
        out[i]=x[idx].mean(axis=0)
    return out
thr=smooth(thr_raw); clim=smooth(clim_raw)
tgt = (Tpd>=pd.Timestamp('2021-06-01'))&(Tpd<=pd.Timestamp('2021-08-31'))
Tt = Tpd[tgt]; At = A[tgt]; Dt = D[tgt]
sea = np.all(np.isfinite(At),axis=0)
'''
open('/work/common.py','w').write(script)
exec(script)
print('sea cells', sea.sum(), 'of', sea.size, 'target days', len(Tt), Tt[0], Tt[-1])
print('NaN thr in sea cells', np.isnan(thr[:,sea]).sum(), 'NaN raw thr', np.isnan(thr_raw[:,sea]).sum())
print('NaN clim sea', np.isnan(clim[:,sea]).sum())
print('doy target range', Dt.min(), Dt.max(), 'doy check Jun1', doy_of(pd.DatetimeIndex(['2021-06-01'])))
