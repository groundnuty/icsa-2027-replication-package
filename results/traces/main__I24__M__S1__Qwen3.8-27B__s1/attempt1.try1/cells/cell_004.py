import xarray as xr, numpy as np, time

t0 = time.time()
ds = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s1z/sst_20040701.nc", engine="h5netcdf")
print("open time:", time.time()-t0)
v = ds["analysed_sst"]
print("attrs:", v.attrs)
t0 = time.time()
arr = v.values
print("read full array time:", time.time()-t0, arr.dtype, arr.shape)
print("nan count:", np.isnan(arr).sum(), "min:", np.nanmin(arr), "max:", np.nanmax(arr))

lat = ds["latitude"].values.astype(np.float64)
lon = ds["longitude"].values.astype(np.float64)
print("lat[0..3]:", lat[:4], "lon[0..3]:", lon[:4])
print("lat step:", np.unique(np.diff(lat))[:3], "lon step:", np.unique(np.diff(lon))[:3])

tol = 1e-5
sel_lat = (lat >= 57.57 - tol) & (lat <= 58.77 + tol)
sel_lon = (lon >= 10.25 - tol) & (lon <= 11.45 + tol)
print("n lat:", sel_lat.sum(), lat[sel_lat][0], lat[sel_lat][-1])
print("n lon:", sel_lon.sum(), lon[sel_lon][0], lon[sel_lon][-1])
i0 = int(np.argmax(sel_lat)); i1 = int(len(lat)-1-np.argmax(sel_lat[::-1]))
j0 = int(np.argmax(sel_lon)); j1 = int(len(lon)-1-np.argmax(sel_lon[::-1]))
print("index ranges:", i0, i1, j0, j1)
sub = arr[None, i0:i1+1, j0:j1+1]
print("subset finite fraction:", np.isfinite(sub).mean(), "nan:", np.isnan(sub).sum())
print("subset min/max:", np.nanmin(sub), np.nanmax(sub))
ds.close()
