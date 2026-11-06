import numpy as np, fsspec, h5py

fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = fs.open(path, "rb")
with h5py.File(f, "r") as h5:
    tm = h5["time"]
    print("time attrs:", {k: (v if isinstance(v, (bytes, np.ndarray, int, float)) else str(v)) for k, v in tm.attrs.items()})
    for k in ("units", "calendar", "standard_name", "long_name", "axis"):
        if k in tm.attrs:
            print(k, "=", tm.attrs[k])
    t = tm[:]
    print("raw first/last:", t[0], t[-1], t.dtype, t.size)

# decode with actual units
import re
u = tm.attrs["units"].decode() if isinstance(tm.attrs["units"], bytes) else str(tm.attrs["units"])
print("units string:", repr(u))
m = re.match(r"(\w+)\s+since\s+([\d-]+)", u)
unitword, ref = m.group(1), m.group(2)
print("unit:", unitword, "ref:", ref)
ref64 = np.datetime64(ref)
if unitword.lower().startswith("sec"):
    dates = ref64 + t.astype("timedelta64[s]")
else:
    dates = ref64 + t.astype("timedelta64[D]")
print("decoded:", dates[0], dates[-1], dates.size)
assert np.all(np.diff(dates) == np.timedelta64(1, "D"))
print("daily continuous OK")

def di(dstr):
    return int((np.datetime64(dstr) - dates[0]) / np.timedelta64(1, "D"))
for s in ["1991-12-27","1992-01-01","2002-12-31","2003-01-05","2004-06-01","2004-08-31"]:
    print(s, "->", di(s))
np.save("/work/dates.npy", dates)
print("saved dates")
