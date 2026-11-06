import h5py, numpy as np
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = h5py.File(path, "r")
lat = f["latitude"][:]; lon = f["longitude"][:]
print(lat[178:188])
print(lon[688:694])
i = np.searchsorted(lat, 57.13, side="left"); j = np.searchsorted(lat, 58.33, side="right")
k = np.searchsorted(lon, 22.79, side="left"); l = np.searchsorted(lon, 23.99, side="right")
print("lat idx", i, j, "lon idx", k, l)
dset = f["analysed_sst"]
blk = dset[100, i:j, k:l]
print("blk nan frac:", np.isnan(blk).mean(), "finite:", np.isfinite(blk).sum())
blk2 = dset[5000, i:j, k:l]
print("day5000 nan frac:", np.isnan(blk2).mean())
