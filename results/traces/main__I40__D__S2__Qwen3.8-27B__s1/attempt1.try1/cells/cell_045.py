import xarray as xr, numpy as np
ds = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(ds)
m = ds['mhw']
print("dtype:", m.dtype, "dims:", m.dims)
print("time:", m['time'].values[0], "...", m['time'].values[-1], "n:", m.sizes['time'])
print("lat first/last:", m['lat'].values[0], m['lat'].values[-1], "lon first/last:", m['lon'].values[0], m['lon'].values[-1])
# compare coords to source dataset
src = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print("lat coords match source:", np.array_equal(m['lat'].values, src['latitude'].values[404:464]))
print("lon coords match source:", np.array_equal(m['lon'].values, src['longitude'].values[559:619]))
a = m.values
print("values unique:", np.unique(a), "total ones:", a.sum())
print("per-day counts on active days:", a[25:35].sum(axis=(1,2)).tolist(), a[65:70].sum(axis=(1,2)).tolist())
print("inactive sample day 40 sum:", a[40].sum(), "day 75 sum:", a[75].sum())
# land cells all zero
sea = np.load('/work/sea.npy').reshape(60,60)
print("land cells all zero:", bool((a[:, ~sea].sum() == 0)))
src.close(); ds.close()
