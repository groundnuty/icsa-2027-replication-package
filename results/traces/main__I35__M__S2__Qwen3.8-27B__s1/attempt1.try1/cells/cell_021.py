import numpy as np

X = np.load("/tmp/X.npy"); p3 = np.load("/tmp/p3.npy"); sea = np.load("/tmp/sea.npy"); M = np.load("/tmp/M.npy")
Xsea = X[:, sea]
mhw = np.load("/tmp/mhw.npy").astype(bool)

# --- B) pipeline run+merge vs naive reference, exact same code ---
def pipeline_cell(hot):
    nt = len(hot)
    hpad = np.array([False] + list(hot) + [False])
    d = np.diff(hpad.astype(np.int8))
    starts = np.where(d == 1)[0]; ends = np.where(d == -1)[0]
    runs = [(s, e) for s, e in zip(starts, ends) if e - s + 1 >= 5]
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    out = np.zeros(nt, bool)
    for s, e in merged:
        out[s-1:e] = True
    return out

def ref_cell(hot):
    n = len(hot); out = np.zeros(n, bool)
    i = 0; runs = []
    while i < n:
        if hot[i]:
            j = i
            while j + 1 < n and hot[j+1]: j += 1
            if j - i + 1 >= 5: runs.append([i, j])
            i = j + 1
        else: i += 1
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2: merged[-1][1] = e
        else: merged.append([s, e])
    for s, e in merged: out[s:e+1] = True
    return out

rng = np.random.default_rng(1)
ok = True
for trial in range(5000):
    hot = rng.random(92) < rng.uniform(0.02, 0.8)
    if not np.array_equal(pipeline_cell(hot), ref_cell(hot)):
        ok = False; print("MISMATCH trial", trial, hot); break
print("B) run+merge logic check:", "PASS" if ok else "FAIL")

# --- C) end-to-end single (cell, doy) ---
c = 0
d = 200
pool_idx = np.where(M[d-1])[0]
vals = Xsea[pool_idx, c]; vals = vals[np.isfinite(vals)]
def hazen_ref(x, p=0.9):
    x = np.sort(x); n = len(x)
    pos = n * p - 0.5
    i = int(np.floor(pos)); f = pos - i
    return x[-1] if i >= n - 1 else x[i] + f * (x[i+1] - x[i])
thr_u = np.full(366, np.nan)
for dd in range(1, 367):
    if dd == 60: continue
    v = Xsea[M[dd-1], c]; v = v[np.isfinite(v)]
    thr_u[dd-1] = hazen_ref(v)
thr_u[59] = (thr_u[58] + thr_u[60]) / 2
w = (199 - 15 + np.arange(31)) % 366
thr_u_s = thr_u[w].mean()
thr_s = np.load("/tmp/thr_s.npy")
print("C) cell0 doy200: ref raw=%.6f ref smoothed=%.6f stored=%.6f" % (hazen_ref(vals), thr_u_s, thr_s[199, c]))
assert abs(thr_u_s - thr_s[199, c]) < 1e-9
print("C) PASS")

# --- D) daily active pattern & events ---
tdates = np.datetime64("2009-06-01") + np.arange(92)
active = mhw.any(axis=1)
print("D) active pattern (2009-06-01 + 91):")
for row in range(0, 92, 10):
    line = "".join("#" if active[i] else "." for i in range(row, min(row+10, 92)))
    print("   ", str(tdates[row])[:10], line)
dd = np.diff(np.concatenate([[0], active.astype(int), [0]]))
ev_s = np.where(dd == 1)[0]; ev_e = np.where(dd == -1)[0] - 1
print("events:", [(str(tdates[s]), str(tdates[e]), int(e-s+1)) for s, e in zip(ev_s, ev_e)])
