import numpy as np, time
# unit test smoother semantics: out[i] = mean(a[(i+k) mod 366]) for k=-15..15
def smooth366(a):
    S = np.zeros_like(a)
    for k in range(-15, 16):
        S += np.roll(a, -k, axis=0)
    return S / 31.0

def smooth366_ref(a):
    n = a.shape[0]
    out = np.empty_like(a)
    for i in range(n):
        idx = [(i + k) % n for k in range(-15, 16)]
        out[i] = a[idx].mean(axis=0)
    return out

rng = np.random.default_rng(7)
a = rng.normal(size=(366, 3, 2))
r1 = smooth366(a); r2 = smooth366_ref(a)
print('smoother matches reference:', np.allclose(r1, r2, rtol=0, atol=1e-12), '| max abs diff:', np.abs(r1-r2).max())
# small-n behaviour check with explicit numbers
b = np.arange(1., 7.).reshape(6, 1)  # n=6, window would be 31 but only 6 days: just checks roll wrap formula
def roll_wrap(x, k):
    return np.roll(x, -k, axis=0)
print('roll(a6,-1):', roll_wrap(b, -1).ravel(), '(expect 2,3,4,5,6,1)')
print('roll(a6, 1):', roll_wrap(b, 1).ravel(), '(expect 6,1,2,3,4,5)')

# benchmark nanquantile on pool shape (121, 60, 60) and nanmean
pool = rng.normal(285, 2, size=(121, 60, 60))
pool[:, :10] = np.nan
t0 = time.time()
q = np.nanquantile(pool, 0.9, axis=0, method='hazen')
t1 = time.time()
m = np.nanmean(pool, axis=0)
t2 = time.time()
print(f'nanquantile (121,60,60): {t1-t0:.3f} s | nanmean: {t2-t1:.3f} s')
print(f'estimated for 366 slots: quantile {366*(t1-t0):.1f} s, mean {366*(t2-t1):.1f} s')
