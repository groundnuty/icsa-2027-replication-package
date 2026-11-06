import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
v = ds["analysed_sst"]
print("attrs of analysed_sst:")
for k, val in v.attrs.items():
    print(" ", k, ":", val)
print("encoding:", v.encoding)
t = ds["time"].values
print("time[0], time[-1]:", t[0], t[-1])
print("lat range:", ds["latitude"].values.min(), ds["latitude"].values.max())
print("lon range:", ds["longitude"].values.min(), ds["longitude"].values.max())

# check region mask
lat = ds["latitude"].values
lon = ds["longitude"].values
lat_mask = (lat >= np.float32(64.39)) & (lat <= np.float32(65.59))
lon_mask = (lon >= np.float32(23.41)) & (lon <= np.float32(23.41+1.20))
print("lat cells:", np.argwhere(lat_mask).ravel()[:3], np.argwhere(lat_mask).ravel()[-3:])
print("num lat:", lat_mask.sum(), "num lon:", lon_mask.sum())
print("lat values in region:", ds["latitude"].values[lat_mask][:5], "...", ds["latitude"].values[lat_mask][-5:])
print("lon values in region:", ds["longitude"].values[lon_mask][:5], "...", ds["longitude"].values[lon_mask][-5:])
ds.close()
