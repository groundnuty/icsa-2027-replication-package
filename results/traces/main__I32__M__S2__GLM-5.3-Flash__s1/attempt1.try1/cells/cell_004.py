import xarray as xr, numpy as np, time
p = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(p, engine="h5netcdf")
print("units attr:", ds.analysed_sst.attrs)
lat = ds.latitude.values; lon = ds.longitude.values
la = np.where((lat >= 59.05-1e-6) & (lat <= 60.25+1e-6))[0]
lo = np.where((lon >= 21.25-1e-6) & (lon <= 22.45+1e-6))[0]
print("lat cells:", la[0], la[-1], "lon cells:", lo[0], lo[-1])
t0=time.time()
sub = ds.analysed_sst.isel(time=slice(0,5), latitude=slice(la[0],la[-1]+1), longitude=slice(lo[0],lo[-1]+1)).values
print("read 5 slices: %.2fs" % (time.time()-t0), sub.shape, sub.dtype)
print("sample values:", sub[0, ipv6-7, ipv6-7])
print("finite frac target-like:", np.isfinite(sub).mean())
