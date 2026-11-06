import xarray as xr, numpy as np, time

ds = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s1z/sst_20040701.nc", engine="h5netcdf")
arr = ds["analysed_sst"].values[0]  # (626,1051)
lat = ds["latitude"].values.astype(np.float64)
lon = ds["longitude"].values.astype(np.float64)
ds.close()

tol = 1e-5
sel_lat = (lat >= 57.57 - tol) & (lat <= 58.77 + tol)
sel_lon = (lon >= 10.25 - tol) & (lon <= 11.45 + tol)
i0, i1 = int(np.argmax(sel_lat)), int(len(lat)-1-np.argmax(sel_lat[::-1]))
j0, j1 = int(np.argmax(sel_lon)), int(len(lon)-1-np.argmax(sel_lon[::-1]))
sub = arr[i0:i1+1, j0:j1+1]
print("subset shape:", sub.shape, "finite frac:", np.isfinite(sub).mean(), "nan:", np.isnan(sub).sum())
print("min/max:", np.nanmin(sub), np.nanmax(sub))

# check a winter file and a target-boundary file for NaNs in region
for fname in ["sst_20041225.nc", "sst_20040601.nc", "sst_20040831.nc", "sst_19911227.nc", "sst_20030105.nc", "sst_19920229.nc"]:
    d2 = xr.open_dataset(f"/data/icsa2027_data_20261101T090944Z/s1z/{fname}", engine="h5netcdf")
    a = d2["analysed_sst"].values[0][i0:i1+1, j0:j1+1]
    d2.close()
    print(fname, "nan in region:", np.isnan(a).sum(), "min:", np.nanmin(a) if np.isfinite(a).any() else None)

# verify lat/lon edge values vs bounds
print("lat edges:", lat[i0], lat[i1], "lon edges:", lon[j0], lon[j1])
# confirm no grid point within 1e-5 of the 4 bounds
for b in (57.57, 58.77, 10.25, 11.45):
    d = np.min(np.abs(np.concatenate([lat, lon]) - b))
    print("bound", b, "min grid distance:", d)
