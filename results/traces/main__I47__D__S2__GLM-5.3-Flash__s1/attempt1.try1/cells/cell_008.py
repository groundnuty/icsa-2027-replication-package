import numpy as np

def hazen_manual(x, q=0.9):
    v = np.sort(x[np.isfinite(x)])
    n = len(v)
    if n == 0: return np.nan
    h = n*q - 0.5
    lo = int(np.floor(h)); hi = int(np.ceil(h))
    lo = min(lo, n-1); hi = min(hi, n-1)
    return v[lo] + (h - lo)*(v[hi] - v[lo])

tests = [([1.,2.,4.], 2.4), ([1.,2.,3.,4.], 3.35), (list(range(1,11)), 9.5), ([5.], 5.)]
for arr, exp in tests:
    a = np.array(arr)
    m = hazen_manual(a)
    try: nq = np.quantile(a, 0.9, method='hazen')
    except Exception as e: nq = str(e)
    print('arr n=%d  manual=%.4f  np=%.4f  expected=%.4f' % (len(a), m, nq, exp))

rng = np.random.default_rng(0)
bad = 0
for trial in range(2000):
    n = rng.integers(1, 60)
    a = rng.normal(size=int(n))
    hm = hazen_manual(a)
    hn = np.quantile(a, 0.9, method='hazen')
    if not np.isclose(hm, hn, rtol=0, atol=1e-12):
        bad += 1
        if bad <= 3: print('MISMATCH n=%d manual=%.10f np=%.10f' % (n, hm, hn))
print('random trials mismatches:', bad, '/ 2000')

print('nanmean [1,2,nan,4]:', np.nanmean(np.array([1.,2.,np.nan,4.])), '(expect 2.3333)')
print('sort NaN placement:', np.sort(np.array([3.,np.nan,1.])))
print('nansum:', np.nansum(np.array([1.,np.nan,2.])))
