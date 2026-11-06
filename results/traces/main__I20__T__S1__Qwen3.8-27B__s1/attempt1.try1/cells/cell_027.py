import numpy as np, pickle
D = pickle.load(open("/tmp/mhw_data.pkl","rb"))
R = pickle.load(open("/tmp/mhw_results.pkl","rb"))
B, T = D["B"], D["T"]
Ths = R["Ths_h"]; tdoys = R["tdoys"]
cells = np.argwhere(np.all(np.isfinite(T), axis=0))

def max_run(h):
    best = cur = 0
    for v in h:
        cur = cur+1 if v else 0
        best = max(best, cur)
    return best

runs = []
for ci,(i,j) in enumerate(cells):
    h = T[:,i,j] >= Ths[ci, tdoys-1]
    runs.append(max_run(h))
runs = np.array(runs)
print("max consecutive hot days per cell: min %d max %d" % (runs.min(), runs.max()))
import collections
print("distribution:", collections.Counter(runs.tolist()).most_common())
# where are the 4-day runs?
top = np.argsort(-runs)[:10]
for ci in top:
    i,j = cells[ci]
    h = (T[:,i,j] >= Ths[ci, tdoys-1])
    days = [D["tgt_dates"][k].isoformat() for k in range(92) if h[k]]
    print("cell", (i,j), "maxrun", runs[ci], "hot days:", days)

# synthetic test of pipeline logic
def pipeline_core(h):
    runs_ = []
    k = 0
    while k < len(h):
        if h[k]:
            l = k
            while l+1 < len(h) and h[l+1]: l += 1
            if l-k+1 >= 5: runs_.append([k, l])
            k = l+1
        else:
            k += 1
    merged = []
    for s, e in runs_:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    out = np.zeros(len(h), bool)
    for s, e in merged: out[s:e+1] = True
    return out

# test: 5 hot, gap 2, 5 hot, gap 3, 5 hot -> expect [0..11] and [15..19]
h = np.array([1,1,1,1,1,0,0,1,1,1,1,1,0,0,0,1,1,1,1,1], dtype=bool)
print("synth:", pipeline_core(h).astype(int).tolist())
# test: 4 hot -> nothing
print("synth2:", pipeline_core(np.array([1,1,1,1,0,1,1,1,1,1])).astype(int).tolist())
# test: 5 hot, gap 2, 4 hot -> only first run
print("synth3:", pipeline_core(np.array([1,1,1,1,1,0,0,1,1,1,1,0,0,0])).astype(int).tolist())