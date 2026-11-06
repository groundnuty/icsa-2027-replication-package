import xarray as xr, numpy as np, os
base = "/data/icsa2027_data_20261101T090944Z/s1z"
ds = xr.open_dataset(os.path.join(base,"sst_20170701.nc"), engine="h5netcdf")
v = ds["analysed_sst"].values.astype("float64")
lat = ds.latitude.values.astype("float64"); lon = ds.longitude.values.astype("float64")
slat = (lat>=62.25-1e-9)&(lat<=63.45+1e-9)
slon = (lon>=18.73-1e-9)&(lon<=19.93+1e-9)
sub = v[:, slat][:, :, slon]
print("sub shape", sub.shape, "finite frac", np.isfinite(sub).mean(), "finite count", int(np.isfinite(sub).sum()))
print("encoding:", ds["analysed_sst"].encoding)
print("sample values (K):", np.sort(sub[np.isfinite(sub)][:10]))
fin = np.isfinite(sub)
print("cells fully finite (this day):", int(fin.all(axis=0).sum()))
ds.close()
