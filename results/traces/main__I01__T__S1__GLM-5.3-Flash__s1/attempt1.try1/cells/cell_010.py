import fsspec, xarray as xr, numpy as np, datetime as dt, time, os

fs = fsspec.filesystem('onedata')
P = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(P, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat = ds.latitude.values.astype(np.float64)
lon = ds.longitude.values.astype(np.float64)
times = ds.time.values
print('total days:', len(times), 'strictly increasing:', bool(np.all(np.diff(times.astype('int64')) > 0)))

la0, la1, lo0, lo1 = 54.13, 55.33, 14.67, 15.87
ii = np.where((lat >= la0 - 1e-6) & (lat <= la1 + 1e-6))[0]
jj = np.where((lon >= lo0 - 1e-6) & (lon <= lo1 + 1e-6))[0]
print('lat idx', ii[0], '..', ii[-1], 'n', len(ii), '| lon idx', jj[0], '..', jj[-1], 'n', len(jj))
lat_r = ds.latitude.values[ii]   # keep float32 dataset values for output
lon_r = ds.longitude.values[jj]
print('lat_r[0],[−1]:', lat_r[0], lat_r[-1], ' lon_r[0],[−1]:', lon_r[0], lon_r[-1])

def read_period(d0, d1):
    t0 = np.searchsorted(times, np.datetime64(d0, 'ns'))
    t1 = np.searchsorted(times, np.datetime64(d1, 'ns'))
    assert times[t0] == np.datetime64(d0, 'ns') and times[t1] == np.datetime64(d1, 'ns'), (times[t0], times[t1])
    arr = ds.analysed_sst.isel(time=slice(t0, t1+1), latitude=ii, longitude=jj).values.astype(np.float64)
    return times[t0:t1+1], arr

t0 = time.time()
btimes, base_sst = read_period('1991-12-27', '2003-01-05')
print('baseline window read: %d days, %.1f s' % (len(btimes), time.time()-t0))
t0 = time.time()
ttimes, tgt_sst = read_period('2008-06-01', '2008-08-31')
print('target read: %d days, %.1f s' % (len(ttimes), time.time()-t0))
f.close(); ds.close()

# diagnostics
sea = np.isfinite(tgt_sst).all(axis=0)
print('target shape', tgt_sst.shape, 'baseline shape', base_sst.shape)
print('sea cells (finite on every target day):', int(sea.sum()), 'of', sea.size)
print('finite frac baseline: %.4f' % np.isfinite(base_sst).mean())
print('target SST range over sea: %.2f .. %.2f K' % (np.nanmin(tgt_sst[:, sea]), np.nanmax(tgt_sst[:, sea])))
print('target mean over sea: %.2f K' % np.nanmean(tgt_sst[:, sea]))
np.savez('/work/cache_stage1.npz', btimes=btimes.astype('datetime64[D]').astype('int64'),
         ttimes=ttimes.astype('datetime64[D]').astype('int64'),
         base_sst=base_sst, tgt_sst=tgt_sst, sea=sea, lat_r=lat_r, lon_r=lon_r, ii=ii, jj=jj)
print('cache written, size MB:', os.path.getsize('/work/cache_stage1.npz')/1e6)
