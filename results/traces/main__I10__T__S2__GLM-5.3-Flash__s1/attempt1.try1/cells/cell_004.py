import numpy as np, fsspec, xarray as xr
print("numpy", np.__version__)
fs = fsspec.filesystem('onedata')
f = fs.open("icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
print("chunksizes:", ds.analysed_sst.encoding.get('chunksizes'))
print("preferred_chunks:", ds.analysed_sst.encoding.get('preferred_chunks'))
import h5py
hf = h5py.File(f, 'r')
print("h5 chunks:", hf['analysed_sst'].chunks, hf['analysed_sst'].shape, hf['analysed_sst'].dtype)
