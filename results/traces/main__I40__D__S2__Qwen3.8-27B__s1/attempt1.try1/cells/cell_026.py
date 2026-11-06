import h5py, numpy as np, xarray as xr, datetime
ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")
t = ds['time'].values
i = int((t == np.datetime64('1992-07-01'))[0])
print("xarray idx of 1992-07-01:", i)
ax = ds['analysed_sst'].isel(time=i).values
f = h5py.File('/work/sst_s2.nc','r')
ah = np.asarray(f['analysed_sst'][i])
print("shapes:", ax.shape, ah.shape)
neq = (ax != ah) & (np.isfinite(ax) | np.isfinite(ah))
print("xarray vs h5py same index: n diff =", neq.sum())
# also check 3652
ax2 = ds['analysed_sst'].isel(time=3652).values
ah2 = np.asarray(f['analysed_sst'][3652])
neq2 = (ax2 != ah2) & (np.isfinite(ax2) | np.isfinite(ah2))
print("idx 3652: n diff =", neq2.sum())
# now xarray 1992-01-01 vs 1992-07-01
a1 = ds['analysed_sst'].isel(time=int((t == np.datetime64('1992-01-01'))[0])).values
a2 = ds['analysed_sst'].isel(time=i).values
n = (a1 != a2) & (np.isfinite(a1) | np.isfinite(a2))
print("xarray 1992-01-01 vs 1992-07-01 n diff:", n.sum())
print("t[3652]:", t[3652], " t[3834]:", t[3834])
ds.close(); f.close()
