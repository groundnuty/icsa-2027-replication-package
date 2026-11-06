import xarray as xr, numpy as np
lat_vals = np.load('/work/lat_vals.npy'); lon_vals = np.load('/work/lon_vals.npy')
for f in ['sst_19920527.nc', 'sst_19920601.nc', 'sst_19960601.nc']:
    d = xr.open_dataset(f'/work/data/{f}', engine='h5netcdf')
    la = d.latitude.values; lo = d.longitude.values
    print(f, "grid same:", np.array_equal(la, lat_vals), np.array_equal(lo, lon_vals),
          "| lat match:", (la == lat_vals[30]).sum(), "lon match:", (lo == lon_vals[30]).sum())
    d.close()
