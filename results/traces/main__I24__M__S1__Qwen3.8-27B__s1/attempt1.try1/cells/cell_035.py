import h5py, numpy as np, datetime as dt, os
BASE = "/data/icsa2027_data_20261101T090944Z/s1z"
epoch_d = dt.date(1981,1,1)
for f in ["sst_20040601.nc","sst_20040701.nc","sst_20040831.nc","sst_20040615.nc"]:
    with h5py.File(os.path.join(BASE,f), "r") as hf:
        tv = hf["time"][()]
        d = epoch_d + dt.timedelta(seconds=float(tv[0]))
    expect = dt.datetime.strptime(f[4:12], "%Y%m%d").date()
    calc = (expect - epoch_d).total_seconds()
    print(f, "raw:", tv[0], "decoded:", d, "match:", abs(tv[0]-calc) < 1e-6 and d == expect)

with h5py.File(os.path.join(BASE,"sst_20040601.nc"), "r") as hf:
    lat = np.array(hf["latitude"][...], dtype=np.float32)
    lon = np.array(hf["longitude"][...], dtype=np.float32)
sel_lat = lat[204:264]; sel_lon = lon[63:123]
print("lat sel:", sel_lat[0], "...", sel_lat[-1], " lon sel:", sel_lon[0], "...", sel_lon[-1])
np.savez("/work/mhw/coords.npz", lat=sel_lat, lon=sel_lon)
print("coords saved")
