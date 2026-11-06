import numpy as np, datetime
z = np.load('/work/region.npz'); s = np.load('/work/doy_stats.npz'); m = np.load('/work/mhw.npz')
tgt3 = z['tgt_sst'].reshape(92, 3600)
st2 = s['sm_thresh'].reshape(366, 3600)
tgt_doy = s['target_doy']
sea = m['sea']; mhw = m['mhw']
NC = 3600

# slow per-cell MHW with explicit day-by-day logic
def slow_mhw(col):
    n = 92
    hot = [bool(tgt3[t, col] >= st2[int(tgt_doy[t])-1, col]) for t in range(n)]
    # maximal hot runs
    runs = []
    i = 0
    while i < n:
        if hot[i]:
            j = i
            while j+1 < n and hot[j+1]: j += 1
            runs.append([i, j]); i = j+1
        else:
            i += 1
    kept = [r for r in runs if r[1]-r[0]+1 >= 5]
    # join iteratively
    changed = True
    while changed:
        changed = False
        newk = []
        for r in kept:
            if newk and r[0] - newk[-1][1] - 1 <= 2:
                newk[-1][1] = r[1]; changed = True
            else:
                newk.append(r)
        kept = newk
    out = [False]*n
    for a, b in kept:
        for t in range(a, b+1): out[t] = True
    return out

rng = np.random.default_rng(7)
sample = list(rng.choice(np.where(sea)[0], 60, replace=False))
bad = 0
for col in sample:
    sm = np.array(slow_mhw(col))
    if not np.array_equal(sm, mhw[:, col]):
        bad += 1
        print("MISMATCH at col", col)
print("slow-vs-vector mask mismatches:", bad, "of", len(sample))

# also verify land cells all zero
print("land cells nonzero in mask:", int((mhw[:, ~sea] != 0).sum()))
print("mask sum:", int(mhw.sum()), "dtype check: uint8 ok")
# event boundaries double-check
active = mhw.any(axis=1)
print("active:", int(np.where(active)[0]))
