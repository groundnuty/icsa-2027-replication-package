import numpy as np, xarray as xr, h5py, time, os
print('numpy', np.__version__, 'xarray', xr.__version__, 'h5py', h5py.__version__)
import importlib
for m in ['netCDF4','h5netcdf','scipy','pandas']:
    try:
        mod = importlib.import_module(m); print(m, getattr(mod,'__version__','?'))
    except Exception as e:
        print(m, 'MISSING', e)

# contiguity of region indices
p = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20080601.nc'
ds = xr.open_dataset(p, engine='h5netcdf')
lat = ds.latitude.values; lon = ds.longitude.values
ilat = np.where((lat>=54.13)&(lat<=55.33))[0]
ilon = np.where((lon>=14.67)&(lon<=15.87))[0]
print('ilat contiguous:', np.all(np.diff(ilat)==1), ilat[0], ilat[-1])
print('ilon contiguous:', np.all(np.diff(ilon)==1), ilon[0], ilon[-1])
print('lat vals first/last:', lat[ilat[0]], lat[ilat[-1]])
print('lon vals first/last:', lon[ilon[0]], lon[ilon[-1]])

# quick speed test with xarray vs h5py
t0=time.time()
for i in range(20):
    d = f'/data/icsa2027_data_20261101T090944Z/s1z/sst_1992060{i%10:02d}.nc'.replace('19920600','19920601')
t0=time.time()
for i in range(20):
    day = 1 + (i%28)
    pth = f'/data/icsa2027_data_20261101T090944Z/s1z/sst_1992_06_{day:02d}.nc'.replace('_','')
    with h5py.File(pth,'r') as f:
        a = f['analysed_sst'][0, ilat[0]:ilat[-1]+1, ilon[0]:ilon[-1]+1]
print('h5py per-file:', (time.time()-t0)/20)
t0=time.time()
for i in range(20):
    day = 1 + (i%28)
    pth = f'/data/icsa2027_data_20261101T090944Z/s1z/sst_1992_06_{day:02d}.nc'.replace('_','')
    d2 = xr.open_dataset(pth, engine='h5netcdf')
    a = d2['analysed_sst'].isel(time=0, latitude=ilat, longitude=ilon).values
    d2.close()
print('xarray per-file:', (time.time()-t0)/20)
