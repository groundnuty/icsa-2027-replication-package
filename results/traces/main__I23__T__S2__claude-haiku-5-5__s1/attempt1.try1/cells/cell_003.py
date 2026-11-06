
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds = xr.open_dataset(f, engine='h5netcdf')
v=ds.analysed_sst
print(v.attrs, v.encoding.get('dtype'), v.encoding.get('_FillValue'), v.encoding.get('scale_factor'))
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=57.41-1e-6)&(lat<=58.61+1e-6))[0]; lo=np.where((lon>=18.69-1e-6)&(lon<=19.89+1e-6))[0]
print(lat[la[0]],lat[la[-1]],len(la), lon[lo[0]],lon[lo[-1]],len(lo))
