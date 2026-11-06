
import fsspec, xarray as xr, re, numpy as np, os, json
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
P='icsa2027_data_20261101T090944Z/s1z'
with fs.open(f'{P}/sst_19820101.nc','rb') as f:
    ds=xr.open_dataset(f, engine='h5netcdf').load()
print(ds.analysed_sst.attrs); print(ds.analysed_sst.encoding); print(ds.attrs['comment'])
