import numpy as np

def runs_of(mask):
    """list of (start, end) inclusive index pairs of True runs in 1D bool array."""
    m = np.asarray(mask, dtype=bool)
    if m.size == 0: return []
    d = np.diff(m.astype(np.int8))
    starts = list(np.where(d == 1)[0] + 1)
    ends = list(np.where(d == -1)[0])
    if m[0]: starts = [0] + starts
    if m[-1]: ends = ends + [m.size - 1]
    return list(zip(starts, ends))

def detect_mhw(hot, min_run=5, join_gap=2):
    runs = [(s, e) for (s, e) in runs_of(hot) if e - s + 1 >= min_run]
    if not runs: return []
    merged = [list(runs[0])]
    for s, e in runs[1:]:
        if s - merged[-1][1] - 1 <= join_gap and s - merged[-1][1] - 1 >= 1:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return [tuple(x) for x in merged]

# synthetic tests
cases = [
    ("run of 5",            [1,1,1,1,1,0,0,0,0,0], [(0,4)]),
    ("run of 4 (too short)",[1,1,1,1,0,0,0,0,0,0], []),
    ("two runs gap 2 -> join",[1,1,1,1,1,0,0,1,1,1,1,1,0,0], [(0,11)]),
    ("two runs gap 3 -> no join",[1,1,1,1,1,0,0,0,1,1,1,1,1,0], [(0,4),(8,12)]),
    ("two runs gap 1 -> join",[1,1,1,1,1,0,1,1,1,1,1,0,0], [(0,10)]),
    ("short bridge doesn't join",[1]*5+[0,0]+[1]*4+[0,0]+[1]*5+[0], [(0,4),(9,13)]),
    ("three runs chain join", [1]*5+[0]+[1]*5+[0,0]+[1]*5+[0,0,0,0], [(0,19)]),
    ("starts hot at end",     [0,0,1,1,1,1,1], [(2,6)]),
    ("all hot",               [1]*10, [(0,9)]),
]
for name, mask, expect in cases:
    got = detect_mhw(np.array(mask, dtype=bool))
    status = "OK " if got == expect else "FAIL"
    print(f"{status} {name}: got {got}" + ("" if status=="OK " else f" expected {expect}"))

# runs_of sanity
print(runs_of(np.array([0,1,1,0,0,1,1,1], dtype=bool)))
