import h5py, numpy as np
f = h5py.File("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", "r")
tt = f["time"]
print("time dtype:", tt.dtype, "attrs:", {k: v for k, v in tt.attrs.items() if k != "DIMENSION_LIST"})
print("first vals:", tt[:5], "around 2014-06-01:", tt[11878:11882])
lat = f["latitude"]; lon = f["longitude"]
print("lat dtype:", lat.dtype, "attrs:", dict(lat.attrs))
print("lon dtype:", lon.dtype, "attrs:", dict(lon.attrs))
f.close()
