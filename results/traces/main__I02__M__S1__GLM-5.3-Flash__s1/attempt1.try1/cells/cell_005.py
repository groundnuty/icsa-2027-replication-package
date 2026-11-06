import xarray as xr, numpy as np
p='/data/icsa2027_data_20261101T090944Z/s1z/sst_20040601.nc'
ds=xr.open_dataset(p, engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
latmask=(lat>=54.17)&(lat<=55.37); lonmask=(lon>=13.25)&(lon<=14.45)
li=np.where(latmask)[0]; lo=np.where(lonmask)[0]
print("lat idx:", li.min(), li.max(), latmask.sum(), lat[li][[0,-1]])
print("lon idx:", lo.min(), lo.max(), lonmask.sum(), lon[lo][[0,-1]])
sub=ds['analysed_sst'].isel(time=0).values[np.ix_(li,lo)]
print("sub shape:", sub.shape, "finite frac:", np.isfinite(sub).mean())
print(sub[:3,:3])
print(sub[-3:,-3:])
