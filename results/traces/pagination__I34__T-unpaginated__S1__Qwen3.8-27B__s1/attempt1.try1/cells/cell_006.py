
import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s1z/sst_20070601.nc"
t0 = time.time()
f = fs.open(path, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
lat = ds["latitude"].values
lon = ds["longitude"].values
print("lat range", lat.min(), lat.max(), "lon range", lon.min(), lon.max())
print("lat spacing", np.unique(np.diff(lat))[:3], "lon spacing", np.unique(np.diff(lon))[:3])
eps = 1e-6
lat_sel = np.where((lat >= 59.93 - eps) & (lat <= 61.13 + eps))[0]
lon_sel = np.where((lon >= 18.69 - eps) & (lon <= 19.89 + eps))[0]
print("n lat:", len(lat_sel), lat[lat_sel[0]], lat[lat_sel[-1]])
print("n lon:", len(lon_sel), lon[lon_sel[0]], lon[lon_sel[-1]])
sst = ds["analysed_sst"].values[:, lat_sel, lon_sel]
print("sst dtype", sst.dtype, "shape", sst.shape)
print("finite:", np.isfinite(sst).sum(), "of", sst.size)
print("min/max finite:", np.nanmin(sst), np.nanmax(sst))
print("elapsed open+read region slice:", time.time()-t0)
ds.close()
