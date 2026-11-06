
import fsspec, os, numpy as np, xarray as xr
os.makedirs('/work/output',exist_ok=True)
print(os.path.exists('/work/sst_s2.nc'), os.path.getsize('/work/sst_s2.nc') if os.path.exists('/work/sst_s2.nc') else None)
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds.analysed_sst.attrs)
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=63.31-1e-6)&(lat<=64.51+1e-6))[0]; lo=np.where((lon>=21.31-1e-6)&(lon<=22.51+1e-6))[0]
print(lat[la[0]],lat[la[-1]],len(la),lon[lo[0]],lon[lo[-1]],len(lo))
sub=ds.analysed_sst.sel(time=slice('1991-12-27','2009-08-31')).isel(latitude=la,longitude=lo).load()
print(sub.shape, float(sub.min()), float(sub.max()))
print(np.isnan(sub.values).mean())
