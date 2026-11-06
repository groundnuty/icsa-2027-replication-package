import numpy as np
bt = np.load("/tmp/base_times.npy")
tgtt = np.load("/tmp/tgt_times.npy")
# ints = days since 1970-01-01 (from datetime64[D].astype(int))
def to_date(n):
    return (np.datetime64("1970-01-01") + np.timedelta64(int(n), "D")).astype(str)
print("base first/last:", to_date(bt[0]), to_date(bt[-1]), "n:", len(bt))
print("contiguous base:", np.all(np.diff(bt) == 1))
print("target first/last:", to_date(tgtt[0]), to_date(tgtt[-1]), "n:", len(tgtt))
print("contiguous target:", np.all(np.diff(tgtt) == 1))
print("target dates:", to_date(tgtt[0]), "...", to_date(tgtt[5]), "...", to_date(tgtt[-1]))
