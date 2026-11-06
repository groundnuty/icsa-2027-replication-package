import fsspec, numpy as np, time
import h5py
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Benchmark: h5py direct slice vs xarray
paths = [f"{base}/sst_1992060{d}.nc" for d in range(1,6)]
t0=time.time()
for p in paths:
    with fs.open(p,'rb') as f:
        with h5py.File(f,'r') as h:
            arr = h['analysed_sst'][0, 48:108, 353:413]
print("h5py 5 files:", round(time.time()-t0,3), "s", arr.dtype, arr.shape)

t0=time.time()
import xarray as xr
for p in paths:
    f = fs.open(p,'rb')
    ds = xr.open_dataset(f, engine="h5netcdf")
    v = ds.analysed_sst.isel(time=0, latitude=slice(48,108), longitude=slice(353,413)).values
    ds.close(); f.close()
print("xarray 5 files:", round(time.time()-t0,3), "s")
