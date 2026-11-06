import numpy as np

def per_cell_mhw(h):
    """h: (nt,) bool. Returns bool array same shape: True where day is inside a per-cell MHW.
    Runs >=5 consecutive hot days; runs separated by 1-2 non-hot days are joined (gap days included)."""
    nt = len(h)
    mhw = np.zeros(nt, dtype=bool)
    # find runs of True
    idx = np.flatnonzero(h)
    if len(idx) == 0:
        return mhw
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.concatenate([[idx[0]], idx[breaks + 1]])
    ends = np.concatenate([idx[breaks], [idx[-1]]])
    cand = [(s, e) for s, e in zip(starts, ends) if e - s + 1 >= 5]
    if not cand:
        return mhw
    # merge candidates with gaps <= 2
    merged = [list(cand[0])]
    for s, e in cand[1:]:
        if s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    for s, e in merged:
        mhw[s:e+1] = True
    return mhw

# synthetic tests
tests = [
    (np.array([1,1,1,1,1,0,0,0,0,0], bool), [(0,4)]),                       # run of 5
    (np.array([1,1,1,1,0,1,1,1,1,1,0,0], bool), [(0,9)]),                   # 4+gap1+5 -> joined? run1 len4 not candidate!
    (np.array([1,1,1,1,1,0,1,1,1,1,1,0,0], bool), [(0,10)]),                # 5+gap1+5 -> joined
    (np.array([1,1,1,1,1,0,0,1,1,1,1,1,0], bool), [(0,11)]),                # gap2 -> joined
    (np.array([1,1,1,1,1,0,0,0,1,1,1,1,1], bool), [(0,4),(8,12)]),          # gap3 -> not joined
    (np.array([0,0,1,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1], bool), [(2,18)]),    # two joins
    (np.array([1,1,1,1,0,0,1,1,1,1,1,1,1,1,0,0,0,0,0], bool), [(0,13)]),    # first len4 -> only second counts
]
allok = True
for i, (h, exp) in enumerate(tests):
    got = per_cell_mhw(h)
    # extract runs from got
    idx = np.flatnonzero(got)
    brk = np.flatnonzero(np.diff(idx) > 1)
    runs = list(zip(np.concatenate([[idx[0]], idx[brk+1]]) if len(idx) else [], 
                    np.concatenate([idx[brk], [idx[-1]]]) if len(idx) else []))
    ok = runs == [tuple(x) for x in exp]
    if not ok:
        allok = False
        print("test", i, "FAILED: got", runs, "expected", exp)
    else:
        print("test", i, "OK:", runs)
print("run-join logic:", "ALL OK" if allok else "ERRORS")
