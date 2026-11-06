import numpy as np, xarray as xr, datetime, warnings

thr = np.load('/work/thr.npy'); clim = np.load('/work/clim.npy')
lat_idx = np.load('/work/lat_idx.npy'); lon_idx = np.load('/work/lon_idx.npy')

# Independent recomputation for doy=166 (Jun 15), cell (lat row 10, lon col 10 within region)
r, c = 10, 10
cell = (r, c)
pools = []
for y in range(1992, 2003):
    b = datetime.date(y, 6, 15)
    for k in range(-5, 6):
        dt = b + datetime.timedelta(days=k)
        ds = xr.open_dataset(f'/work/data/sst_{dt.strftime("%Y%m%d")}.nc', engine='h5netcdf')
        val = ds['analysed_sst'].values[0][lat_idx[r], lon_idx[c]]  # float32
        ds.close()
        pools.append(float(val))
pools = np.array(pools)
print("pool size:", len(pools), "nans:", int(np.isnan(pools).sum()))
q90 = np.nanquantile(pools, 0.9, method="hazen")
mn = np.nanmean(pools)
print("independent thr[165]:", q90, " saved:", thr[165, cell], " equal:", np.isclose(q90, thr[165, cell]))
print("independent clim[165]:", mn, " saved:", clim[165, cell])

# independent check for doy=167 (Jun 16) in leap-adjacent window? use doy=61 (Mar 1) to test Feb29 inclusion
r2, c2 = 30, 40
pools61 = []
for y in range(1992, 2003):
    b = datetime.date(y, 3, 1)
    for k in range(-5, 6):
        dt = b + datetime.timedelta(days=k)
        ds = xr.open_dataset(f'/work/data/sst_{dt.strftime("%Y%m%d")}.nc', engine='h5netcdf')
        val = ds['analysed_sst'].values[0][lat_idx[r2], lon_idx[c2]]
        ds.close()
        pools61.append(float(val))
pools61 = np.array(pools61)
q61 = np.nanquantile(pools61, 0.9, method="hazen")
print("independent thr[60] (doy61):", q61, " saved:", thr[60, (r2,c2)], " equal:", np.isclose(q61, thr[60, (r2,c2)]))
# verify Feb 29 of 1992 is in the doy-61 pool: 1992-02-29 = b - 1 day
ds = xr.open_dataset('/work/data/sst_19920229.nc', engine='h5netcdf')
v29 = ds['analysed_sst'].values[0][lat_idx[r2], lon_idx[c2]]
ds.close()
print("1992-02-29 value present in doy61 pool:", v29 in pools61)

# smoothing check: recompute raw[60..62] from saved thr? we overwrote raw. Instead verify smoothing relation
# thr = smooth31(thr_raw): check that thr[d] equals mean of 31 values of thr_raw -> we don't have raw saved.
# Re-derive: thr_raw = ? not invertible directly; instead recompute thr for a 3-day window and compare smoothed.
# Simpler: reconstruct raw at d=166,167,165 via independent pools is heavy. Instead check smoothing property:
# thr[d] - thr[d+1] should equal (raw[d-15]-raw[d+16])/31 ... skip; verify convolution on a synthetic + verify saved thr is smooth:
diffs = np.abs(np.diff(thr[:, cell]))
print("max consecutive diff of smoothed thr (doy160-170, cell):", diffs[158:168].max())
