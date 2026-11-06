import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/data/sst_20190601.nc', engine='h5netcdf')
v = ds['analysed_sst']
print(v.attrs)
print(v.encoding)
lat = ds['latitude'].values
lon = ds['longitude'].values
print("lat range:", lat.min(), lat.max(), "n=", lat.size, "step:", np.diff(lat)[:5])
print("lon range:", lon.min(), lon.max(), "n=", lon.size, "step:", np.diff(lon)[:5])
# region mask (careful with float32 comparisons)
latm = (lat >= 64.39) & (lat <= 65.59)
lonm = (lon >= 23.41) & (lon <= 24.61)
print("region lats:", lat[latm].min(), lat[latm].max(), latm.sum())
print("region lons:", lon[lonm].min(), lon[lonm].max(), lonm.sum())
sst = v.values[0]
sub = sst[np.ix_(latm, lonm)]
print("sub shape:", sub.shape, "min:", sub.min(), "max:", sub.max(), "nans:", np.isnan(sub).sum())
print("sample values (deg C if -273.15):", sub.ravel()[:8] - 273.15)
ds.close()
