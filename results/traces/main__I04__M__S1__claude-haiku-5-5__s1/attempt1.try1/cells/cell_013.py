import xarray as xr, subprocess
x=xr.open_dataset("/work/output/mhw_mask.nc"); print(x.mhw.dtype, x.mhw.dims, x.mhw.shape, int(x.mhw.max()), x.time.values[[0,-1]])