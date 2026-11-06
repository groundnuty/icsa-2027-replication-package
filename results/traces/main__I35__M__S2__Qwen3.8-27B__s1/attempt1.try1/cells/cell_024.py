import numpy as np

PREF = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
def doy(dates):
    dates = dates.astype("datetime64[D]")
    d = dates.astype("int64")
    first = dates.astype("datetime64[M]").astype("datetime64[D]").astype("int64")
    day = d - first + 1
    month = dates.astype("datetime64[M]").astype("int64") % 12
    return PREF[month] + day

p3 = np.load("/tmp/p3.npy"); sea = np.load("/tmp/sea.npy")
thr_s = np.load("/tmp/thr_s.npy"); mhw = np.load("/tmp/mhw.npy").astype(bool)
tdates = np.datetime64("2009-06-01") + np.arange(92)
tdoy = doy(tdates)
SST_t = p3[:, sea]
hot = SST_t >= thr_s[tdoy - 1]

def cell_mhw(hot):
    nt = len(hot)
    hpad = np.array([False] + list(hot) + [False])
    d = np.diff(hpad.astype(np.int8))
    starts = np.where(d == 1)[0]; ends = np.where(d == -1)[0] - 1
    runs = [(s, e) for s, e in zip(starts, ends) if e - s + 1 >= 5]
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2: merged[-1][1] = e
        else: merged.append([s, e])
    out = np.zeros(nt, bool)
    for s, e in merged: out[s:e+1] = True
    return out

# corrected expectations
cases = [
    ("5 hot gap2 5 hot", [True]*5 + [False]*2 + [True]*5 + [False]*82, [(0,11)]),
    ("5 hot gap3 5 hot", [True]*5 + [False]*3 + [True]*5 + [False]*82, [(0,4),(8,12)]),
    ("4 hot only", [True]*4 + [False]*88, []),
    ("5-1-4-1-5", [True]*5+[False]+[True]*4+[False]+[True]*5+[False]*77, [(0,4),(11,15)]),
    ("6 hot gap2 6 hot gap2 6 hot", [True]*6+[False]*2+[True]*6+[False]*2+[True]*6+[False]*72, [(0,21)]),
]
ok = True
for name, hotr, exp_runs in cases:
    got = cell_mhw(np.array(hotr, bool))
    exp = np.zeros(92, bool)
    for s, e in exp_runs: exp[s:e+1] = True
    if not np.array_equal(got, exp): print("CASE FAIL:", name); ok = False
print("B-cases:", "PASS" if ok else "FAIL")

# boundary inspection
active = mhw.any(axis=1)
def day(i): return str(tdates[i])[:10]
print("active pattern:")
for row in range(0, 92, 10):
    print("  ", day(row), "".join("#" if active[i] else "." for i in range(row, min(row+10, 92))))
for b in [23,24,25,26, 37,38, 36, 96-1, 36, 37]:
    pass
checks = [("06-24", 23), ("06-25", 24), ("06-26", 25), ("06-27", 26),
          ("07-06", 36), ("07-07", 37), ("07-08", 38),
          ("08-05", 66), ("08-06", 67), ("08-10", 71), ("08-11", 72)]
for nm, i in checks:
    nact = int(active[i]); ncell = int(mhw[i].sum())
    print("2009-%s: active=%s cells-in-MHW=%d" % (nm, nact, ncell))
