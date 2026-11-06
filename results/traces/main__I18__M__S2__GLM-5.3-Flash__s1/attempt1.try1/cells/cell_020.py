import os, json, warnings
import numpy as np
import h5py

print("cwd:", os.getcwd())
os.makedirs("output", exist_ok=True)

PATH = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
EPOCH = np.datetime64("1970-01-01")

with h5py.File(PATH, "r") as f:
    times = EPOCH + f["time"][:].astype("timedelta64[s]")
    lat = f["latitude"][:].astype(np.float32)
    lon = f["longitude"][:].astype(np.float32)
    i0b = np.searchsorted(times, np.datetime64("1991-12-27"))
    i1b = np.searchsorted(times, np.datetime64("2003-01-05"), side="right")
    i0t = np.searchsorted(times, np.datetime64("2010-06-01"))
    i1t = np.searchsorted(times, np.datetime64("2010-08-31"), side="right")
    base = f["analysed_sst"][i0b:i1b, 180:240, 690:750].astype(np.float64)
    tgt  = f["analysed_sst"][i0t:i1t, 180:240, 690:750].astype(np.float64)

print("base", base.shape, "tgt", tgt.shape)
print("base matches intermediate:", np.array_equal(base, np.load("/tmp/base.npy"), equal_nan=True))
print("tgt matches intermediate:", np.array_equal(tgt, np.load("/tmp/tgt.npy"), equal_nan=True))
assert np.array_equal(base, np.load("/tmp/base.npy"), equal_nan=True)
assert np.array_equal(tgt, np.load("/tmp/tgt.npy"), equal_nan=True)
