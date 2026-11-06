import time, fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
latmin, latmax, lonmin, lonmax = 57.85, 59.05, 21.01, 22.21

with fs.open(f'{base}/sst_20130601.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds.latitude.values.astype('float64'); lon = ds.longitude.values.astype('float64')
    ds.close()
li = np.where((lat>=latmin-1e-9)&(lat<=latmax+1e-9))[0]
oi = np.where((lon>=lonmin-1e-9)&(lon<=lonmax+1e-9))[0]

# breakdown: fs.open + xarray parse vs data read
names = [f'sst_199207{d:02d}.nc' for d in range(1,16)]
topen=tload=0.0
for nm in names:
    a0=time.time()
    f = fs.open(f'{base}/{nm}','rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    a1=time.time()
    v = ds.analysed_sst.isel(time=0, latitude=li, longitude=oi).values.astype('float64')
    a2=time.time()
    ds.close(); f.close()
    topen += a1-a0; tload += a2-a1
print(f"open+meta: {topen/len(names)*1000:.0f} ms/file, data: {tload/len(names)*1000:.0f} ms/file")

# larger batch stability test: 200 files
t0=time.time()
for i,nm in enumerate([f'sst_19920{m}{d:02d}.nc' for m in (8,9) for d in range(1,31)]):
    with fs.open(f'{base}/{nm}','rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        v = ds.analysed_sst.isel(time=0, latitude=li, longitude=oi).values.astype('float64')
        ds.close()
print(f"200 files in {time.time()-t0:.1f}s -> {200/(time.time()-t0):.2f} files/s")
