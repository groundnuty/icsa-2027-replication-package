import numpy as np

def mhw_runs_greedy(h):
    nd = len(h)
    if not h.any(): return []
    diff = np.diff(h.astype(np.int8))
    starts = list(np.where(diff == 1)[0] + 1)
    if h[0]: starts.insert(0, 0)
    ends = list(np.where(diff == -1)[0])
    if h[-1]: ends.append(nd - 1)
    runs = [(s, e) for s, e in zip(starts, ends) if e - s + 1 >= 5]
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged

def mhw_runs_iterative(h):
    """spec-faithful independent: maximal hot runs of >=5, then repeatedly merge any pair with gap 1-2"""
    nd = len(h)
    # maximal hot runs
    runs = []
    t = 0
    while t < nd:
        if h[t]:
            u = t
            while u + 1 < nd and h[u+1]:
                u += 1
            runs.append((t, u))
            t = u + 1
        else:
            t += 1
    mhw = [r for r in runs if r[1] - r[0] + 1 >= 5]
    changed = True
    while changed:
        changed = False
        new = []
        used = [False] * len(mhw)
        for i in range(len(mhw)):
            if used[i]: continue
            s, e = mhw[i]
            for j in range(i+1, len(mhw)):
                if used[j]: continue
                s2, e2 = mhw[j]
                if s2 - e - 1 <= 2:
                    s, e = s, e2
                    used[j] = True
                    changed = True
            new.append((s, e))
            used[i] = True
        mhw = new
    return mhw

rng = np.random.default_rng(7)
bad = 0
for trial in range(50000):
    nd = int(rng.integers(1, 120))
    p = float(rng.uniform(0.05, 0.9))
    h = rng.random(nd) < p
    r1 = mhw_runs_greedy(h)
    r2 = mhw_runs_iterative(h)
    if r1 != r2:
        bad += 1
        if bad <= 5:
            print("MISMATCH", h.astype(int), r1, r2)
print("mismatches:", bad, "of 50000")
