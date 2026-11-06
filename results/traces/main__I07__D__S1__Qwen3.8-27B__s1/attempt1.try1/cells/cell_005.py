import xarray as xr, numpy as np
ds = xr.open_dataset('/work/sst_20210601.nc', engine='h5netcdf')
v = ds['analysed_sst']
print("attrs:", v.attrs)
print("dims:", v.dims, v.dtypes)
arr = v.values
print("shape:", arr.shape)
finite = np.isfinite(arr)
print("finite fraction:", finite.mean())
# region slice
lat = ds.latitude.values
lon = ds.longitude.values
sl = (lat >= 54.45) & (lat <= 55.65) & (lon >= 16.05) & (lon <= 17.25)
print("lat in region:", sl[:,0].sum() if sl.ndim==2 else sl.sum())
lat_idx = np.where(np.isin(lat, np.arange(54.45, 55.651, 0.02)))[0]
# better: direct mask
lm = (lat >= 54.45) & (lat <= 55.65)
mm = (lon >= 16.05) & (lon <= 17.25)
print("n lat:", lm.sum(), "n lon:", mm.sum())
print("lats:", lat[lm][:3], lat[lm][-3:])
print("lons:", lon[mm][:3], lon[mm][-3:])
reg = arr[0][np.ix_(lm, mm)]
print("region finite fraction:", np.isfinite(reg).mean())
print("region value range:", np.nanmin(reg), np.nanmax(reg))
# check what land looks like: sample a few
print("min raw:", arr.min(), "max raw:", arr.max())
# unique non-finite values
vals, counts = np.unique(arr, return_counts=True)
nonfin = vals[~np.isfinite(vals)]
print("nonfinite values:", nonfin)
ds.close()
