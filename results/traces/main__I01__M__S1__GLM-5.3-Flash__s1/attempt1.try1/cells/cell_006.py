import h5py, xarray as xr, numpy as np, time
ilat0, ilat1 = 32, 91
ilon0, ilon1 = 284, 343
pth = '/data/icsa2027_data_20261101T090944Z/s1z/sst_19920601.nc'
t0=time.time()
for i in range(20):
    with h5py.File(pth,'r') as f:
        a = f['analysed_sst'][0, ilat0:ilat1+1, ilon0:ilon1+1]
print('h5py per-file:', (time.time()-t0)/20)
t0=time.time()
for i in range(20):
    d2 = xr.open_dataset(pth, engine='h5netcdf')
    a = d2['analysed_sst'].isel(time=0, latitude=slice(ilat0,ilat1+1), longitude=slice(ilon0,ilon1+1)).values
    d2.close()
print('xarray per-file:', (time.time()-t0)/20)
