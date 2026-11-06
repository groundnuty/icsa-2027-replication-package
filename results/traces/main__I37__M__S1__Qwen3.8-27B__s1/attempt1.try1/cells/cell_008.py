import h5py, time, numpy as np, xarray as xr
base = "/data/icsa2027_data_20261101T090944Z/s1z"
p = f"{base}/sst_20120701.nc"

f = h5py.File(p, "r")
v = f['analysed_sst']
a_hyp = v[0, 330:390, 551:611]
a_full = v[0][:][330:390, 551:611]
a_hyp2 = v[:, 330:390, 551:611][0]
print("hyp vs full:", np.array_equal(a_hyp, a_full))
print("hyp2 vs full:", np.array_equal(a_hyp2, a_full))
print("allclose:", np.allclose(a_hyp, a_full, equal_nan=True))
diff = np.where(~np.isclose(a_hyp, a_full, equal_nan=True))[0]
print("num diff:", len(diff))
if len(diff):
    i, j = divmod(int(diff[0]), 60)
    print("example", i, j, a_hyp[i,j], a_full[i,j])
f.close()

ds = xr.open_dataset(p, engine="h5netcdf", decode_times=False)
a_xr = ds['analysed_sst'].sel(latitude=slice(60.09,61.29), longitude=slice(20.01,21.21)).values[0]
print("xr dtype", a_xr.dtype)
print("xr vs full:", np.array_equal(a_xr, a_full))
print("xr vs hyp:", np.array_equal(a_xr, a_hyp))
ds.close()
