import h5py, numpy as np, datetime as dt, os
BASE = "/data/icsa2027_data_20261101T090944Z/s1z"
epoch = dt.datetime(1981,1,1)
# verify raw time encoding on a few target files
for f in ["sst_20040601.nc","sst_20040701.nc","sst_20040831.nc","sst_20040615.nc"]:
    with h5py.File(os.path.join(BASE,f), "r") as hf:
        tv = hf["time"][()]
        d = (epoch + dt.timedelta(seconds=float(tv[0]))).date()
    expect = dt.datetime.strptime(f[4:12], "%Y%m%d").date()
    calc = (expect - epoch).total_seconds()
    print(f, "raw:", tv[0], "decoded:", d, "calc:", calc, "match:", abs(tv[0]-calc) < 1e-6)

# get lat/lon full arrays
with h5py.File(os.path.join(BASE,"sst_20040601.nc"), "r") as hf:
    lat = np.array(hf["latitude"][...], dtype=np.float32)
    lon = np.array(hf["longitude"][...], dtype=np.float32)
print("lat shape", lat.shape, "lon shape", lon.shape)
sel_lat = lat[204:264]; sel_lon = lon[63:123]
print("lat sel first/last:", sel_lat[0], sel_lat[-1])
print("lon sel first/last:", sel_lon[0], sel_lon[-1])
np.save("/work/mhw/coords.npy", {"lat": sel_lat, "lon": sel_lon})
print("coords saved")
