
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z'
for name in ['sst_19911227.nc','sst_19920101.nc','sst_20021231.nc','sst_20030105.nc','sst_20140831.nc']:
    with fs.open(f'{base}/{name}','rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        lat = ds['latitude'].values; lon = ds['longitude'].values
        t = ds['time'].values
        print(name, "time:", t, "lat0,1,[-1]:", lat[0], lat[1], lat[-1], "lon0,1,[-1]:", lon[0], lon[1], lon[-1],
              "shape:", ds['analysed_sst'].shape,
              "i region:", np.where((lat>=59.05-1e-4)&(lat<=60.25+1e-4))[0][[0,-1]],
              "j region:", np.where((lon>=21.25-1e-4)&(lon<=22.45+1e-4))[0][[0,-1]])
