import numpy as np

def per_cell_mhw(h):
    nt = len(h)
    mhw = np.zeros(nt, dtype=bool)
    idx = np.flatnonzero(h)
    if len(idx) == 0:
        return mhw
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.concatenate([[idx[0]], idx[breaks + 1]])
    ends = np.concatenate([idx[breaks], [idx[-1]]])
    cand = [(s, e) for s, e in zip(starts, ends) if e - s + 1 >= 5]
    if not cand:
        return mhw
    merged = [list(cand[0])]
    for s, e in cand[1:]:
        if s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    for s, e in merged:
        mhw[s:e+1] = True
    return mhw

# corrected expectations: runs <5 are NOT MHWs and are not joined
tests = [
    (np.array([1,1,1,1,0,1,1,1,1,1,0,0], bool), [(5,9)]),      # 4-day run not an MHW
    (np.array([1,1,1,1,0,0,1,1,1,1,1,1,1,1,0,0,0,0,0], bool), [(6,13)]),
    (np.array([1,1,1,1,1,0,1,1,1,1,0,1,1,1,1,1], bool), [(0,15)]),  # 5,gap1,4,gap1,5 -> the two >=5 runs separated by 6 non-hot days -> NOT joined; middle 4-day run excluded
    (np.array([1,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1], bool), [(0,16)]),  # 5,gap1,5,gap1,5 -> joined into one
]
allok = True
for i, (h, exp) in enumerate(tests):
    got = per_cell_mhw(h)
    idx = np.flatnonzero(got)
    if len(idx):
        brk = np.flatnonzero(np.diff(idx) > 1)
        runs = list(zip(np.concatenate([[idx[0]], idx[brk+1]]).tolist(),
                        np.concatenate([idx[brk], [idx[-1]]]).tolist()))
    else:
        runs = []
    ok = runs == [tuple(x) for x in exp]
    allok &= ok
    print("test", i, "OK" if ok else f"FAILED got {runs} exp {exp}")
print("logic:", "ALL OK" if allok else "ERRORS")

# check non-sea cells are all-NaN (land) in target
T = np.load('work/T.npy')
fin_any = np.isfinite(T).any(axis=0)
fin_all = np.isfinite(T).all(axis=0)
n_land = (~fin_any).sum(); n_partial = (fin_any & ~fin_all).sum()
print("all-NaN cells (land):", n_land, "| partial-data cells:", n_partial, "| sea cells:", fin_all.sum())
