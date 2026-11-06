import os, glob
files = glob.glob('/work/data/*.nc')
print("local files:", len(files))
# check none truncated (size > 0)
import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
small = [(os.path.basename(f), os.path.getsize(f)) for f in files if os.path.getsize(f) < 50000]
print("suspiciously small:", small[:10], len(small))
# spot-check one mid-list file integrity
import xarray as xr
ds = xr.open_dataset('/work/data/sst_19990715.nc', engine='h5netcdf')
print(ds.analysed_sst.shape, ds.time.values)
ds.close()
