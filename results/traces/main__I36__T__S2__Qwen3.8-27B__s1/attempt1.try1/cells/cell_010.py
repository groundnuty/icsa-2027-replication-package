import numpy as np
# 1) verify hazen quantile vs manual computation
rng = np.random.default_rng(42)
x = rng.random(121)
q_np = float(np.quantile(x, 0.9, method='hazen'))
xs = np.sort(x)
n = len(xs)
h = (n + 1/3)*0.9 - 1/3   # HF type 5 position (1-based)
i0 = int(np.floor(h))
frac = h - i0
q_manual = xs[i0-1] + frac*(xs[i0]-xs[i0-1]) if frac>0 and i0<n else xs[i0-1]
print('np', q_np, 'manual', q_manual, 'match', np.isclose(q_np, q_manual))

# 2) verify run-find + merge logic on synthetic hot pattern
def mhw_of(h):
    h = np.asarray(h, bool)
    pad = np.concatenate(([0], h.view(np.uint8), [0]))
    diff = np.diff(pad.astype(np.int8))
    stt = np.flatnonzero(diff==1); en = np.flatnonzero(diff==-1)-1
    runs = [(s,e) for s,e in zip(stt,en) if e-s+1>=5]
    merged=[]
    for s,e in runs:
        if merged and (s - merged[-1][1] - 1) <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s,e))
    out = np.zeros_like(h, bool)
    for s,e in merged: out[s:e+1]=True
    return merged, out
# case A: 5-day run, gap 2, 5-day run -> one MHW of length 12
hA = [1]*5+[0]*2+[1]*5+[0]*3+[1]*5+[0]*2+[1]*6
mA,_ = mhw_of(hA)
print('A runs:', mA)   # expect [(0,8),(12,20)]
# case B: gap 3 -> separate
hB = [1]*5+[0]*3+[1]*5
print('B runs:', mhw_of(hB)[0])  # expect [(0,4),(8,12)]
# case C: 4-day run alone -> nothing; then 5-day run
hC = [1]*4+[0]+[1]*5
print('C runs:', mhw_of(hC)[0])  # expect [(5,9)]
# case D: chaining gaps: 5, gap2, 5, gap2, 5 -> one
hD = [1]*5+[0]*2+[1]*5+[0]*2+[1]*5
print('D runs:', mhw_of(hD)[0])  # expect [(0,19)]
# case E: single 5-run
hE = [0]*3+[1]*5+[0]*3
print('E runs:', mhw_of(hE)[0])  # expect [(3,7)]
