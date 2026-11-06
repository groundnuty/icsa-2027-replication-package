
import numpy as np
xraw = np.load('/tmp/thr_raw.npy')[1:]
x = np.load('/tmp/thr_s.npy')
def smooth366(a2d):
    y = np.r_[a2d[-15:], a2d, a2d[:15]]
    out = np.empty_like(a2d)
    for i in range(366):
        out[i] = y[i:i+31].mean(axis=0)
    return out
sm = smooth366(xraw)
ok=True
for d in [1,20,60,153,244,352,366]:
    i=d-1
    idxs = np.array([(i+k)%366 for k in range(-15,16)])
    ref = xraw[idxs].mean(axis=0)
    bothnan = np.isnan(ref)&np.isnan(sm[i])
    fin = np.isfinite(ref)
    good = np.all(bothnan | (fin & np.isclose(ref[fin], sm[i][fin]))) and np.all(np.isnan(ref)==np.isnan(sm[i]))
    if not good: ok=False; print("MISMATCH", d)
print("smoothing check final:", "ok" if ok else "FAIL")
