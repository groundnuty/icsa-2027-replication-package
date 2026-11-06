import numpy as np

PREF = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
def doy(dates):
    dates = dates.astype("datetime64[D]")
    d = dates.astype("int64")
    first = dates.astype("datetime64[M]").astype("datetime64[D]").astype("int64")
    day = d - first + 1
    month = dates.astype("datetime64[M]").astype("int64") % 12
    return PREF[month] + day

cand = np.datetime64("1991-12-27") + np.arange(4028)
b_start = np.datetime64("1992-01-01"); b_end = np.datetime64("2002-12-31")

k = int(np.searchsorted(cand, np.datetime64("1992-03-01")))
print("cand[k] =", cand[k])
got = set()
for o in range(-5, 6):
    b = cand[k] + np.timedelta64(o, "D")
    if b_start <= b <= b_end:
        got.add(int(doy(b)))
print("expected pools for 1992-03-01:", sorted(got))

# now replicate the vectorized loop exactly for all k, compare
Mtest = np.zeros((366, len(cand)), dtype=bool)
for o in range(-5, 6):
    b = cand + np.timedelta64(o, "D")
    within = (b >= b_start) & (b <= b_end)
    kx = np.where(within)[0]
    Mtest[doy(b)[kx] - 1, kx] = True
got2 = sorted(np.where(Mtest[:, k])[0] + 1)
print("vectorized pools for 1992-03-01:", got2)

# check the o=-5 iteration value at k
b = cand + np.timedelta64(-5, "D")
print("b[k] =", b[k], "doy(b)[k] =", doy(b)[k], "within:", bool(b[k] >= b_start and b[k] <= b_end))
