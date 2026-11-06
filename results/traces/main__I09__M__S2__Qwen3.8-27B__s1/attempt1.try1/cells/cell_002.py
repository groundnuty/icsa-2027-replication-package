import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
v = ds['analysed_sst']
print(v.attrs)
print("dtype:", v.dtype)
lat = ds['latitude'].values
lon = ds['longitude'].values
t = ds['time'].values
print("lat range:", lat.min(), lat.max(), "nlat:", len(lat))
print("lon range:", lon.min(), lon.max(), "nlon:", len(lon))
print("time first/last:", t[0], t[-1])

# region cells
lat_min, lat_max, lon_min, lon_max = 54.81, 56.01, 19.61, 20.81
lats = lat[(lat >= lat_min) & (lat <= lat_max)]
lons = lon[(lon >= lon_min) & (lon <= lon_max)]
print("nlat in region:", len(lats), lats[:3], lats[-3:])
print("nlon in region:", len(lons), lons[:3], lons[-3:])
# check values just outside bounds
idx = np.where((lat >= lat_min-0.05) & (lat <= lat_max+0.05))[0]
print("lat around bounds:", lat[idx][:10])
idx2 = np.where((lon >= lon_min-0.05) & (lon <= lon_max+0.05))[0]
print("lon around bounds:", lon[idx2][:10])
ds.close()