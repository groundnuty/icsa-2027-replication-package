import os, h5py, numpy as np, time, json
print("cwd:", os.getcwd(), "| writable:", os.access(os.getcwd(), os.W_OK))
os.makedirs("cache", exist_ok=True); os.makedirs("output", exist_ok=True)
print("made cache/ and output/ ok")

p = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc"
with h5py.File(p, "r") as f:
    t = f["time"]
    print("time attrs:", dict(t.attrs))
    print("time value:", t[0], t.dtype)
    lat = f["latitude"]; lon = f["longitude"]
    print("lat attrs:", dict(lat.attrs)); print("lon attrs:", dict(lon.attrs))
    sl = f["analysed_sst"][0, 218:278, 601:661]
fin = sl[np.isfinite(sl)]
print("region slice finite stats: n=", fin.size, "min/max:", fin.min(), fin.max(), "mean:", fin.mean())
print("nan count:", int(np.isnan(sl).sum()), "of", sl.size)
