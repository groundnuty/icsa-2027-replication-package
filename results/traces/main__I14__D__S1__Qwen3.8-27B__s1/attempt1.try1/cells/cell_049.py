import numpy as np, netCDF4, xarray as xr
nc = netCDF4.Dataset('/work/data/sst_s2.nc', 'r')
a = nc['analysed_sst']
print("netCDF4 var attrs:")
for k, v in a.__dict__.items():
    print("  ", k, "=", v)
i = 12231  # 2015-07-06 (12204 + 35)
print("netCDF4 2015-07-06 @ (250,440):", a[i, 250, 440], " @ (330,500):", a[i, 330, 500])
# region cell 3299: lat 57.32, lon 18.90 -> find SITE_G,FC
lat_all = nc['latitude'][:]; lon_all = nc['longitude'][:]
SITE_G = int(np.searchsorted(lat_all, 57.32)); FC = int(np.searchsorted(lon_all, 18.90))
print("SITE_G,FC:", SITE_G, FC, lat_all[SITE_G], lon_all[FC])
print("netCDF4 2015-07-06 @ region corner:", a[i, SITE_G, FC])
nc.close()

ds = xr.open_dataset('/work/data/sst_s2.nc', engine="h5netcdf")
v = ds['analysed_sst']
print("xarray var attrs:")
for k, val in v.attrs.items():
    print("  ", k, "=", val)
print("xarray 2015-07-06 @ (250,440):", v.isel(time=i).values[250, 440], " @ (330,500):", v.isel(time=i).values[330, 500])
print("xarray 2015-07-06 @ region corner:", v.isel(time=i, latitude=SITE_G, longitude=FC).values)
ds.close()