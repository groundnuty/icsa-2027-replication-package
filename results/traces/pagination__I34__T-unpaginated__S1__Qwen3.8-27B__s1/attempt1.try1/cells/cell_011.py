import numpy as np, datetime
from collections import Counter

b_dates = np.load("/tmp/mhw/baseline_dates.npy")
cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366]
def doy_of(d):
    return cum[d.month - 1] + d.day

base_start = datetime.date(1992, 1, 1).toordinal()
base_end = datetime.date(2002, 12, 31).toordinal()

S = []
for o in b_dates:
    lo = max(int(o) - 5, base_start)
    hi = min(int(o) + 5, base_end)
    doys = set()
    for so in range(lo, hi + 1):
        d = doy_of(datetime.date.fromordinal(so))
        if d != 60:  # day 60 has no pool of its own; Feb29 samples enter neighbours' pools
            doys.add(d)
    S.append(sorted(doys))

idx_by_doy = {d: [] for d in range(1, 367) if d != 60}
for i, s in enumerate(S):
    for d in s:
        idx_by_doy[d].append(i)
sizes = {d: len(v) for d, v in idx_by_doy.items()}
print("pool size distribution:", Counter(sizes.values()))
print("doy 1:", sizes[1], "doy 59:", sizes[59], "doy 61:", sizes[61], "doy 153:", sizes[153], "doy 244:", sizes[244])

# verify doy 1 first/last dates
v1 = idx_by_doy[1]
print("doy1 first:", [str(datetime.date.fromordinal(int(b_dates[i]))) for i in v1[:9]])
print("doy1 last:", [str(datetime.date.fromordinal(int(b_dates[i]))) for i in v1[-5:]])

# verify doy 59 includes Feb 29 samples (leap years 1992,1996,2000)
v59 = [int(b_dates[i]) for i in idx_by_doy[59]]
f29 = [o for o in v59 if datetime.date.fromordinal(o).month == 2 and datetime.date.fromordinal(o).day == 29]
print("doy59 pool Feb29 ordinals:", [str(datetime.date.fromordinal(o)) for o in f29])
# verify a Feb29 sample's full pool membership: 1996-02-29
o = datetime.date(1996, 2, 29).toordinal()
i = int(np.where(b_dates == o)[0][0])
print("1996-02-29 belongs to pools:", S[i])

np.save("/tmp/mhw/idx_by_doy.npy", np.array([idx_by_doy[d] for d in range(1, 367) if d != 60], dtype=object), allow_pickle=True)
print("saved idx_by_doy")
