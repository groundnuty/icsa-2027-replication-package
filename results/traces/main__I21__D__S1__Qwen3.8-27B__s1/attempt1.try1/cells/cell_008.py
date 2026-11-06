import xarray as xr, numpy as np
ds = xr.open_dataset('/work/data/sst_20210601.nc', engine='h5netcdf')
v = ds.analysed_sst
lat = ds.latitude.values; lon = ds.longitude.values
ilats = np.where((lat >= 57.33) & (lat <= 58.53))[0]
ilons = np.where((lon >= 9.03) & (lon <= 10.23))[0]
print("lat idx:", ilats.min(), ilats.max(), "values:", lat[ilats][:6], "...", lat[ilats][-6:])
print("lon idx:", ilons.min(), ilons.max(), "values:", lon[ilons][:6], "...", lon[ilons][-6:])
vals = v.values[0, ilats[:,None], ilons[None,:]]
print("shape:", vals.shape, "finite frac:", np.isfinite(vals).mean())
print("min/max finite:", np.nanmin(vals), np.nanmax(vals))
print("nonfinite count:", (~np.isfinite(vals)).sum())
# which pattern: print a coarse mask
m = np.isfinite(vals)
for r in range(0, 60, 6):
    print(''.join('#' if m[r,c] else '.' for c in range(0,60,2)))
ds.close()
