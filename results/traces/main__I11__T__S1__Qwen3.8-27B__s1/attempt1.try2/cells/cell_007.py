
import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z/'
t0 = time.time()
with fs.open(base + "sst_20210601.nc", "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
    sst = ds["analysed_sst"].values
    lat = ds["latitude"].values
    lon = ds["longitude"].values
t1 = time.time()
print("download+parse time:", t1-t0, "s; size", sst.shape, sst.dtype)
print("SST range:", np.nanmin(sst), np.nanmax(sst))
i = np.where((lat >= 55.67-1e-6) & (lat <= 56.87+1e-6))[0]
j = np.where((lon >= 16.45-1e-6) & (lon <= 17.65+1e-6))[0]
print("lat idx", i.min(), i.max(), i.size, lat[i[0]], lat[i[-1]])
print("lon idx", j.min(), j.max(), j.size, lon[j[0]], lon[j[-1]])
reg = sst[0][i[:,None], j[None,:]]
print("region finite:", np.isfinite(reg).sum(), "of", reg.size)
print("region min/max:", np.nanmin(reg), np.nanmax(reg))
