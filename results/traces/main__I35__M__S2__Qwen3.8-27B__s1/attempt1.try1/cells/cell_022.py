import numpy as np, json
from collections import Counter

PREF = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
def doy(dates):
    dates = dates.astype("datetime64[D]")
    d = dates.astype("int64")
    first = dates.astype("datetime64[M]").astype("datetime64[D]").astype("int64")
    day = d - first + 1
    month = dates.astype("datetime64[M]").astype("int64") % 12
    return PREF[month] + day

p3 = np.load("/tmp/p3.npy"); sea = np.load("/tmp/sea.npy")
nsea = int(sea.sum())
thr_s = np.load("/tmp/thr_s.npy")

tdates = np.datetime64("2009-06-01") + np.arange(p3.shape[0])
tdoy = doy(tdates)
SST_t = p3[:, sea]
assert not np.isnan(SST_t).any()
hot = SST_t >= thr_s[tdoy - 1]

def cell_mhw(hot):
    nt = len(hot)
    hpad = np.array([False] + list(hot) + [False])
    d = np.diff(hpad.astype(np.int8))
    starts = np.where(d == 1)[0]      # hot index of first hot day
    ends = np.where(d == -1)[0] - 1   # hot index of last hot day
    runs = [(s, e) for s, e in zip(starts, ends) if e - s + 1 >= 5]
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

# validate vs naive reference on the previously failing case + random
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
ok = True
for trial in range(20000):
    hotr = rng.random(92) < rng.uniform(0.02, 0.8)
    if not np.array_equal(cell_mhw(hotr)[0], ref_cell(hotr)):
        ok = False; print("MISMATCH trial", trial); break
# explicit cases:
cases = {
    "5 hot, gap2, 5 hot": ([True]*5 + [False]*2 + [True]*5 + [False]*82, [0,12]),
    "5 hot, gap3, 5 hot": ([True]*5 + [False]*3 + [True]*5 + [False]*82, [0,4], [10,14]),
    "4 hot only": ([True]*4 + [False]*88, []),
    "5 hot gap1 4 hot gap1 5 hot": ([True]*5+[False]+[True]*4+[False]+[True]*5+[False]*77, [0,16]),
}
for name, *rest in cases.items():
    hotr = rest[0]
    got = cell_mhw(np.array(hotr, bool))[0]
    exp_runs = rest[1:]
    exp = np.zeros(92, bool)
    for s, e in exp_runs: exp[s:e+1] = True
    if not np.array_equal(got, exp): print("CASE FAIL:", name); ok = False
print("B) run+merge logic check:", "PASS" if ok else "FAIL")

# ---- full detection with corrected code ----
nt = p3.shape[0]
mhw = np.zeros((nt, nsea), dtype=bool)
durs = []
n_cells_with = 0
for c in range(nsea):
    out, merged = cell_mhw(hot[:, c])
    if merged:
        mhw[:, c] = out
        n_cells_with += 1
        durs += [e - s + 1 for s, e in merged]

print("hot fraction: %.4f" % float(hot.mean()))
print("cells with >=1 MHW:", n_cells_with, "of", nsea)
print("per-cell MHWs:", len(durs), "durations:", dict(sorted(Counter(durs).items())))

active = mhw.any(axis=1)
print("active days:", int(active.sum()), "of", nt)
dd = np.diff(np.concatenate([[0], active.astype(int), [0]]))
ev_s = np.where(dd == 1)[0]; ev_e = np.where(dd == -1)[0] - 1
events = [(int(s), int(e)) for s, e in zip(ev_s, ev_e)]
print("regional events:")
for s, e in events:
    print("   %s -> %s  len %d" % (str(tdates[s]), str(tdates[e]), e - s + 1))

np.save("/tmp/mhw.npy", mhw.astype(np.uint8))
json.dump([{"onset": str(tdates[s]), "end": str(tdates[e])} for s, e in events], open("/tmp/events.json", "w"))
print("saved OK")
