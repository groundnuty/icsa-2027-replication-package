import numpy as np, h5py
D='/data/icsa2027_data_20261101T090944Z/s1z'
p=f'{D}/sst_19920601.nc'
for k in range(5):
    with h5py.File(p,'r') as f:
        a=f['analysed_sst'][0]
    print(k, a[40,40], a[45,45], np.isfinite(a).sum())
# also with xarray
import xarray as xr
for k in range(2):
    ds=xr.open_dataset(p, engine='h5netcdf')
    v=ds['analysed_sst'].isel(time=0).values
    ds.close()
    print("xr", k, v[40,40], v[45,45], np.isfinite(v).sum())
# via netCDF4
import netCDF4
nc=netCDF4.Dataset(p)
v=nc.variables['analysed_sst'][0]
print("nc4", v[40,40], v[45,45], np.isfinite(np.asarray(v)).sum())
nc.close()
