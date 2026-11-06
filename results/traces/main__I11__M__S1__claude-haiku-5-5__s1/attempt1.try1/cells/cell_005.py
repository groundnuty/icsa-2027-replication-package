import xarray as xr, numpy as np
d='/data/icsa2027_data_20261101T090944Z/s1z'
ds=xr.open_dataset(d+'/sst_19820101.nc',engine='h5netcdf')
lat=ds.latitude.values.astype(np.float64); lon=ds.longitude.values.astype(np.float64)
print(lat[:3], np.diff(lat)[:3].mean(), lon[:3], np.diff(lon)[:3].mean(), len(lat), len(lon))
li=np.where((lat>=55.67-1e-6)&(lat<=56.87+1e-6))[0]; lo=np.where((lon>=16.45-1e-6)&(lon<=17.65+1e-6))[0]
print(li[[0,-1]], lat[li[[0,-1]]], len(li)); print(lo[[0,-1]], lon[lo[[0,-1]]], len(lo))
print(ds.analysed_sst.encoding)
v=ds.analysed_sst.isel(time=0).values[np.ix_(li,lo)]; print(np.isnan(v).sum(), v.size, np.nanmin(v), np.nanmax(v))