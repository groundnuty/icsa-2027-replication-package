import numpy as np
rng = np.random.default_rng(42)

def methodA(h):
    """runs >=5, forward-pass join over gaps 1-2 -> set of event days"""
    n = len(h)
    runs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j + 1 < n and h[j+1]: j += 1
            if j - i + 1 >= 5: runs.append([i, j])
            i = j + 1
        else: i += 1
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    out = set()
    for s, e in merged: out.update(range(s, e+1))
    return out

def methodB(h):
    """exhaustive: all maximal hot runs (any length), then find all maximal chains of
    runs with len>=5 and consecutive gaps <=2; union of days in any maximal chain"""
    n = len(h)
    runs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j + 1 < n and h[j+1]: j += 1
            runs.append((i, j)); i = j + 1
        else: i += 1
    R = [r for r in runs if r[1]-r[0]+1 >= 5]
    # maximal chains: chain is sequence of consecutive runs in R where each gap<=2
    # (consecutive in the full run list AND in R - since R preserves order, gaps between
    #  R elements must also be <=2, but a skipped <5 run between them would break the
    #  'separated by 1-2 non-hot days' condition. Two MHW runs separated by a <5 run + gaps:
    #  non-hot days between them > 2 automatically? gap between R[k] and R[k+2] (skipping a <5 run)
    #  = 1 + len(short run) + 1 >= 3 -> cannot be joined. So chains are just consecutive in R.)
    ev = set()
    k = 0
    while k < len(R):
        s, e = R[k]
        m = k
        while m + 1 < len(R) and R[m+1][0] - R[m][1] - 1 <= 2:
            m += 1
        for r in R[k:m+1]: ev.update(range(r[0], r[1]+1))
        k = m + 1
    return ev

bad = 0
for trial in range(20000):
    p = rng.uniform(0.1, 0.9)
    h = rng.random(92) < p
    if methodA(h) != methodB(h):
        bad += 1
        if bad < 4: print("MISMATCH", h.astype(int).tobytes().decode('latin1')[:92])
print("mismatches:", bad, "/ 20000")
