import xarray as xr, numpy as np
ds = xr.open_dataset('/work/sst_20210601.nc', engine='h5netcdf')
v = ds['analysed_sst']
arr = v.values
lat = ds.latitude.values; lon = ds.longitude.values
lm = (lat >= 54.45) & (lat <= 55.65)
mm = (lon >= 16.05) & (lon <= 17.25)
print("n lat:", lm.sum(), "n lon:", mm.sum())
print("lats:", lat[lm][0], lat[lm][-1], "lons:", lon[mm][0], lon[mm][-1])
reg = arr[0][np.ix_(lm, mm)]
print("region finite fraction:", np.isfinite(reg).mean())
print("region value range:", np.nanmin(reg), np.nanmax(reg))
print("global finite fraction:", np.isfinite(arr).mean())
print("global min/max:", np.nanmin(arr), np.nanmax(arr))
vals, counts = np.unique(arr, return_counts=True)
print("nonfinite values:", vals[~np.isfinite(vals)])
print("n unique values:", len(vals))
ds.close()
