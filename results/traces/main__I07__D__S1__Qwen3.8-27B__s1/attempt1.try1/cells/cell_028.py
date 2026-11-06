import numpy as np

def cell_mhw_spans(h):
    padded = np.concatenate(([0], h.astype(np.int8), [0]))
    dd = np.diff(padded)
    starts = np.where(dd == 1)[0]
    ends = np.where(dd == -1)[0] - 1
    runs = [(s, e) for s, e in zip(starts, ends) if e - s + 1 >= 5]
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return [tuple(m) for m in merged]

# unit tests
tests = [
    # (hot pattern, expected merged spans inclusive)
    ([1]*5, [(0,4)]),                                   # bare minimum
    ([1]*4, []),                                         # too short
    ([1]*5+[0,0]+[1]*5, [(0,9)]),                        # gap 2 -> join
    ([1]*5+[0,0,0]+[1]*5, [(0,4),(8,12)]),               # gap 3 -> no join
    ([1]*5+[0]+[1]*5+[0,0]+[1]*5, [(0,16)]),             # transitive join
    ([0,1]*3+[1]*6, [(1,8)]),                            # short runs ignored
    ([1]*7+[0]+[1]*4+[0]+[1]*7, [(0,14)]),               # middle run <5 but joins via chain? 
    # wait: runs are (0,6),(8,11) len4 -> not kept,(13,19). (0,6) and (13,19): gap = 13-6-1=6 -> no join.
    ([1]*5+[0,0,1]*1+[0]*10, [(0,4)]),                   # trailing singleton ignored
    ([0]*3+[1]*5+[0]*3+[1]*6, [(3,7),(11,16)]),          # gap 3 no join
    ([1]*5+[0]*2+[1]*5+[0]*2+[1]*5+[0]*2+[1]*5, [(0,18)]),  # chained
    (list(np.zeros(92, dtype=int)), []),
]
fixed_tests = []
for h, exp in tests:
    if h == [1]*7+[0]+[1]*4+[0]+[1]*7:
        exp = [(0,6),(13,19)]
    fixed_tests.append((h, exp))

for h, exp in fixed_tests:
    got = cell_mhw_spans(np.array(h, dtype=bool))
    status = "OK" if got == exp else f"FAIL expected {exp}"
    print(h, "->", got, status)
