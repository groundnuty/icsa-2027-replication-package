import os, glob, numpy as np, xarray as xr, datetime
fl=sorted(glob.glob('/work/sst/sst_*.nc'))
ds=xr.open_dataset(fl[0],engine='h5netcdf')
lat=ds.latitude.values.astype(np.float64); lon=ds.longitude.values.astype(np.float64)
li=np.where((lat>=59.05-1e-6)&(lat<=60.25+1e-6))[0]; lo=np.where((lon>=21.25-1e-6)&(lon<=22.45+1e-6))[0]
print(len(li),lat[li[0]],lat[li[-1]],len(lo),lon[lo[0]],lon[lo[-1]])
print(ds.analysed_sst.dtype, ds.analysed_sst.attrs.get('_FillValue'), ds.analysed_sst.encoding)
print(np.diff(lat)[:3], np.diff(lon)[:3])