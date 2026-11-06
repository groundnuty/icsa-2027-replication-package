import numpy as np, xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")
la = ds['latitude'].values; lo = ds['longitude'].values
print("lat shape/range:", la.shape, la.min(), la.max())
w1 = np.where(la >= 61.57 - 1e-9)[0]
w2 = np.where(la <= 62.77 + 1e-9)[0]
print("w1 size:", w1.size, "first:", w1[:3], "w2 size:", w2.size, "last:", w2[-3:])
w3 = np.where((la >= 61.57 - 1e-9) & (la <= 62.77 + 1e-9))[0]
print("combined:", w3.size, w3[:2], w3[-2:])
w4 = np.where(lo >= 20.17 - 1e-9)[0]
w5 = np.where(lo <= 21.37 + 1e-9)[0]
print("lon:", w4.size, w4[:2], w5.size, w5[-2:])
ds.close()
