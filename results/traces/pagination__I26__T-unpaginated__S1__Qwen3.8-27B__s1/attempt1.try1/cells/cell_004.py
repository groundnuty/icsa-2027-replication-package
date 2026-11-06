import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
f = fs.open(base + '/sst_20070601.nc', "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
v = ds['analysed_sst']
print("attrs:", dict(v.attrs))
lat = ds.latitude.values
lon = ds.longitude.values
# region selection
latm = (lat >= 57.83 - 1e-9) & (lat <= 59.03 + 1e-9)
lonm = (lon >= 17.41 - 1e-9) & (lon <= 18.61 + 1e-9)
print("n lat:", latm.sum(), "n lon:", lonm.sum())
print("lats:", lat[latm][:3], lat[latm][-3:])
print("lons:", lon[lonm][:3], lon[lonm][-3:])
t0 = time.time()
sub = v.isel(latitude=np.where(latm)[0], longitude=np.where(lonm)[0]).values
t1 = time.time()
print("read time one file region:", t1-t0, "s")
print("dtype:", sub.dtype, "shape:", sub.shape)
print("finite:", np.isfinite(sub).sum(), "of", sub.size)
print("sample values:", sub[0,:5], sub[30,30])
f.close()
