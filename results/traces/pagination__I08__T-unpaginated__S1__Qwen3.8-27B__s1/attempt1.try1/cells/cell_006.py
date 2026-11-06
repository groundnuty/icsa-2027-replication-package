
import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z'

# time several sliced reads
t0 = time.time()
for name in ['sst_19920101.nc', 'sst_19960229.nc', 'sst_20021231.nc', 'sst_20030105.nc', 'sst_19911227.nc', 'sst_20070715.nc']:
    with fs.open(base + '/' + name, "rb") as f:
        ds = xr.open_dataset(f, engine="h5netcdf")
        v = ds['analysed_sst'].isel(latitude=slice(66,126), longitude=slice(531,591)).values
        ds.close()
    print(name, v.shape, np.isfinite(v).mean())
print("total time for 6 sliced reads:", round(time.time()-t0, 2), "s")

# count files in directory (sample: list all and count)
names = fs.ls(base, detail=False)
print("total files:", len(names))
print("first:", names[0].split('/')[-1], "last:", names[-1].split('/')[-1])
