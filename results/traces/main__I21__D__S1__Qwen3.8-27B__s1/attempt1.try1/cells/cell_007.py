import xarray as xr, numpy as np
ds = xr.open_dataset('/work/data/sst_20210601.nc', engine='h5netcdf')
v = ds.analysed_sst
print("attrs:", v.attrs)
lat = ds.latitude.values; lon = ds.longitude.values
print("lat min/max:", lat.min(), lat.max(), "unique step:", np.unique(np.diff(lat)))
print("lon min/max:", lon.min(), lon.max())
slat = (lat >= 57.33) & (lat <= 58.53)
slon = (lon >= 9.03) & (lon <= 10.23)
print("n lat:", slat.sum(), "n lon:", slon.sum())
vals = v.values[0, slat[:,None], slon[None,:]]
print("finite fraction in region:", np.isfinite(vals).mean())
print("sample values:", vals[10,10], vals[30,30])
# land detection: look at where values are finite across a few days later; for now just unique-ish
print("min/max finite:", vals[np.isfinite(vals)].min(), vals[np.isfinite(vals)].max())
# check fill value
print("nonfinite count:", (~np.isfinite(vals)).sum())
ds.close()
