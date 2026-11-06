import xarray as xr, numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print("units:", ds['analysed_sst'].attrs)
print("enc:", ds['analysed_sst'].encoding)
lat = ds['latitude'].values; lon = ds['longitude'].values
print("lat range", lat.min(), lat.max(), "lon range", lon.min(), lon.max())
dlat = np.diff(lat); dlon = np.diff(lon)
print("dlat uniq", np.unique(dlat), "dlon uniq", np.unique(dlon))
t = ds['time'].values
print("time first/last:", t[0], t[-1])
diffs = np.unique(np.diff(t).astype('timedelta64[D]').astype(int))
print("day gaps:", diffs)
i = np.where((lat >= 62.25) & (lat <= 63.45))[0]
j = np.where((lon >= 18.73) & (lon <= 19.93))[0]
print("lat idx", i.min(), i.max(), "n=", i.size, "lat vals", lat[i].min(), lat[i].max())
print("lon idx", j.min(), j.max(), "n=", j.size, "lon vals", lon[j].min(), lon[j].max())
print("lat within region:", lat[i][[0,-1]])
print("lon within region:", lon[j][[0,-1]])
print("total cells:", i.size*j.size)
