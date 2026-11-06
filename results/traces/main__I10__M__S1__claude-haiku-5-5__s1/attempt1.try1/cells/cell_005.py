import xarray as xr, numpy as np
D='/data/icsa2027_data_20261101T090944Z/s1z'
ds=xr.open_dataset(D+'/sst_20050615.nc',engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=55.67-1e-6)&(lat<=56.87+1e-6))[0]; lo=np.where((lon>=16.45-1e-6)&(lon<=17.65+1e-6))[0]
print(len(la),len(lo),lat[la[0]],lat[la[-1]],lon[lo[0]],lon[lo[-1]])
sub=ds.analysed_sst.isel(time=0,latitude=la,longitude=lo).values
print(sub.dtype, np.isfinite(sub).mean(), np.nanmin(sub), np.nanmax(sub))
print(ds.analysed_sst.attrs, ds.analysed_sst.encoding)