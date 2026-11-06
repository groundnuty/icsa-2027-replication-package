import numpy as np
import pickle

# --- unit test 1: hazen quantile == MATLAB quantile (linear interp) ---
rng = np.random.default_rng(0)
x = rng.normal(0, 1, 121)
def matlab_quantile(x, p):
    xs = np.sort(x)
    h = 1 + p*(len(xs)-1)      # 1-indexed position
    lo = int(np.floor(h)); hi = min(lo+1, len(xs)-1)
    return xs[lo-1] + (h-lo)*(xs[hi]-xs[lo-1]) if lo < len(xs) else xs[-1]
for n in (1, 2, 11, 109, 121):
    xx = rng.normal(0,1,n)
    a = np.quantile(xx, 0.9, method='hazen')
    b = matlab_quantile(xx, 0.9)
    assert np.isclose(a, b, atol=1e-12), (n, a, b)
print("quantile test OK (hazen == MATLAB linear)")

# --- unit test 2: MHW run + join logic ---
def detect(hot_seq):
    """returns list of (start,end) 0-based inclusive merged MHWs per spec"""
    n = len(hot_seq)
    idx = [i for i in range(n) if hot_seq[i]]
    runs = []
    for i in idx:
        if runs and i == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], i)
        else:
            runs.append((i, i))
    runs = [r for r in runs if r[1]-r[0]+1 >= 5]
    merged = []
    for s,e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s,e))
    return merged

tests = [
    ([0]*4 + [1]*5 + [0]*3 + [1]*5, [(4,8)]),            # gap 3 -> not joined
    ([0]*4 + [1]*5 + [0]*2 + [1]*5, [(4,15)]),           # gap 2 -> joined
    ([0]*4 + [1]*5 + [0] + [1]*5,  [(4,14)]),            # gap 1 -> joined
    ([1]*4 + [0], []),                                   # only 4 -> none
    ([1]*5, [(0,4)]),
    ([1]*6 + [0]*2 + [1]*4, [(0,5)]),                    # 4-run not kept
    ([0]*3 + [1]*5 + [0]*2 + [1]*5 + [0]*2 + [1]*5, [(3,23)]),  # chain joins
    ([1]*5 + [0] + [1]*5, [(0,11)]),
]
for seq, exp in tests:
    got = detect(seq)
    assert got == exp, (seq, got, exp)
print("MHW logic test OK")

# --- inspect the found event ---
with open('/work/final.pkl','rb') as f:
    F = pickle.load(f)
mask, time_tgt = F['mask'], F['time_tgt']
ones = np.argwhere(mask == 1)
print("mask-1 cells (flat idx):", ones[:,0].unique(), "days:", [str(np.datetime64(time_tgt[d],'D')) for d in ones[:,1].unique()])
c = ones[0,0]
lati, loni = np.unravel_index(c, (60,60))
print("cell lat/lon:", 57.42+0.02*lati, 18.70+0.02*loni)
with open('/work/thr.pkl','rb') as f:
    T = pickle.load(f)
V_tgt = T['V_tgt'].reshape(92,3600)
s = V_tgt[4:15, c]  # June 5..15
th = F['thr_s'][T['doy_tgt'][4:15], None]
th = th.reshape(-1)
print(" date        SST     thr_s   hot")
for i,(d,ss,tt) in enumerate(zip(np.arange(5,16), s, th)):
    print(" ", str(np.datetime64(time_tgt[d],'D')), round(float(ss),2), round(float(tt),2), ss>=tt)
