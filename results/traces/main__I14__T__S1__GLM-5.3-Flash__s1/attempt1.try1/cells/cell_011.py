import fsspec, xarray as xr, numpy as np, pandas as pd, time as timer, warnings, pickle

t0 = timer.time()
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat = ds.latitude.values; lon = ds.longitude.values
latidx = np.where((lat >= 56.13) & (lat <= 57.33))[0]
lonidx = np.where((lon >= 17.71) & (lon <= 18.91))[0]
latvals = lat[latidx].astype(np.float64); lonvals = lon[lonidx].astype(np.float64)
times = pd.DatetimeIndex(ds.time.values)

b0, b1 = pd.Timestamp('1991-12-27'), pd.Timestamp('2003-01-05')
bidx = np.where((times >= b0) & (times <= b1))[0]
bdates = times[bidx]
arr = ds.analysed_sst.isel(time=bidx, latitude=latidx, longitude=lonidx).values.astype(np.float64)
tidx = np.where((times >= pd.Timestamp('2015-06-01')) & (times <= pd.Timestamp('2015-08-31')))[0]
tdates = times[tidx]
sst = ds.analysed_sst.isel(time=tidx, latitude=latidx, longitude=lonidx).values.astype(np.float64)
ds.close(); f.close()
print("loaded", arr.shape, sst.shape, round(timer.time()-t0,1), "s", flush=True)

sea = np.isfinite(sst).all(axis=0).ravel()          # (3600,)
print("sea cells:", int(sea.sum()))
arr_sea = arr.reshape(arr.shape[0], -1)[:, sea]     # (4028, 3300)
n_nan_base = int((~np.isfinite(arr_sea)).sum())
print("arr_sea:", arr_sea.shape, "| baseline NaNs at sea cells:", n_nan_base, "of", arr_sea.size, flush=True)

# remapped day of year
m_start = np.array([1,32,61,92,122,153,183,214,245,275,306,336])
bdoy = m_start[bdates.month.values-1] + bdates.day.values - 1
tdoy = m_start[tdates.month.values-1] + tdates.day.values - 1

# --- pools -> raw threshold (hazen q90) and mean climatology, doy 1..366 (skip 60) ---
N = arr_sea.shape[1]
thresh = np.full((366, N), np.nan)
clim   = np.full((366, N), np.nan)
windows = {d: np.array(sorted({((d + k - 1) % 366) + 1 for k in range(-5, 6)})) for d in range(1, 367) if d != 60}
for d in range(1, 367):
    if d == 60: continue
    sel = np.isin(bdoy, windows[d])
    pool = arr_sea[sel]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        thresh[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
        clim[d-1]   = np.nanmean(pool, axis=0)
    if d % 120 == 0:
        print("  doy", d, "pool size", int(sel.sum()), round(timer.time()-t0,1), "s", flush=True)

# day 60 = mean of days 59 and 61
thresh[59] = 0.5*(thresh[58] + thresh[60])
clim[59]   = 0.5*(clim[58]   + clim[60])
print("day-60 fill done; any NaN:", bool(np.isnan(thresh).any()), bool(np.isnan(clim).any()))

# --- wrapped centred 31-day moving mean ---
def smooth31(x):  # x: (366, N)
    ext = np.concatenate([x[-15:], x, x[:15]], axis=0)
    cs = np.vstack([np.zeros((1, x.shape[1])), np.cumsum(ext, axis=0)])
    return (cs[31:] - cs[:-31]) / 31.0
thresh_s = smooth31(thresh)
clim_s   = smooth31(clim)

j = 1500
for d0 in [0, 152, 365]:
    dd = d0 + 1
    idxs = [((dd + k - 1) % 366) for k in range(-15, 16)]
    print(f"doy {dd}: smoothed {thresh_s[d0, j]:.8f} vs manual {thresh[idxs, j].mean():.8f}")

with open('/tmp/stepA.pkl','wb') as fh:
    pickle.dump({'thresh_s': thresh_s, 'clim_s': clim_s, 'sst': sst, 'sea': sea,
                 'tdates': tdates, 'tdoy': tdoy, 'latvals': latvals, 'lonvals': lonvals,
                 'bdates': bdates, 'arr_sea': arr_sea}, fh)
print("saved. total", round(timer.time()-t0,1), "s")
print("cell j=1500 doy168: raw thresh", round(float(thresh[167,1500]),4), "-> smoothed", round(float(thresh_s[167,1500]),4),
      "| clim raw", round(float(clim[167,1500]),4), "-> smoothed", round(float(clim_s[167,1500]),4))
