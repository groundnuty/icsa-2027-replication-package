import xarray as xr, numpy as np, time, os
base = "/data/icsa2027_data_20261101T090944Z/s1z"

t0=time.time()
ds = xr.open_dataset(os.path.join(base,"sst_20170701.nc"), engine="h5netcdf")
t1=time.time()
v = ds["analysed_sst"].values.astype("float64")
t2=time.time()
print("open+slice read:", round(t1-t0,2), "s; to mem:", round(t2-t1,2), "s")
lat = ds.latitude.values.astype("float64"); lon = ds.longitude.values.astype("float64")
print("lat range", lat.min(), lat.max(), "n=",lat.size)
print("lon range", lon.min(), lon.max(), "n=",lon.size)
slat = (lat>=62.25-1e-9)&(lat<=63.45+1e-9)
slon = (lon>=18.73-1e-9)&(lon<=19.93+1e-9)
print("lat selected", lat[slat][0], lat[slat][-1], slat.sum())
print("lon selected", lon[slon][0], lon[slon][-1], slon.sum())
sub = v[slat][:,slon]
print("sub shape", sub.shape, "finite frac", np.isfinite(sub).mean())
print("finite count", int(np.isfinite(sub).sum()), "of", sub.size)
print("sample values:", sub[np.isfinite(sub)][:5])
print("encoding:", ds["analysed_sst"].encoding)
ds.close()
