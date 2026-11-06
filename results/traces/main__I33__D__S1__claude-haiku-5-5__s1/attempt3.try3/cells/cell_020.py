import os, xarray as xr
print(os.getcwd())
print(os.path.exists('output/mhw_mask.nc'), os.path.abspath('output'))
d=xr.open_dataset('/work/output/mhw_mask.nc'); print(d.mhw.dtype, d.mhw.dims, d.mhw.shape, int(d.mhw.sum()))