import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/data/sst_20160601.nc', engine='h5netcdf')
v = ds['analysed_sst']
print("attrs:", v.attrs)
print("dtype:", v.dtype)
lat = ds['latitude'].values
lon = ds['longitude'].values
print("lat range:", lat.min(), lat.max(), "lon range:", lon.min(), lon.max())
latm = (lat >= 64.51) & (lat <= 65.71)
lonm = (lon >= 21.97) & (lon <= 23.17)
print("n lat:", latm.sum(), "n lon:", lonm.sum())
sub = v.values[0][latm][:, lonm].astype('float64')
print("region shape:", sub.shape)
print("min/max/finite:", sub.min(), sub.max(), np.isfinite(sub).all())
print("sample values (C?):", sub.flatten()[:10])
print("unique non-finite count:", np.sum(~np.isfinite(sub)))
ds.close()
