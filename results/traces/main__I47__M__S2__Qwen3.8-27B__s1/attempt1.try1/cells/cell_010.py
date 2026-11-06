import numpy as np
from datetime import date, timedelta
import calendar

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
def doy_of(m, d):
    return int(cum[m-1] + d)
def md_of_d(d):
    m = int(np.searchsorted(cum, d, side="left"))
    return m, d - cum[m-1]

ok = True
d = 1
for m in range(1, 13):
    for dd in range(1, calendar.monthrange(2000, m)[1] + 1):
        if doy_of(m, dd) != d:
            print("MISMATCH", m, dd, doy_of(m, dd), d); ok = False
        if md_of_d(d) != (m, dd):
            print("MISMATCH2", d, md_of_d(d), (m, dd)); ok = False
        d += 1
print("round-trip over leap year OK:", ok, "final d:", d)
print("doy 2019-06-01:", doy_of(6,1), "doy 2019-08-31:", doy_of(8,31), "doy 1992-02-29:", doy_of(2,29))

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
        if m == 2 and day == 29 and not (y % 4 == 0 and (y % 100 != 0 or y % 400 == 400//400*400 //400*1 and False or y % 400 == 0)):
            continue
        tb = date(y, m, day)
        lo = tb - timedelta(days=5)
        for k in range(11):
            idxs.add(bidx(lo + timedelta(days=k)))
    win_idx[d] = np.array(sorted(idxs), dtype=np.int64)

print("d=1 dates:", [base_dates[i] for i in win_idx[1]])
print("d=366 dates:", [base_dates[i] for i in win_idx[366]])
s59 = [str(base_dates[i]) for i in win_idx[59]]
print("d=59 1992:", [s for s in s59 if s.startswith("1992")])
print("d=59 1993:", [s for s in s59 if s.startswith("1993")])
print("len d=59:", len(win_idx[59]), "len d=61:", len(win_idx[61]),
      "min/max:", min(len(v) for v in win_idx.values()), max(len(v) for v in win_idx.values()))
np.save("work/win_idx.npy", {d: win_idx[d] for d in win_idx}, allow_pickle=True)
print("OK windows built")
