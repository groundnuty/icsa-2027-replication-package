import xarray as xr
import numpy as np, time

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')
v = ds.analysed_sst
print("attrs:", dict(v.attrs))
print("encoding:", v.encoding)

# sample values (target day 2012-06-01 idx 11109, region)
s = time.time()
b = v.isel(time=slice(11109,11110), latitude=slice(438,498), longitude=slice(487,547)).values
print(f"sample read: {time.time()-s:.2f}s")
b = np.asarray(b, dtype=np.float64)
print("min/max finite:", np.nanmin(b), np.nanmax(b))
print("sample values:", np.ravel(b[np.isfinite(b)])[:10])

# benchmark 500-day region read
s = time.time()
c = v.isel(time=slice(3647,4147), latitude=slice(438,498), longitude=slice(487,547)).values
dt = time.time()-s
c = np.asarray(c, dtype=np.float64)
print(f"500-day region: {c.shape} {c.nbytes/1e6:.1f} MB in {dt:.2f}s -> {c.nbytes/1e6/dt:.1f} MB/s; finite frac {np.isfinite(c).mean():.4f}")
ds.close()
