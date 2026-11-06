import os, time, warnings, json
import numpy as np, xarray as xr
warnings.filterwarnings('ignore')
print('cwd:', os.getcwd())

cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])  # leap-style cumulative month starts
def date_of_doy(d, y):
    m = np.searchsorted(cum, d, side='left') - 1
    return np.datetime64(f'{y:04d}-{m+1:02d}-{d-cum[m]:02d}')

t_start = time.time()
ds = xr.open_dataset('/work/s2z/sst_s2.nc', engine='h5netcdf')
t = ds.time.values
lat = ds.latitude.values; lon = ds.longitude.values
lat_idx = np.where((lat >= 56.09) & (lat <= 57.29))[0]
lon_idx = np.where((lon >= 10.55) & (lon <= 11.75))[0]

b0 = np.searchsorted(t, np.datetime64('1991-12-27'))
b1 = np.searchsorted(t, np.datetime64('2003-01-05'), side='right')
ext_dates = t[b0:b1].astype('datetime64[D]')
print('extended baseline:', str(ext_dates[0]), '..', str(ext_dates[-1]), 'ndays', len(ext_dates))

sst_b = ds.analysed_sst.isel(time=slice(b0, b1), latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)
print('sst_b', sst_b.shape, sst_b.dtype, 'loaded at', round(time.time()-t_start,1), 's')

# Build pool day indices per day-of-year
pool_idx = {}
sizes = []
for d in range(1, 367):
    if d == 60:
        continue
    idxs = []
    for y in range(1992, 2003):
        d0 = date_of_doy(d, y)
        s = d0 - np.timedelta64(5, 'D'); e = d0 + np.timedelta64(5, 'D')
        i0 = np.searchsorted(ext_dates, s); i1 = np.searchsorted(ext_dates, e, side='right')
        idxs.append(np.arange(i0, i1))
    idxs = np.concatenate(idxs)
    assert np.all(np.diff(idxs) > 0), d  # windows must not overlap
    pool_idx[d] = idxs
    sizes.append(len(idxs))
sizes = np.array(sizes)
print('pool sizes: min', sizes.min(), 'max', sizes.max(), 'count@121:', (sizes==121).sum(), 'count@33:', (sizes==33).sum())
# spot check d=1 covers 1991-12-27..1992-01-06 etc.
i1d = pool_idx[1]
print('d=1 first/last dates:', str(ext_dates[i1d[0]]), str(ext_dates[i1d[-1]]), 'n=', len(i1d))
i365 = pool_idx[365]
print('d=365 first/last dates:', str(ext_dates[i365[0]]), str(ext_dates[i365[-1]]), 'n=', len(i365))
i366 = pool_idx[366]
print('d=366 dates:', str(ext_dates[i366[0]]), '..', str(ext_dates[i366[-1]]), 'n=', len(i366))
print('d=366 unique years:', sorted({str(ext_dates[i])[:4] for i in i366}))

thr = np.full((366, 60, 60), np.nan, dtype=np.float64)
clim = np.full((366, 60, 60), np.nan, dtype=np.float64)
tt = time.time()
for d in range(1, 367):
    if d == 60:
        continue
    vals = sst_b[pool_idx[d]]           # (npool, 60, 60) float64
    thr[d-1] = np.nanpercentile(vals, 90, axis=0, method='hazen')
    clim[d-1] = np.nanmean(vals, axis=0)
    if d % 60 == 0:
        print('  doy', d, 'done at', round(time.time()-tt,1), 's')
print('percentile loop finished in', round(time.time()-tt,1), 's')

# day 60 = mean of days 59 and 61 (before smoothing)
thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])
print('day60 filled from days 59/61')

def smooth31_wrap(arr):  # arr: (366, ...)
    ext = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    c = np.cumsum(ext, axis=0)
    c = np.concatenate([np.zeros_like(c[:1]), c], axis=0)
    s = (c[31:] - c[:-31]) / 31.0     # s[i] = mean(ext[i..i+30]) -> arr[(i-15)..(i+15)] mod 366
    return s

thr_s = smooth31_wrap(thr)
clim_s = smooth31_wrap(clim)
print('smoothed shapes:', thr_s.shape, clim_s.shape, 'finite:', np.isfinite(thr_s).all(axis=(1,2)).sum(), '/366 doys fully finite')

np.savez('/work/thr_clim.npz', thr=thr, clim=clim, thr_s=thr_s, clim_s=clim_s,
         lat_idx=lat_idx, lon_idx=lon_idx, b0=b0, b1=b1, j0=0)
# save target indices too
j0 = int(np.searchsorted(t, np.datetime64('2009-06-01')))
j1 = int(np.searchsorted(t, np.datetime64('2009-08-31'), side='right'))
np.savez('/work/idx.npz', j0=j0, j1=j1)
print('saved caches. total time', round(time.time()-t_start,1), 's')
print('sample thr_s doy 200 (cell 30,30):', thr_s[199,30,30], ' clim_s:', clim_s[199,30,30])
print('n threshold NaN cells (land):', np.mean(~np.isfinite(thr_s))*100, '%')