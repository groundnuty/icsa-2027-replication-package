import numpy as np, xarray as xr, os, datetime, warnings

LOCAL = '/work/data'
# ---- region selection from a reference file ----
ref = xr.open_dataset(f'{LOCAL}/sst_20160601.nc', engine='h5netcdf')
lat_all = ref['latitude'].values.astype('float64')
lon_all = ref['longitude'].values.astype('float64')
latm = (lat_all >= 64.51) & (lat_all <= 65.71)
lonm = (lon_all >= 21.97) & (lon_all <= 23.17)
lat_idx = np.where(latm)[0]; lon_idx = np.where(lonm)[0]
print("lat cells:", lat_idx[0], lat_idx[-1], "n=", len(lat_idx), "range", lat_all[lat_idx][0], lat_all[lat_idx][-1])
print("lon cells:", lon_idx[0], lon_idx[-1], "n=", len(lon_idx), "range", lon_all[lon_idx][0], lon_all[lon_idx][-1])
lat_vals = ref['latitude'].values[lat_idx]   # float32, dataset values
lon_vals = ref['longitude'].values[lon_idx]
varname = 'analysed_sst'
ref.close()
print("grid:", len(lat_idx), "x", len(lon_idx))
