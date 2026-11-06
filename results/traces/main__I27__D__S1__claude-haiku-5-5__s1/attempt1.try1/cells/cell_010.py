import xarray as xr, numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds.analysed_sst.encoding)
lat=ds.latitude.values; lon=ds.longitude.values
print(lat[:3], np.diff(lat)[:3].round(6), lon[:3])
ilat=np.where((lat>=57.83-1e-6)&(lat<=59.03+1e-6))[0]
ilon=np.where((lon>=17.41-1e-6)&(lon<=18.61+1e-6))[0]
print(len(ilat), len(ilon), lat[ilat][[0,-1]], lon[ilon][[0,-1]])
print(ds.analysed_sst.attrs)