import numpy as np
# reproduce first mismatch deterministically
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
    return out, runs, merged

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
        for r in R[k:m+1]: ev.update(range(r[0], r[1]+1))
        k = m + 1
    return ev, runs, R

cnt = 0
for trial in range(20000):
    p = rng.uniform(0.1, 0.9)
    h = rng.random(92) < p
    a, runsA, mergedA = methodA(h)
    b, runsB, R = methodB(h)
    if a != b:
        cnt += 1
        if cnt == 1:
            s = ''.join('1' if x else '0' for x in h)
            print("seq:", s)
            print("runs(all):", runsB)
            print("runsA(long):", runsA, "mergedA:", mergedA)
            print("R(long):", R)
            print("days only in A:", sorted(a-b))
            print("days only in B:", sorted(b-a))
        break
print("found", cnt)
