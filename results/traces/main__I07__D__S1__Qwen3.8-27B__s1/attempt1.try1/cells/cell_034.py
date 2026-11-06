import xarray as xr, numpy as np
lat_vals = np.load('/work/lat_vals.npy')
d = xr.open_dataset('/work/data/sst_19920601.nc', engine='h5netcdf')
la = d.latitude.values
print("shapes:", la.shape, lat_vals.shape, la.dtype, lat_vals.dtype)
diff = np.where(la != lat_vals)[0]
print("n diff:", len(diff))
if len(diff):
    i = diff[0]
    print("first diff idx", i, repr(la[i]), repr(lat_vals[i]), la[i]-lat_vals[i])
    print(la[i-1:i+2]); print(lat_vals[i-1:i+2])
# check full-grid equality with 2021 file directly
d2 = xr.open_dataset('/work/data/sst_20210601.nc', engine='h5netcdf')
print("1992 vs 2021 lat equal:", np.array_equal(la, d2.latitude.values))
print("lat_vals vs 2021 lat equal:", np.array_equal(lat_vals, d2.latitude.values))
print("saved lat_vals origin check: equal to 1992 lat? diff:", (la != lat_vals).sum())
d.close(); d2.close()
