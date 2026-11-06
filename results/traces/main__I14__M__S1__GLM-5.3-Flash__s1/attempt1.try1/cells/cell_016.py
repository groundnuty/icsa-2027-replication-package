import numpy as np, datetime as dt

z = np.load("/work/cache_sst.npz"); tgt32 = z["tgt"]; tgt_ord = z["tgt_ord"]
z2 = np.load("/work/cache_thr2.npz"); thr, clim = z2["thr"], z2["clim"]
zm = np.load("/work/cache_mhw.npz"); mhw = zm["mhw"]
tgt64 = tgt32.astype(np.float64)
tgt_doy = np.array([dt.date.fromordinal(int(o)).timetuple().tm_yday for o in tgt_ord], dtype=np.int32)
sea = np.all(np.isfinite(tgt64), axis=0)
hot = (tgt64 >= thr[tgt_doy-1]) & sea[None, :, :]

# --- synthetic tests of the segment algorithm (incl. gap-join cases) ---
def cell_segments(hot):
    n = len(hot); segs = []; i = 0
    while i < n:
        if hot[i]:
            j = i
            while j < n and hot[j]: j += 1
            if j - i >= 5: segs.append((i, j-1))
            i = j
        else: i += 1
    if not segs: return []
    joined = [list(segs[0])]
    for s, e in segs[1:]:
        if s - joined[-1][1] - 1 <= 2: joined[-1][1] = e
        else: joined.append([s, e])
    return [tuple(x) for x in joined]

cases = [
    ([1]*5+[0]+[1]*5, [(0,9)]),                    # 5d run, 1 gap, 5d run -> join
    ([1]*5+[0,0]+[1]*5, [(0,10)]),                 # 2-day gap -> join
    ([1]*5+[0,0,0]+[1]*5, [(0,4),(8,12)]),         # 3-day gap -> no join
    ([1]*4+[0]+[1]*5, [(5,9)]),                    # 4d run too short, dropped
    ([0]*3+[1]*7+[0]*2+[1]*5+[0], [(3,14)]),       # 7d + 2 gap + 5d -> join
    ([1]*10, [(0,9)]),
    ([1]*4, []),                                    # run shorter than 5 at end
    ([0,1,1,1,1,1,1,1,1,1,1,1,1,0], [(1,12)]),
]
ok_syn = True
for h, exp in cases:
    got = cell_segments(np.array(h, dtype=bool))
    if got != exp: ok_syn = False; print("SYN FAIL", h, "got", got, "exp", exp)
print("synthetic segment tests passed:", ok_syn)

# --- brute-force independent recomputation for sample cells ---
rng = np.random.default_rng(7)
cells = list(map(tuple, rng.choice(np.argwhere(sea), 6, replace=False)))
ok_bf = True
for (i, j) in cells:
    h = hot[:, i, j]
    # independent run labeling via np.diff on padded array
    pad = np.concatenate([[0], h.view(np.int8), [0]])
    starts = np.where(np.diff(pad) == 1)[0]; ends = np.where(np.diff(pad) == -1)[0] - 1
    segs = [(s, e) for s, e in zip(starts, ends) if e - s + 1 >= 5]
    joined = []
    for s, e in segs:
        if joined and s - joined[-1][1] - 1 <= 2: joined[-1][1] = e
        else: joined.append([s, e])
    mask_bf = np.zeros(92, dtype=np.uint8)
    for s, e in joined: mask_bf[s:e+1] = 1
    if not np.array_equal(mask_bf, mhw[:, i, j]): ok_bf = False; print("BF FAIL", (i, j))
    # also verify hot day derivation for this cell on 5 random days
    for k in rng.integers(0, 92, 5):
        d = tgt_doy[k]
        exp_hot = tgt64[k, i, j] >= thr[d-1, i, j]
        if exp_hot != bool(h[k]): ok_bf = False; print("HOT FAIL", (i,j), k)
print("brute-force per-cell checks passed (6 cells):", ok_bf)

# --- event cross-check: active days and their MHW cell counts ---
active = mhw.reshape(92, -1).any(axis=1)
dates = [dt.date.fromordinal(int(o)) for o in tgt_ord]
print("active days:", [d.isoformat() for d, a in zip(dates, active) if a])
for k in np.where(active)[0]:
    print("  %s: %d cells in MHW" % (dates[k].isoformat(), int(mhw[k].sum())))
# max gap between consecutive MHW cell-days outside event: verify no cell has mhw outside Jul1-8
outside = mhw.copy(); outside[np.where(active)[0][0]:np.where(active)[0][-1]+1] = 0
print("mhw days outside event window:", int(outside.sum()))
# cells per active day edge check: on Jul 1 (first active) how many cells start their MHW?
k0 = int(np.where(active)[0][0])
print("Jul 1: cells with MHW starting that day:", int((mhw[k0] & ~mhw[k0-1]).sum()), "continuing:", int((mhw[k0] & mhw[k0-1]).sum()))
k1 = int(np.where(active)[0][-1])
print("Jul 8: cells with MHW ending that day:", int((mhw[k1] & ~mhw[k1+1]).sum()))
