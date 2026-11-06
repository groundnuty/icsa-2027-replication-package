import xarray as xr, numpy as np
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
lat = ds.latitude.values; lon = ds.longitude.values
print("lat dtype", lat.dtype, "lat[0],lat[-1]:", lat[0], lat[-1])
print("lon dtype", lon.dtype, "lon[0],lon[-1]:", lon[0], lon[-1])
latm = (lat >= 57.13) & (lat <= 58.33)
lonm = (lon >= 22.79) & (lon <= 23.99)
print("n lat in region:", latm.sum(), lat[latm][[0,-1]])
print("n lon in region:", lonm.sum(), lon[lonm][[0,-1]])
t = ds.time.values
print("time dtype", t.dtype, t[0], t[-1], "ndiff unique:", np.unique(np.diff(t)).astype('timedelta64[D]'))
# check encoding
print(ds.analysed_sst.encoding)
