
import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
P='icsa2027_data_20261101T090944Z/s1z/'
ds=xr.open_dataset(fs.open(P+'sst_19820101.nc','rb'),engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
ilat=np.where((lat>=58.69-1e-6)&(lat<=59.89+1e-6))[0]; ilon=np.where((lon>=18.69-1e-6)&(lon<=19.89+1e-6))[0]
print(len(ilat),len(ilon), lat[ilat[[0,-1]]], lon[ilon[[0,-1]]])
t=time.time()
d2=xr.open_dataset(fs.open(P+'sst_20170615.nc','rb'),engine='h5netcdf')
x=d2['analysed_sst'].isel(latitude=ilat,longitude=ilon).values
print(time.time()-t, x.shape, np.isnan(x).sum(), d2.time.values)
