import xarray as xr, numpy as np, glob
d='/data/icsa2027_data_20261101T090944Z/s1z'
ds=xr.open_dataset(f'{d}/sst_19820101.nc',engine='h5netcdf')
print(ds)
for v in ds.variables: print(v, ds[v].attrs)
fs=sorted(os.listdir(d)); print(fs[0],fs[-1],len(fs)); print([f for f in fs if not f.startswith('sst_')][:10])