import xarray as xr
import numpy as np, time

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')
v = ds.analysed_sst
print("h5netcdf object type:", type(v.variable._var) if hasattr(v.variable, '_var') else '?')
try:
    import h5netcdf as h
    f = h.File(path, 'r')
    ds_ = f['analysed_sst']
    print("chunks:", getattr(ds_, 'chunks', None))
    f.close()
except Exception as e:
    print("err", e)

# Test 1: one full day plane (626x1051x4 ~ 2.63 MB)
s = time.time()
a = v.values[3647]  # full plane for 1 day
dt = time.time() - s
print(f"full plane 1 day: {a.nbytes/1e6:.2f} MB in {dt:.2f}s -> {a.nbytes/1e6/dt:.1f} MB/s")

# Test 2: one day, region only (60x60)
s = time.time()
b = v.values[3647, 438:498, 487:547]
dt = time.time() - s
print(f"region 1 day: {b.nbytes/1e3:.1f} kB in {dt:.2f}s")
print("finite in region:", np.isfinite(b).sum(), "/", b.size)

# Test 3: 30 days region
s = time.time()
c = v.values[3647:3677, 438:498, 487:547]
dt = time.time() - s
print(f"region 30 days: {c.nbytes/1e6:.2f} MB in {dt:.2f}s -> {c.nbytes/1e6/dt:.2f} MB/s")
