import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

# --- demonstrate the bug in the previous vectorized version on a toy case ---
hot = np.zeros((20,1), bool); hot[2:9] = True; hot[12:17] = True   # run of 7, gap 3, run of 5
def runs_ge_buggy(mask, L):
    T, N = mask.shape
    pad = np.zeros((T+L-1, N), bool); pad[L-1:L-1+T] = mask
    starts = sliding_window_view(pad, L, axis=0).all(axis=2)
    res = starts.copy()
    for k in range(1, L): res[k:] |= starts[:-k]
    return res
def dilate(mask, r):
    out = mask.copy()
    for k in range(1, r+1):
        out[k:] |= mask[:-k]; out[:-k] |= mask[k:]
    return out
buggy = dilate(runs_ge_buggy(hot,5),2) & dilate(hot,2)
print('toy hot      :', hot[:,0].astype(int))
print('toy buggy out:', buggy[:,0].astype(int), ' <- should equal hot exactly (runs>=5, gap 3 not joined)')

# --- correct implementations ---
def runs_ge5_correct(m):
    """mark all days of maximal hot runs with length >= 5. m: (T,N) bool"""
    T, N = m.shape
    starts = m.copy(); starts[1:] &= ~m[:-1]          # run starts
    rid = np.cumsum(starts, axis=0)                    # run id per column (0 where not started yet)
    uid = rid + np.arange(N)[None,:]*(T+1)             # unique per (column, run)
    lens = np.bincount(uid[m].ravel(), minlength=N*(T+1))
    return m & (lens[uid] >= 5)

def join_R1(q, hot):
    """join consecutive QUALIFYING runs when day gap <=2; all days strictly between belong to it."""
    T, N = hot.shape; out = np.zeros_like(hot)
    for n in range(N):
        mm = q[:,n]
        if not mm.any(): continue
        d = np.diff(np.concatenate(([0], mm.view(np.int8), [0])))
        st = np.flatnonzero(d==1); en = np.flatnonzero(d==-1)-1
        segs = [[int(a),int(b)] for a,b in zip(st,en)]
        merged = [segs[0]]
        for a,b in segs[1:]:
            if a - merged[-1][1] - 1 <= 2: merged[-1][1] = b
            else: merged.append([a,b])
        for a,b in merged: out[a:b+1, n] = True
    return out

def join_R2(q, hot):
    """join qualifying runs that are adjacent in the FULL maximal-run list with gap<=2 non-hot days."""
    T, N = hot.shape; out = np.zeros_like(hot)
    for n in range(N):
        h = hot[:,n]
        if not h.any(): continue
        d = np.diff(np.concatenate(([0], h.view(np.int8), [0])))
        rst = np.flatnonzero(d==1); ren = np.flatnonzero(d==-1)-1
        keep = [(int(a),int(b)) for a,b in zip(rst,ren) if b-a+1 >= 5]
        if not keep: continue
        segs = [list(keep[0])]
        # only join if NO other maximal run lies between (i.e. consecutive in full list)
        allruns = list(zip(rst, ren))
        idxs = [i for i,r in enumerate(allruns) if r in keep]
        merged = [list(keep[0])]
        for i in range(1, len(keep)):
            prev_i, cur_i = idxs[i-1], idxs[i]
            adjacent = (cur_i == prev_i + 1)
            gap = keep[i][0] - merged[-1][1] - 1
            if adjacent and gap <= 2: merged[-1][1] = keep[i][1]
            else: merged.append(list(keep[i]))
        for a,b in merged: out[a:b+1, n] = True
    return out

# test correctness of runs_ge5_correct + joins on the toy case and random data
q = runs_ge5_correct(hot)
print('toy correct q:', q[:,0].astype(int))
print('toy R1       :', join_R1(q, hot)[:,0].astype(int))
print('toy R2       :', join_R2(q, hot)[:,0].astype(int))

rng = np.random.default_rng(0)
bad = 0
for trial in range(300):
    p = rng.uniform(0.3, 0.95)
    m = rng.random((92, 40)) < p
    if trial % 3 == 0:   # inject structured cases
        for c in range(0, 40, 7):
            m[5:12, c] = True; m[14:16, c] = True; m[18:25, c] = True; m[27, c] = True; m[29:36, c] = True
    # brute reference for runs>=5 marking
    ref = np.zeros_like(m)
    for n in range(40):
        h = m[:,n]; i = 0
        while i < 92:
            if h[i]:
                j = i
                while j+1 < 92 and h[j+1]: j += 1
                if j-i+1 >= 5: ref[i:j+1, n] = True
                i = j+1
            else: i += 1
    if not np.array_equal(runs_ge5_correct(m), ref): bad += 1; print('runs_ge5 MISMATCH trial', trial)
print('runs_ge5_correct vs brute mismatches:', bad, '/300')

# random-data comparison R1 vs R2
diffs = 0
for trial in range(300):
    p = rng.uniform(0.3, 0.95)
    m = rng.random((92, 40)) < p
    if trial % 2 == 0:
        for c in range(0, 40, 5):
            m[5:12, c] = True; m[13, c] = True; m[15:22, c] = True; m[24, c] = True; m[25, c] = True; m[27:34, c] = True
    q = runs_ge5_correct(m)
    r1 = join_R1(q, m); r2 = join_R2(q, m)
    if not np.array_equal(r1, r2): diffs += 1
print('R1 vs R2 differing trials:', diffs, '/300')
