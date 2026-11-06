import numpy as np, os, json, datetime as dt

os.makedirs("/tmp/mhw", exist_ok=True)

def daterange(d0, d1):
    d = d0
    out = []
    while d <= d1:
        out.append(d)
        d += dt.timedelta(days=1)
    return out

base_win = daterange(dt.date(1991,12,27), dt.date(2003,1,5))
target   = daterange(dt.date(2009,6,1), dt.date(2009,8,31))
print(len(base_win), base_win[0], base_win[-1])
print(len(target), target[0], target[-1])

NC = 60*60
nb = np.memmap("/tmp/mhw/baseline.npy", dtype=np.float64, mode="w+", shape=(len(base_win), NC))
nt = np.memmap("/tmp/mhw/target.npy",   dtype=np.float64, mode="w+", shape=(len(target), NC))
del nb, nt
json.dump({"base_win":[str(d) for d in base_win], "target":[str(d) for d in target]},
          open("/tmp/mhw/dates.json","w"))
# also save lat/lon coordinate values for the region (float32 as in dataset)
import h5py
f = h5py.File("/data/icsa2027_data_20261101T090944Z/s1z/sst_20090601.nc","r")
lat = f["latitude"][322:382][:]; lon = f["longitude"][485:545][:]
f.close()
np.save("/tmp/mhw/lat.npy", lat); np.save("/tmp/mhw/lon.npy", lon)
print(lat[0], lat[-1], lon[0], lon[-1])
print("ok")
