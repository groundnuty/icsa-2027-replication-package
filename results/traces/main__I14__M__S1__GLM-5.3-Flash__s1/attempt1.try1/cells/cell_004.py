import os, xarray as xr, numpy as np
d = "/data/icsa2027_data_20261101T090944Z/s1z"

# check grid consistency across a few files from different eras
lat_ref = lon_ref = None
for fn in ["sst_19920101.nc", "sst_20020615.nc", "sst_20150601.nc", "sst_20231231.nc"]:
    ds = xr.open_dataset(os.path.join(d, fn), engine="h5netcdf")
    la, lo = ds["latitude"].values, ds["longitude"].values
    if lat_ref is None:
        lat_ref, lon_ref = la, lo
        same = True
    else:
        same = np.array_equal(la, lat_ref) and np.array_equal(lo, lon_ref)
    print(fn, "shape:", ds["analysed_sst"].shape, "grid same as ref:", same,
          "time:", ds["time"].values)
    ds.close()

lat_ref = lat_ref.astype(np.float64); lon_ref = lon_ref.astype(np.float64)
lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91
lat_mask = (lat_ref >= lat_min) & (lat_ref <= lat_max)
lon_mask = (lon_ref >= lon_min) & (lon_ref <= lon_max)
print("\nlat in region:", lat_ref[lat_mask])
print("lon in region:", lon_ref[lon_mask])
print("nlat, nlon:", lat_mask.sum(), lon_mask.sum())
print("lat indices:", np.where(lat_mask)[0])
print("lon indices:", np.where(lon_mask)[0])
