import numpy as np, h5py
from datetime import date, timedelta

base = "/data/icsa2027_data_20261101T090944Z/s1z"
arr = np.load("/work/baseline_region_f32.npy")   # supposedly baseline region, (4028,60,60)
sst_t = np.load("/work/sst_target.npy")          # target region (92,60,60)

with h5py.File(f"{base}/sst_19920615.nc","r") as f:
    lat = f["latitude"][:]; lon = f["longitude"][:]
    sst_full = f["analysed_sst"][0]

lat_idx = np.where((lat >= 62.25-1e-6) & (lat <= 63.45+1e-6))[0]
lon_idx = np.where((lon >= 18.73-1e-6) & (lon <= 19.93+1e-6))[0]
print("region indices: lat", lat_idx[0], "..", lat_idx[-1], " lon", lon_idx[0], "..", lon_idx[-1])
print("region lat values:", lat[lat_idx[0]], lat[lat_idx[-1]], " lon:", lon[lon_idx[0]], lon[lon_idx[-1]])
i0r, i1r = lat_idx[0], lat_idx[-1]+1
j0r, j1r = lon_idx[0], lon_idx[-1]+1

# compare baseline arr on 1992-06-15 (index: 1992-06-15 - 1991-12-27 = 171 days)
k = (date(1992,6,15) - date(1991,12,27)).days
print("k for 1992-06-15:", k)
sub_region = sst_full[i0r:i1r, j0r:j1r]
sub_435 = sst_full[435:495, 485:545]
a = arr[k]
print("baseline_arr == region slice (438..498, 487..547)?", np.array_equal(np.nan_to_num(a), np.nan_to_num(sub_region)))
print("baseline_arr == slice (435..495, 485..545)?", np.array_equal(np.nan_to_num(a), np.nan_to_num(sub_435)))
print("NaN patterns equal: region:", np.array_equal(np.isnan(a), np.isnan(sub_region)),
      " 435slice:", np.array_equal(np.isnan(a), np.isnan(sub_435)))

# target check on 2012-06-15 (target index 14)
with h5py.File(f"{base}/sst_20120615.nc","r") as f:
    sst_t_full = f["analysed_sst"][0]
print("sst_target[14] == region slice?", np.array_equal(np.nan_to_num(sst_t[14]), np.nan_to_num(sst_t_full[i0r:i1r, j0r:j1r])))
print("sst_target[14] == 435slice?", np.array_equal(np.nan_to_num(sst_t[14]), np.nan_to_num(sst_t_full[435:495, 485:545])))
print("land cells baseline arr:", np.isnan(arr[k]).all(axis=0).sum() if False else np.isnan(a).sum(), "region NaNs:", np.isnan(sub_region).sum())
