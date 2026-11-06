import numpy as np
from datetime import date, timedelta

z = np.load("work/sst.npz", allow_pickle=False)
base_dates = z["base_dates"].astype("datetime64[D]")
tgt_dates = z["tgt_dates"].astype("datetime64[D]")
base32 = z["base_arr"]           # (4028,60,60) float32
tgt32 = z["tgt_arr"]             # (92,60,60) float32
lat = z["lat"]
lon = z["lon"]
print("loaded", base32.shape, tgt32.shape)

base64 = base32.astype(np.float64)
tgt64 = tgt32.astype(np.float64)

# --- 1. sea cells: finite on every target day ---
finite_all = np.all(np.isfinite(tgt64), axis=0)   # (60,60)
n_sea = int(finite_all.sum())
print("sea cells:", n_sea, "of", finite_all.size)
sea_idx = np.where(finite_all.ravel())[0]         # cell indices

# --- 2. day-of-year mapping (by month/day, leap calendar: Feb 29 = 60) ---
cum = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366])  # end-of-month doy in leap year
def doy_of(y, m, d):
    return int(cum[m-1] + d)
def md_of_d(d):  # d in 1..366 -> (month, day) in leap calendar
    m = int(np.searchsorted(cum, d, side="right"))  # cum[m-1] < d <= cum[m]
    day = d - cum[m-1]
    return m, day

# map every date to its index in base_dates (1991-12-27..2003-01-05)
base_set = {d: i for i, d in enumerate(base_dates)}
def bidx(dt):  # dt: python date
    return base_set[np.datetime64(dt.strftime("%Y-%m-%d"))]

# sanity on mapping
assert doy_of(2000,2,29) == 60 and md_of_d(60) == (2,29)
assert md_of_d(59) == (2,28) and md_of_d(61) == (3,1)
assert doy_of(1995,1,1) == 1 and doy_of(2019,12,31) == 366

# --- window date index lists per day of year d (d != 60) ---
win_idx = {}
for d in range(1, 367):
    if d == 60:
        continue
    m, day = md_of_d(d)
    idxs = set()
    for y in range(1992, 2003):
        if m == 2 and day == 29:
            # only leap years have it as a baseline date
            if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) is False:
                continue
        tb = date(y, m, day)
        lo = tb - timedelta(days=5)
        hi = tb + timedelta(days=5)
        for k in range(11):
            dt = lo + timedelta(days=k)
            idxs.add(bidx(dt))
    win_idx[d] = np.array(sorted(idxs), dtype=np.int64)
    if d in (1, 59, 61, 366):
        print(f"d={d}: n_pool_dates={len(win_idx[d])}, span {base_dates[win_idx[d][0]]} .. {base_dates[win_idx[d][-1]]}")

# pool for d=1 should be 1991-12-27..1992-01-06 (11 dates) and d=366: 2002-12-26..2003-01-05
print("d=1 first dates:", [base_dates[i] for i in win_idx[1][:11]])
print("d=366 first dates:", [base_dates[i] for i in win_idx[366][:11]])
np.save("work/win_idx.npy", {d: win_idx[d] for d in win_idx}, allow_pickle=True)
print("window sizes: min", min(len(v) for v in win_idx.values()), "max", max(len(v) for v in win_idx.values()))
