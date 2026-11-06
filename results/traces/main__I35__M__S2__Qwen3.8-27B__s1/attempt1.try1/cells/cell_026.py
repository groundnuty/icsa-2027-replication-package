import numpy as np, json
from collections import Counter

# ============ load verified inputs ============
X = np.load("/tmp/X.npy")        # (4028, 60, 60): 1991-12-27..2003-01-05
p3 = np.load("/tmp/p3.npy")      # (92, 60, 60): 2009-06-01..2009-08-31
sea = np.load("/tmp/sea.npy")    # (60, 60) sea cells
M = np.load("/tmp/M.npy")        # (366, 4028) pool membership
assert X.shape == (4028, 60, 60) and p3.shape == (92, 60, 60) and M.shape == (366, 4028)
nsea = int(sea.sum())
Xsea = X[:, sea]
print("sea cells:", nsea)

# ============ doy mapping (task's month/day rule) ============
PREF = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
def doy(dates):
    dates = dates.astype("datetime64[D]")
    d = dates.astype("int64")
    first = dates.astype("datetime64[M]").astype("datetime64[D]").astype("int64")
    day = d - first + 1
    month = dates.astype("datetime64[M]").astype("int64") % 12
    return PREF[month] + day
for s, e in [("1992-01-01",1),("1992-02-29",60),("1993-03-01",61),("2002-12-31",366),("2009-06-01",153),("2009-08-31",244)]:
    assert int(doy(np.array([s], dtype="datetime64[D]"))[0]) == e, s

# ============ threshold & climatology ============
thr = np.full((366, nsea), np.nan)
clim = np.full((366, nsea), np.nan)
for d in range(1, 367):
    if d == 60: continue
    vals = Xsea[M[d-1]]
    thr[d-1] = np.nanquantile(vals, 0.9, axis=0, method="hazen")
    clim[d-1] = np.nanmean(vals, axis=0)
thr[59] = (thr[58] + thr[60]) / 2.0
clim[59] = (clim[58] + clim[60]) / 2.0
assert not np.isnan(thr).any() and not np.isnan(clim).any()
idx31 = (np.arange(366)[:, None] - 15 + np.arange(31)[None, :]) % 366
thr_s = thr[idx31].mean(axis=1)
clim_s = clim[idx31].mean(axis=1)
assert not np.isnan(thr_s).any()
print("thr_s: %.3f..%.3f K" % (thr_s.min(), thr_s.max()))

# ============ target period ============
tdates = np.datetime64("2009-06-01") + np.arange(92)
tdoy = doy(tdates)
assert str(tdates[0]) == "2009-06-01" and str(tdates[-1]) == "2009-08-31"
SST_t = p3[:, sea]
assert not np.isnan(SST_t).any(), "sea cells must be finite on all target days"
hot = SST_t >= thr_s[tdoy - 1]
print("hot fraction: %.4f" % float(hot.mean()))

# ============ per-cell MHW (validated logic) ============
def cell_mhw(hot):
    nt = len(hot)
    hpad = np.array([False] + list(hot) + [False])
    dd = np.diff(hpad.astype(np.int8))
    starts = np.where(dd == 1)[0]
    ends = np.where(dd == -1)[0] - 1
    runs = [(int(s), int(e)) for s, e in zip(starts, ends) if e - s + 1 >= 5]
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    out = np.zeros(nt, bool)
    for s, e in merged:
        out[s:e+1] = True
    return out, merged

def ref_cell(hot):
    n = len(hot); out = np.zeros(n, bool)
    i = 0; runs = []
    while i < n:
        if hot[i]:
            j = i
            while j + 1 < n and hot[j+1]: j += 1
            if j - i + 1 >= 5: runs.append([i, j])
            i = j + 1
        else: i += 1
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2: merged[-1][1] = e
        else: merged.append([s, e])
    for s, e in merged: out[s:e+1] = True
    return out

rng = np.random.default_rng(1)
for trial in range(20000):
    hr = rng.random(92) < rng.uniform(0.02, 0.8)
    assert np.array_equal(cell_mw if False else cell_mhw(hr)[0], ref_cell(hr)), trial
cases = [
    ("5hot-gap2-5hot", [True]*5 + [False]*2 + [True]*5 + [False]*82, [(0,11)]),
    ("5hot-gap3-5hot", [True]*5 + [False]*3 + [True]*5 + [False]*82, [(0,4),(8,12)]),
    ("4hot", [True]*4 + [False]*88, []),
    ("5-1-4-1-5", [True]*5+[False]+[True]*4+[False]+[True]*5+[False]*77, [(0,4),(11,15)]),
    ("6-2-6-2-6", [True]*6+[False]*2+[True]*6+[False]*2+[True]*6+[False]*72, [(0,21)]),
    ("endrun", [False]*87 + [True]*5, [(87,91)]),
]
for name, hr, exp_runs in cases:
    got = cell_mhw(np.array(hr, bool))[0]
    exp = np.zeros(92, bool)
    for s, e in exp_runs: exp[s:e+1] = True
    assert np.array_equal(got, exp), name
print("run+merge validation: PASS")

mhw = np.zeros((92, nsea), dtype=bool)
durs = []
n_with = 0
for c in range(nsea):
    out, merged = cell_mhw(hot[:, c])
    if merged:
        mhw[:, c] = out
        n_with += 1
        durs += [e - s + 1 for s, e in merged]
print("cells with >=1 MHW:", n_with, " per-cell MHWs:", len(durs),
      " durations:", dict(sorted(Counter(durs).items())))

# ============ regional events ============
active = mhw.any(axis=1)
print("active days:", int(active.sum()))
dd = np.diff(np.concatenate([[0], active.astype(int), [0]]))
ev_s = np.where(dd == 1)[0]; ev_e = np.where(dd == -1)[0] - 1
events = [(int(s), int(e)) for s, e in zip(ev_s, ev_e)]
print("regional events:")
for s, e in events:
    print("   %s -> %s  len %d" % (str(tdates[s]), str(tdates[e]), e - s + 1))
for row in range(0, 92, 10):
    print("   ", str(tdates[row])[:10], "".join("#" if active[i] else "." for i in range(row, min(row+10, 92))))

# ============ save fresh artifacts ============
np.save("/tmp/final_mhw.npy", mhw.astype(np.uint8))
np.save("/tmp/final_thr_s.npy", thr_s)
np.save("/tmp/final_clim_s.npy", clim_s)
json.dump([{"onset": str(tdates[s]), "end": str(tdates[e])} for s, e in events], open("/tmp/final_events.json", "w"))
print("saved final artifacts")
