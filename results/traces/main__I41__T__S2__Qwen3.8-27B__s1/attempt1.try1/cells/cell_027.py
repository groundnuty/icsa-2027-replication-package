import numpy as np
rng = np.random.default_rng(42)

def methodA(h):
    n = len(h); runs = []; i = 0
    while i < n:
        if h[i]:
            j = i
            while j + 1 < n and h[j+1]: j += 1
            if j - i + 1 >= 5: runs.append([i, j])
            i = j + 1
        else: i += 1
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2: merged[-1][1] = e
        else: merged.append([s, e])
    out = set()
    for s, e in merged: out.update(range(s, e+1))
    return out

def methodB(h):
    n = len(h); runs = []; i = 0
    while i < n:
        if h[i]:
            j = i
            while j + 1 < n and h[j+1]: j += 1
            runs.append((i, j)); i = j + 1
        else: i += 1
    R = [r for r in runs if r[1]-r[0]+1 >= 5]
    ev = set(); k = 0
    while k < len(R):
        m = k
        while m + 1 < len(R) and R[m+1][0] - R[m][1] - 1 <= 2: m += 1
        ev.update(range(R[k][0], R[m][1]+1))   # full interval incl. gap days
        k = m + 1
    return ev

bad = 0
for trial in range(100000):
    p = rng.uniform(0.05, 0.95)
    h = rng.random(92) < p
    if methodA(h) != methodB(h):
        bad += 1
print("mismatches:", bad, "/ 100000")
