import xarray as xr, numpy as np
ds = xr.open_dataset('/work/data/sst_19911227.nc', engine='h5netcdf')
print(ds.time.encoding)
print(ds.latitude[:3], ds.latitude[-3:])
print(ds.longitude[:3], ds.longitude[-3:])
lat = ds.latitude.values.astype(np.float64)
lon = ds.longitude.values.astype(np.float64)
# region masks
il = np.where((lat >= 58.69) & (lat <= 59.89))[0]
io = np.where((lon >= 18.69) & (lon <= 19.89))[0]
print("lat cells:", il[0], il[-1], len(il), lat[il[0]], lat[il[-1]])
print("lon cells:", io[0], io[-1], len(io), lon[io[0]], lon[io[-1]])
print("lat range:", lat[il].min(), lat[il].max(), "lon range:", lon[io].min(), lon[io].max())
ds.close()
