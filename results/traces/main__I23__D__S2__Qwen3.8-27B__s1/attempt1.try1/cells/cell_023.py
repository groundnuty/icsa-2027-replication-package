import numpy as np
import pickle

def detect(hot_seq):
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
    ([0]*4 + [1]*5 + [0]*3 + [1]*5, [(4,8),(12,16)]),   # gap 3 -> separate
    ([0]*4 + [1]*5 + [0]*2 + [1]*5, [(4,15)]),          # gap 2 -> joined
    ([0]*4 + [1]*5 + [0] + [1]*5,  [(4,14)]),           # gap 1 -> joined
    ([1]*4 + [0], []),
    ([1]*5, [(0,4)]),
    ([1]*6 + [0]*2 + [1]*4, [(0,5)]),
    ([0]*3 + [1]*5 + [0]*2 + [1]*5 + [0]*2 + [1]*5, [(3,23)]),
    ([1]*5 + [0] + [1]*5, [(0,11)]),
    ([1]*5 + [0]*3 + [1]*5, [(0,4),(9,13)]),
]
for seq, exp in tests:
    got = detect(seq)
    assert got == exp, (seq, got, exp)
print("MHW logic test OK")

with open('/work/final.pkl','rb') as f:
    F = pickle.load(f)
with open('/work/thr.pkl','rb') as f:
    T = pickle.load(f)
mask, time_tgt = F['mask'], F['time_tgt']
ones = np.argwhere(mask == 1)
print("mask-1 cells (flat):", ones[:,0].unique(), "days:", [str(np.datetime64(time_tgt[d],'D')) for d in ones[:,1].unique()])
c = ones[0,0]
lati, loni = np.unravel_index(c, (60,60))
print("cell lat/lon: %.4f %.4f" % (57.42+0.02*lati, 18.70+0.02*loni))
V = T['V_tgt'].reshape(92,3600)
th_s = F['thr_s'][T['doy_tgt']]
print(" date       SST     thr_s    hot?")
for d in range(4, 16):
    print("  ", str(np.datetime64(time_tgt[d],'D')), "%.2f" % V[d,c], "%.2f" % th_s[d], bool(V[d,c] >= th_s[d]))
