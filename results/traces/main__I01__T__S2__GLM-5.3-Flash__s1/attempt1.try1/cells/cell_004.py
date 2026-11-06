import fsspec, xarray as xr, numpy as np, datetime as dt, warnings, time

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
sst = ds['analysed_sst']
tvals = ds.time.values
lat = ds.latitude.values; lon = ds.longitude.values
latmask = (lat >= 54.13) & (lat <= 55.33); lonmask = (lon >= 14.67) & (lon <= 15.87)
la = np.where(latmask)[0]; lo = np.where(lonmask)[0]
lat_sl = slice(la[0], la[-1]+1); lon_sl = slice(lo[0], lo[-1]+1)

# baseline slab dates: 1991-12-27 .. 2003-01-05 (covers every +/-5-day window around 1992-2002 dates)
b0 = np.searchsorted(tvals, np.datetime64('1991-12-27'))
b1 = np.searchsorted(tvals, np.datetime64('2003-01-05'), 'right')
print("baseline idx", b0, b1, "n days", b1-b0, tvals[b0], tvals[b1-1])
base_D = tvals[b0].astype('datetime64[D]')

t0 = time.time()
basel = sst.isel(time=slice(b0,b1), latitude=lat_sl, longitude=lon_sl).values.astype(np.float64)
print("baseline read %.1fs shape %s" % (time.time()-t0, basel.shape))
print("baseline SST range (K): %.3f .. %.3f" % (np.nanmin(basel), np.nanmax(basel)))

# centers: for doy d in year y  (leap-safe): d<=59 -> Jan1+(d-1); d>=61 -> Mar1+(d-61)
years = list(range(1992, 2003))
def center_date(y, d):
    if d <= 59:  return dt.date(y,1,1) + dt.timedelta(days=d-1)
    if d >= 61:  return dt.date(y,3,1) + dt.timedelta(days=d-61)
    return None  # d == 60 (Feb 29): no pool of its own

thr = np.full((366, 60, 60), np.nan)
clim = np.full((366, 60, 60), np.nan)
pool_sizes = []
t0 = time.time()
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, 367):
        if d == 60: continue
        ks = []
        for y in years:
            c = center_date(y, d)
            k = int((np.datetime64(c, 'D') - base_D).astype(int))
            ks.extend(range(k-5, k+6))
        ks = np.array(sorted(set(ks)))
        assert ks.min() >= 0 and ks.max() < (b1-b0)
        pool_sizes.append(len(ks))
        pool = basel[ks]                       # (n_pool, 60, 60) float64
        thr[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
        clim[d-1] = np.nanmean(pool, axis=0)
print("pool loop %.1fs; pool sizes min/max: %d/%d" % (time.time()-t0, min(pool_sizes), max(pool_sizes)))

# day 60 <- mean of day 59 and 61 (before smoothing)
thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])

# unweighted centred 31-day moving mean, wrapping modulo 366
offs = np.arange(-15, 16)
sidx = (np.arange(366)[:, None] + offs[None, :]) % 366
thr_sm = thr[sidx].mean(axis=1)
clim_sm = clim[sidx].mean(axis=1)

print("thr_sm NaN cells:", int(np.isnan(thr_sm).any(axis=0).sum()), " clim_sm NaN cells:", int(np.isnan(clim_sm).any(axis=0).sum()))
print("thr_sm range: %.3f .. %.3f K" % (np.nanmin(thr_sm), np.nanmax(thr_sm)))
print("clim_sm range: %.3f .. %.3f K" % (np.nanmin(clim_sm), np.nanmax(clim_sm)))
# sample: a central cell, days 150-160
print("sample thr_sm[149:160, 30, 30]:", np.round(thr_sm[149:160, 30, 30], 3).tolist())
print("sample clim_sm[149:160, 30, 30]:", np.round(clim_sm[149:160, 30, 30], 3).tolist())

np.savez_compressed('/tmp/mhw_interm.npz', thr_sm=thr_sm, clim_sm=clim_sm)
print("saved /tmp/mhw_interm.npz")
