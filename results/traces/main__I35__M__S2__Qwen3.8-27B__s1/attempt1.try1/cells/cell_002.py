import xarray as xr, numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
var = ds["analysed_sst"]
print("encoding:", var.encoding)
print("attrs:", var.attrs)
print()
lat = ds.latitude.values
lon = ds.longitude.values
t = ds.time.values
print("lat range:", lat.min(), lat.max(), "n:", len(lat), "diff:", np.unique(np.diff(lat))[:5])
print("lon range:", lon.min(), lon.max(), "n:", len(lon), "diff:", np.unique(np.diff(lon))[:5])
print("time[0]:", t[0], "time[-1]:", t[-1], "n:", len(t))
print("unique time diffs:", np.unique(np.diff(t)))

# region cells
lat_min, lat_max, lon_min, lon_max = 59.93, 61.13, 18.69, 19.89
il = np.where((lat >= lat_min) & (lat <= lat_max))[0]
io = np.where((lon >= lon_min) & (lon <= lon_max))[0]
print("lat cells:", il.min(), il.max(), il.max()-il.min()+1, lat[il[0]], lat[il[-1]])
print("lon cells:", io.min(), io.max(), io.max()-io.min()+1, lon[io[0]], lon[io[-1]])
print("region size:", (il.max()-il.min()+1)*(io.max()-io.min()+1))
