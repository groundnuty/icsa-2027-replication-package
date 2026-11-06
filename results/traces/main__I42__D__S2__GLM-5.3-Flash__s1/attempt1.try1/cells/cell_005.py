import h5py, numpy as np
f = h5py.File('/work/sst_s2.nc','r')
d = f['analysed_sst']
print("raw dtype:", d.dtype, "shape:", d.shape, "chunks:", d.chunks, "compression:", d.compression, "complevel:", d.compression_opts)
print("raw attrs:", dict(d.attrs))
print("file attrs keys:", list(f.attrs.keys()))
lat = f['latitude'][:]; lon = f['longitude'][:]
print("lat raw dtype", lat.dtype, "lon raw dtype", lon.dtype)
import numpy, xarray, pandas
print("numpy", numpy.__version__, "xarray", xarray.__version__, "pandas", pandas.__version__)
# quick peek at one day's region values
sub = d[0, 438:498, 487:547]
print("day0 region sample:", sub[:3,:3], "finite frac:", np.isfinite(sub).mean())
tm = f['time'][:]
print("time raw:", tm[:3], tm.dtype, dict(f['time'].attrs))
