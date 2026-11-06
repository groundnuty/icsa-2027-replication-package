import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

ref_lat = ref_lon = None
for nm in ['sst_19820101.nc','sst_19920229.nc','sst_20030105.nc','sst_20130831.nc']:
    with fs.open(f'{base}/{nm}','rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        lat = ds.latitude.values.astype('float64'); lon = ds.longitude.values.astype('float64')
        t = ds.time.values
        if ref_lat is None:
            ref_lat, ref_lon = ds.latitude.values, ds.longitude.values
        else:
            print(nm, "lat identical:", np.array_equal(ref_lat, ds.latitude.values),
                  "lon identical:", np.array_equal(ref_lon, ds.longitude.values))
        print(nm, "time:", t)
        ds.close()

lat = ref_lat.astype('float64'); lon = ref_lon.astype('float64')
print("lat dtype:", ref_lat.dtype)
# region selection
latmin, latmax, lonmin, lonmax = 57.85, 59.05, 21.01, 22.21
lat_idx = np.where((lat >= latmin - 1e-9) & (lat <= latmax + 1e-9))[0]
lon_idx = np.where((lon >= lonmin - 1e-9) & (lon <= lonmax + 1e-9))[0]
print("lat idx:", lat_idx[0], lat_idx[-1], "n=", len(lat_idx))
print("lon idx:", lon_idx[0], lon_idx[-1], "n=", len(lon_idx))
print("lat values first/last:", lat[lat_idx[0]], lat[lat_idx[-1]])
print("lon values first/last:", lon[lon_idx[0]], lon[lon_idx[-1]])
print("lat steps unique-ish:", np.unique(np.round(np.diff(lat[lat_idx]),10))[:5])
print("n cells:", len(lat_idx)*len(lon_idx))
