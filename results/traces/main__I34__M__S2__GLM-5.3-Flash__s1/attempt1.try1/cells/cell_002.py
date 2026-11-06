import xarray as xr, numpy as np, time
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
lat = ds.latitude.values.astype(np.float64)
lon = ds.longitude.values.astype(np.float64)
print("lat range", lat.min(), lat.max(), "step", np.diff(lat)[:3])
print("lon range", lon.min(), lon.max(), "step", np.diff(lon)[:3])
latb = (59.93, 61.13); lonb = (18.69, 19.89)
latmask = (lat >= latb[0]) & (lat <= latb[1])
lonmask = (lon >= lonb[0]) & (lon <= lonb[1])
i0, i1 = np.where(latmask)[0][[0,-1]]
j0, j1 = np.where(lonmask)[0][[0,-1]]
print("lat idx", i0, i1, "vals", lat[i0], lat[i1], "n=", i1-i0+1)
print("lon idx", j0, j1, "vals", lon[j0], lon[j1], "n=", j1-j0+1)
print("units:", ds.analysed_sst.attrs.get('units'), "| standard_name:", ds.analysed_sst.attrs.get('standard_name'))
t = ds.time.values
print("time dtype", t.dtype, "n=", len(t), "first", t[0], "last", t[-1])
# check daily continuity
d = np.diff(t).astype('timedelta64[D]').astype(int)
print("time step unique:", np.unique(d))
import json
print(json.dumps({k: v for k, v in ds.analysed_sst.attrs.items() if not isinstance(v, bytes)}, default=str)[:800])
