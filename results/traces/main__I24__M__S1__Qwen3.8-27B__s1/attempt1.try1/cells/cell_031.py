import numpy as np

def mhw_mask(h):
    """h: 1-D bool array (hot days). Returns mask of days inside per-cell MHWs (>=5 runs, merge gap<=2)."""
    h = np.asarray(h).astype(bool)
    n = len(h)
    d = np.diff(np.concatenate(([0], h.view(np.int8), [0])))
    st = np.flatnonzero(d == 1)
    en = np.flatnonzero(d == -1) - 1
    keep = (en - st + 1) >= 5
    st, en = st[keep], en[keep]
    ms, me = [], []
    for s, e in zip(st, en):
        if ms and s - me[-1] - 1 <= 2:
            me[-1] = int(e)
        else:
            ms.append(int(s)); me.append(int(e))
    out = np.zeros(n, dtype=np.uint8)
    for s, e in zip(ms, me):
        out[s:e+1] = 1
    return out, list(zip(ms, me))

def ref_events(h):
    """brute force: returns list of (start,end) inclusive of merged MHWs"""
    n = len(h)
    runs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j+1 < n and h[j+1]:
                j += 1
            runs.append([i, j])
            i = j+1
        else:
            i += 1
    runs = [r for r in runs if r[1]-r[0]+1 >= 5]
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] - 1 <= 2:
            merged[-1][1] = r[1]
        else:
            merged.append(list(r))
    return [tuple(m) for m in merged]

rng = np.random.default_rng(3)
ok = True
for trial in range(20000):
    n = int(rng.integers(0, 80))
    p = rng.choice([0.0, 0.1, 0.3, 0.5, 0.7, 1.0])
    h = rng.random(n) < p
    got = mhw_mask(h)[1]
    exp = ref_events(h)
    if got != exp:
        ok = False
        print("MISMATCH", n, h.tolist(), got, exp)
        break
print("run/merge logic verified on 20000 random cases:", ok)

# targeted cases
cases = [
    ([1,1,1,1,1,0,1,1,1,1,1], [(0,4),(6,10)]),            # gap 1 -> merge -> (0,10)
    ([1,1,1,1,1,0,0,1,1,1,1,1], [(0,11)]),                # gap 2 -> merge
    ([1,1,1,1,1,0,0,0,1,1,1,1,1], [(0,4),(8,12)]),        # gap 3 -> no merge
    ([1,1,1,1,1,0,1,1,1,1,1,0,0,1,1,1,1,1], [(0,17)]),    # chain merge
    ([1,1,1,1,1,0,1,1,0,0,1,1,1,1,1], [(0,14)]),          # gap2, gap2 chain
    ([1,1,1,1,0,0,0,1,1,1,1,1], [(0,11)]),                # first run len4! -> no MHW at all
    ([1,1,1,1,1,1,1], [(0,6)]),
    ([0,0,0], []),
]
for h, exp in cases:
    got = mhw_mask(np.array(h, dtype=bool))[1]
    print(h.count(1), "hot:", got, "expected-ish:", exp, "OK" if got==exp else "MISMATCH")
