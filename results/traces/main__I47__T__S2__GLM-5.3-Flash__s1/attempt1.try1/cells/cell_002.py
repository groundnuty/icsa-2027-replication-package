import fsspec, time, numpy as np, xarray as xr, os, sys
print("py", sys.version.split()[0])
try:
    import h5py; print("h5py", h5py.__version__)
except Exception as e: print("no h5py", e)
try:
    import netCDF4; print("netCDF4", netCDF4.__version__)
except Exception as e: print("no netCDF4", e)
try:
    import h5netcdf; print("h5netcdf", h5netcdf.__version__)
except Exception as e: print("no h5netcdf", e)
try:
    import dask; print("dask", dask.__version__)
except Exception as e: print("no dask", e)

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
t0=time.time()
f = fs.open(path, 'rb')
print("open s:", round(time.time()-t0,2))

import h5py
t0=time.time()
hf = h5py.File(f, 'r')
print("h5py open s:", round(time.time()-t0,2))
d = hf['analysed_sst']
print("shape", d.shape, "dtype", d.dtype, "chunks", d.chunks, "compression", d.compression, "comp_opts", d.compression_opts, "shuffle", d.shuffle)
print("storage_size (bytes of allocated chunks):", d.id.get_storage_size())
lat = hf['latitude'][:]; lon = hf['longitude'][:]
print("lat", lat[0], lat[-1], lat.dtype, "n=", len(lat))
print("lon", lon[0], lon[-1], lon.dtype, "n=", len(lon))
tv = hf['time']
print("time dtype", tv.dtype, tv.shape, "attrs", dict(tv.attrs))
# step check
latd = np.diff(lat.astype('float64')); lond = np.diff(lon.astype('float64'))
print("lat step min/max", latd.min(), latd.max(), "lon step min/max", lond.min(), lond.max())

# region indices
latm = (lat >= np.float32(64.39)) & (lat <= np.float32(65.59))
lonm = (lon >= np.float32(23.41)) & (lon <= np.float32(24.61))
ii = np.where(latm)[0]; jj = np.where(lonm)[0]
print("lat idx", ii.min(), ii.max(), "count", len(ii), "vals", lat[ii.min()], lat[ii.max()])
print("lon idx", jj.min(), jj.max(), "count", len(jj), "vals", lon[jj.min()], lon[jj.max()])
print("n cells", len(ii)*len(jj))
hf.close(); f.close()
