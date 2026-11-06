import fsspec, h5py, numpy as np, time, xarray as xr
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# raw structure
with fs.open(f'{base}/sst_20120601.nc','rb') as f:
    with h5py.File(f,'r') as h:
        def show(name, obj):
            if isinstance(obj, h5py.Dataset):
                print(name, obj.shape, obj.dtype, dict(obj.attrs))
        h.visititems(show)
        print("time raw:", h['time'][:], h['time'].dtype)

# timing: xarray vs h5py read of subset
lat0,lat1,lon0,lon1 = 48,108,353,413
t0=time.time()
for i in range(5):
    with fs.open(f'{base}/sst_199206{i+1:02d}.nc','rb') as f:
        with xr.open_dataset(f, engine='h5netcdf') as ds:
            v = ds['analysed_sst'].isel(time=0, latitude=slice(lat0,lat1), longitude=slice(lon0,lon1)).values
print("xarray per-file sec:", (time.time()-t0)/5)
t0=time.time()
for i in range(5):
    with fs.open(f'{base}/sst_199206{i+1:02d}.nc','rb') as f:
        with h5py.File(f,'r') as h:
            v = h['analysed_sst'][0, lat0:lat1, lon0:lon1]
            tt = h['time'][0]
print("h5py per-file sec:", (time.time()-t0)/5)
print(v.shape, v.dtype, np.isfinite(v).mean())
