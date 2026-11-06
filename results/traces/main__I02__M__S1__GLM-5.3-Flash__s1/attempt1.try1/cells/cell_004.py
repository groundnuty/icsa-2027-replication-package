import xarray as xr, numpy as np
p='/data/icsa2027_data_20261101T090944Z/s1z/sst_20040601.nc'
ds=xr.open_dataset(p, engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
print(lat.dtype, lon.dtype, lat[:3], lat[-3:], lon[:3], lon[-3:])
dlat=np.diff(lat); dlon=np.diff(lon)
print("dlat uniq:", np.unique(np.round(dlat,6)), "dlon uniq:", np.unique(np.round(dlon,6)))
sst=ds['analysed_sst']
print("encoding:", {k:v for k,v in sst.encoding.items()})
print("attrs:", sst.attrs)
region=(lat>=54.17)&(lat<=55.37)&(lon>=13.25)&(lon<=14.45)
latmask=(lat>=54.17)&(lat<=55.37); lonmask=(lon>=13.25)&(lon<=14.45)
print("lat idx:", np.where(latmask)[0].min(), np.where(latmask)[0].max(), latmask.sum())
print("lon idx:", np.where(lonmask)[0].min(), np.where(lonmask)[0].max(), lonmask.sum())
sub=sst.isel(time=0)[np.ix_(latmask,lonmask)]
a=sub.values
print("sub shape:", a.shape, "finite frac:", np.isfinite(a).mean())
import numpy as np
print("sample row0:", a[0,:5])
