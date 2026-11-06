import numpy as np
from datetime import date, timedelta

z = np.load("work/sst.npz", allow_pickle=False)
base_dates = z["base_dates"].astype("datetime64[D]")
tgt_dates = z["tgt_dates"].astype("datetime64[D]")
base64 = z["base_arr"].astype(np.float64)
tgt64 = z["tgt_arr"].astype(np.float64)
lat = z["lat"]; lon = z["lon"]

finite_all = np.all(np.isfinite(tgt64), axis=0)
n_sea = int(finite_all.sum())
print("sea cells:", n_sea, "of", finite_all.size)
sea_idx = np.where(finite_all.ravel())[0]

cum = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366])
def doy_of(y, m, d):
    return int(cum[m-1] + d)
def md_of_d(d):
    m = int(np.searchsorted(cum, d, side="left"))
    return m, d - cum[m-1]

assert md_of_d(60) == (2,29) and md_of_d(59) == (2,28) and md_of_d(61) == (3,1)
assert md_of_d(1) == (1,1) and md_of_d(366) == (12,31) and md_of_d(31) == (1,31) and md_of_d(32) == (2,1)
assert doy_of(2000,2,29) == 60 and doy_of(1995,12,31) == 366 and doy_of(2019,6,1) == 152

base_set = {d: i for i, d in enumerate(base_dates)}
def bidx(dt):
    return base_set[np.datetime64(dt.strftime("%Y-%m-%d"))]

win_idx = {}
for d in range(1, 367):
    if d == 60:
        continue
    m, day = md_of_d(d)
    idxs = set()
    for y in range(1992, 2003):
        if m == 2 and day == 29 and not (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)):
            continue
        tb = date(y, m, day)
        lo = tb - timedelta(days=5)
        for k in range(11):
            idxs.add(bidx(lo + timedelta(days=k)))
    win_idx[d] = np.array(sorted(idxs), dtype=np.int64)

print("d=1 dates:", [base_dates[i] for i in win_idx[1]])
print("d=59 dates (1992 leap):", [base_dates[i] for i in win_idx[59][:22]])
print("d=61 dates (1992 leap):", [base_dates[i] for i in win_idx[61][:22]])
print("d=366 dates:", [base_dates[i] for i in win_idx[366]])
print("pool sizes min/max:", min(len(v) for v in win_idx.values()), max(len(v) for v in win_idx.values()))
# non-leap d=59: 1993-02-23..1993-03-05 should NOT contain 1993-02-29 (doesn't exist)
sub = [base_dates[i] for i in win_idx[59]]
print("1993 in d59:", [s for s in sub if s.startswith("1993")])
# leap d=59 (1992): 1992-02-23..1992-03-05 includes 1992-02-29
sub92 = [base_dates[i] for i in win_idx[59]]
print("1992 in d59:", [s for s in sub92 if s.startswith("1992")])
np.save("work/win_idx.npy", {d: win_idx[d] for d in win_idx}, allow_pickle=True)
