import numpy as np

# synthetic check of the two orders on a 1-cell sequence
seq = np.array([1,1,0,1,1,1,1,1,1,0,0], dtype=bool)  # hot 0-1, gap 2 (1 non-hot), hot 3-8 (6d)
# spec order: MHWs = runs >=5 -> [3..8]; joining between MHWs only -> single MHW 3..8
def spec_mhw(seq):
    idx = np.flatnonzero(np.diff(np.concatenate(([False], seq, [False])).astype(np.int8)))
    starts = idx[0::2]; ends = idx[1::2]-1
    keep = []
    for s, e in zip(starts, ends):
        if e-s+1 >= 5:
            if keep and s - keep[-1][1] - 1 <= 2: keep[-1][1] = e
            else: keep.append([s, e])
    out = np.zeros_like(seq)
    for s, e in keep: out[s:e+1] = True
    return out
# wrong order: merge all runs first, then filter >=5
def wrong_mhw(seq):
    idx = np.flatnonzero(np.diff(np.concatenate(([False], seq, [False])).astype(np.int8)))
    starts = idx[0::2]; ends = idx[1::2]-1
    groups = [[s,e] for s,e in zip(starts, ends)]
    merged = []
    for g in groups:
        if merged and g[0] - merged[-1][1] - 1 <= 2: merged[-1][1] = g[1]
        else: merged.append(list(g))
    out = np.zeros_like(seq)
    for s, e in merged:
        if e-s+1 >= 5: out[s:e+1] = True
    return out
print("spec :", spec_mhw(seq).astype(int))   # expect 0 except 3..8
print("wrong:", wrong_mhw(seq).astype(int))  # expect 0..8
# join between two real MHWs: hot 0-5, gap 6 (1 non-hot), hot 7-12
seq2 = np.array([1]*6 + [0] + [1]*6, dtype=bool)
print("join works:", spec_mhw(seq2).astype(int))  # expect 0..12 all 1

# redo independent check with SPEC order
block = np.load("/tmp/sst_block.npy")
alldays = open("/tmp/alldays.txt").read().split("\n")
sea_cells = np.load("/tmp/sea_cells.npy")
thr = np.load("/tmp/thr_smooth.npy")
nb = 4028
target_days = alldays[nb:]; nt = len(target_days)
cum_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_of(s):
    m, d = int(s[5:7]), int(s[8:10]); return cum_before[m-1] + d
sst = block[nb:].astype(np.float64)
hot = sst >= thr[np.array([doy_of(s) for s in target_days]) - 1]
hot[:, ~sea_cells] = False

mhw_ref = np.zeros((nt, 60, 60), dtype=bool)
n_ev = 0
for r in range(60):
    for l in range(60):
        if not sea_cells[r, l]: continue
        s = hot[:, r, l]
        if not s.any(): continue
        idx = np.flatnonzero(np.diff(np.concatenate(([False], s, [False])).astype(np.int8)))
        starts = idx[0::2]; ends = idx[1::2]-1
        keep = []
        for a, b in zip(starts, ends):
            if b-a+1 >= 5:
                if keep and a - keep[-1][1] - 1 <= 2: keep[-1][1] = b
                else: keep.append([a, b])
        for a, b in keep:
            n_ev += 1
            mhw_ref[a:b+1, r, l] = True
mhw = np.load("/tmp/mhw_mask.npy")
print("independent (spec order) events:", n_ev, "| mask identical:", np.array_equal(mhw, mhw_ref))
# which extra days the wrong order would have added (regional diff)
mhw_wrong = np.zeros((nt,60,60), dtype=bool)
for r in range(60):
    for l in range(60):
        if not sea_cells[r,l]: continue
        s = hot[:, r, l]
        if not s.any(): continue
        idx = np.flatnonzero(np.diff(np.concatenate(([False], s, [False])).astype(np.int8)))
        starts = idx[0::2]; ends = idx[1::2]-1
        merged = []
        for a, b in zip(starts, ends):
            if merged and a - merged[-1][1] - 1 <= 2: merged[-1][1] = b
            else: merged.append([a, b])
        for a, b in merged:
            if b-a+1 >= 5: mhw_wrong[a:b+1, r, l] = True
extra = mhw_wrong & ~mhw
print("days the wrong order would add:", [target_days[t] for t in np.flatnonzero(extra.any(axis=(1,2)))],
      "| extra cells per day:", extra.sum(axis=(1,2))[extra.any(axis=(1,2))])
