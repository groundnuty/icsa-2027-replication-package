import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/data/sst_20090601.nc', engine="h5netcdf")
t = ds['time'].values
print("time:", t, ds['time'].dtype, "attrs:", dict(ds['time'].attrs))
lat = ds['latitude'].values; lon = ds['longitude'].values
print("lat range", lat[0], lat[-1], "lon range", lon[0], lon[-1])
# region indices
lat_sel = np.where((lat >= 63.31 - 1e-9) & (lat <= 64.51 + 1e-9))[0]
lon_sel = np.where((lon >= 21.31 - 1e-9) & (lon <= 22.51 + 1e-9))[0]
print("lat_sel:", lat_sel.min(), lat_sel.max(), lat_sel.size, "values:", lat[lat_sel[0]], lat[lat_sel[-1]])
print("lon_sel:", lon_sel.min(), lon_sel.max(), lon_sel.size, "values:", lon[lon_sel[0]], lon[lon_sel[-1]])
sst = ds['analysed_sst'].values[:, lat_sel[0]:lat_sel[-1]+1, lon_sel[0]:lon_sel[-1]+1]
print("region sst shape", sst.shape, sst.dtype)
print("finite count:", np.isfinite(sst).sum(), "of", sst.size)
print("min/max finite:", np.nanmin(sst), np.nanmax(sst))
print("nan count:", np.isnan(sst).sum())
print("attrs of sst:", dict(ds['analysed_sst'].attrs))
ds.close()
