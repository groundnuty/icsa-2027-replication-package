import xarray as xr, numpy as np
ds = xr.open_dataset('/work/data/sst_19920101.nc', engine='h5netcdf')
a = ds['analysed_sst']
print("units:", a.attrs)
print("dims:", a.dims)
lat = ds['latitude'].values
lon = ds['longitude'].values
print("lat range:", lat.min(), lat.max(), "n=", len(lat))
print("lon range:", lon.min(), lon.max(), "n=", len(lon))
# region selection
lat_min, lat_max = 54.17, 55.37
lon_min, lon_max = 13.25, 14.45
li = np.where((lat >= lat_min) & (lat <= lat_max))[0]
lo = np.where((lon >= lon_min) & (lon <= lon_max))[0]
print("lat idx", li.min(), li.max(), "n=", len(li), "vals:", lat[li[0]], lat[li[-1]])
print("lon idx", lo.min(), lo.max(), "n=", len(lo), "vals:", lon[lo[0]], lon[lo[-1]])
v = a.values[0, li[0]:li[-1]+1, lo[0]:lo[-1]+1]
print("region sample:", v.ravel()[:5], "finite:", np.isfinite(v).sum(), "of", v.size)
print("min/max:", np.nanmin(v), np.nanmax(v))
ds.close()
