
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
    fin = np.isfinite(ref)
    good = np.array_equal(np.isnan(ref), np.isnan(sm[i])) and np.allclose(ref[fin], sm[i][fin])
    if not good: ok=False; print("MISMATCH", d)
print("smoothing check final:", "ok" if ok else "FAIL")
# also compare against full recompute saved earlier
print("saved thr_s == fresh smooth:", np.allclose(x, sm, equal_nan=True))
