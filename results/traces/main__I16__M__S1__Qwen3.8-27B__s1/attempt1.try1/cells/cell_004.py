import xarray as xr, numpy as np, time
t0=time.time()
ds = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s1z/sst_20080601.nc", engine="h5netcdf")
lat = ds.latitude.values; lon = ds.longitude.values
print("lat range", lat.min(), lat.max(), "step", np.diff(lat[:5]))
print("lon range", lon.min(), lon.max(), "step", np.diff(lon[:5]))
sl = (lat>=56.63)&(lat<=57.83)
so = (lon>=20.23)&(lon<=21.43)
print("n lat:", sl.sum(), "n lon:", so.sum())
print("lat selected:", lat[sl][0], "...", lat[sl][-1])
print("lon selected:", lon[so][0], "...", lon[so][-1])
sub = ds.analysed_sst.isel(latitude=np.where(sl)[0], longitude=np.where(so)[0]).values
print("region shape:", sub.shape, sub.dtype, "min", np.nanmin(sub), "max", np.nanmax(sub), "nan frac", np.isnan(sub).mean())
ds.close()
print("open+read time:", time.time()-t0)
