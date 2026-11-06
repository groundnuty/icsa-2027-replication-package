import numpy as np, pickle
from numpy.lib.stride_tricks import sliding_window_view

def smooth31_wrap(a):
    b = np.concatenate([a[-15:], a, a[:15]], axis=0)
    return sliding_window_view(b, 31, axis=0).mean(axis=-1)

rng = np.random.default_rng(1)
a = rng.standard_normal((366, 7))
s = smooth31_wrap(a)
# explicit loop check
ok = True
for d in range(0, 366, 53):
    idx = [(d + k) % 366 for k in range(-15, 16)]
    m = a[idx].mean(axis=0)
    if not np.allclose(s[d], m):
        ok = False
        print("mismatch at", d)
print("explicit loop check:", ok)

# corrected wrap check for real threshold
with open("/tmp/thr.pkl","rb") as f: T = pickle.load(f)
thr, thr_s = T["thr"], T["thr_s"]
idx = [(0 + k) % 366 for k in range(-15, 16)]
print("real wrap check day1:", np.allclose(thr_s[0], thr[idx].mean(axis=0)))
