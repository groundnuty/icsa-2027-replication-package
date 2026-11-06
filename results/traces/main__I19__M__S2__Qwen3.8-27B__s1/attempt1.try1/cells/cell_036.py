import xarray as xr, numpy as np, json
ds = xr.open_dataset('/work/output/mhw_mask.nc', engine="h5netcdf")
print(ds)
print("dims:", dict(ds.sizes))
m = ds.mhw.values
print("dtype:", m.dtype, "shape:", m.shape, "values:", np.unique(m), "sum:", int(m.sum()))
print("coords:", list(ds.coords))
print("lat is index:", ds.indexes)
# netCDF4 backend read
ds2 = xr.open_dataset('/work/output/mhw_mask.nc')
assert ds2.mhw.dtype == np.uint8
assert np.array_equal(ds2.mhw.values, m)
print("netCDF4 backend read OK")
M = np.load('/work/mhw.npz', allow_pickle=True)
assert np.array_equal(m, M['mem'].reshape(92,60,60).astype(np.uint8))
print("values match computation: True")
# independent spot check of mask on a specific cell/day using the dataset + saved thresholds
import xarray as xr2
SRC = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
src = xr2.open_dataset(SRC, engine="h5netcdf")
# pick a sea cell inside the event: find one active on Jul 24
col_active = np.where(M['mem'][53])[0]
c = int(col_active[0])
r, col = divmod(c, 60)
latv = float(ds.lat[r].values); lonv = float(ds.lon[col].values)
ti = int(np.searchsorted(src.time.values, np.datetime64("2014-07-24")))
sst = float(src.analysed_sst[ti, src.latitude.values.astype(np.float64).argmin(np.abs(src.latitude.values-latv)), src.longitude.values.astype(np.float64).argmin(np.abs(src.longitude.values-lonv))].values)
thr_s = M['thr_s']
print(f"spot cell ({r},{col}) lat={latv} lon={lonv}: mask day Jul24 = {m[53,r,col]}, sst={sst:.4f} K, thr(doy153)={thr_s[152,c]:.4f} K, hot={sst >= thr_s[152,c]}")
src.close()
print(json.dumps(json.load(open('/work/output/report.json'))))
