import numpy as np, fsspec, h5py, re

fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = fs.open(path, "rb")
with h5py.File(f, "r") as h5:
    tm = h5["time"]
    u = tm.attrs["units"]
    u = u.decode() if isinstance(u, bytes) else str(u)
    t = tm[:]

m = re.match(r"(\w+)\s+since\s+([\d\-]+)", u)
unitword, ref = m.group(1), m.group(2)
print("unit:", unitword, "ref:", ref)
ref64 = np.datetime64(ref)
if unitword.lower().startswith("sec"):
    dates = ref64 + t.astype("timedelta64[s]").astype("timedelta64[D]")
else:
    dates = ref64 + t.astype("timedelta64[D]")
print("decoded:", dates[0], dates[-1], dates.size)
assert np.all(np.diff(dates) == np.timedelta64(1, "D"))
print("daily continuous OK")

def di(dstr):
    return int((np.datetime64(dstr) - dates[0]) / np.timedelta64(1, "D"))
for s in ["1991-12-27","1992-01-01","2002-12-31","2003-01-05","2004-06-01","2004-08-31"]:
    print(s, "->", di(s), str(dates[di(s)]))
np.save("/work/dates.npy", dates)
print("saved dates")
