import numpy as np, os, time
# 0) does variable state persist between calls?
marker = '/work/work/_persist_test.txt'
if os.path.exists(marker):
    print('state persists:', open(marker).read())
else:
    with open(marker, 'w') as f:
        f.write('written at t0')
    print('first call, wrote marker')

# 1) Hazen quantile semantics: find the virtual-index formula that matches np.quantile(method='hazen')
rng = np.random.default_rng(42)
def hazen_my(x, q=0.9):
    xs = np.sort(x)
    n = len(xs)
    # candidate: 1-based h = q*(n+1) - 0.5
    h0 = q*(n+1) - 0.5 - 1  # 0-based
    lo = int(np.floor(h0)); hi = int(np.ceil(h0))
    lo = min(max(lo, 0), n-1); hi = min(max(hi, 0), n-1)
    g = h0 - np.floor(h0)
    g = 0.0 if lo == hi else g
    return xs[lo] + g*(xs[hi]-xs[lo])
def hazen_my2(x, q=0.9):
    xs = np.sort(x)
    n = len(xs)
    h0 = q*n + 0.5 - 1  # candidate 2: h = q*n + 0.5 (1-based)
    lo = int(np.floor(h0)); hi = int(np.ceil(h0))
    lo = min(max(lo, 0), n-1); hi = min(max(hi, 0), n-1)
    g = h0 - np.floor(h0)
    g = 0.0 if lo == hi else g
    return xs[lo] + g*(xs[hi]-xs[lo])
bad1 = bad2 = 0
for trial in range(300):
    n = rng.integers(1, 60)
    x = rng.normal(size=int(n))
    ref = np.quantile(x, 0.9, method='hazen')
    r1 = hazen_my(x); r2 = hazen_my2(x)
    if not np.isclose(ref, r1, rtol=0, atol=1e-12): bad1 += 1
    if not np.isclose(ref, r2, rtol=0, atol=1e-12): bad2 += 1
print('candidate1 (h=q(n+1)-0.5) mismatches:', bad1, '| candidate2 (h=qn+0.5) mismatches:', bad2)
x = np.arange(1., 11.)
print('n=10 x=1..10 hazen q0.9 ref:', np.quantile(x, 0.9, method='hazen'), 'cand1:', hazen_my(x), 'cand2:', hazen_my2(x))
# NaN behaviour of nanquantile vs quantile-on-valid
xn = x.copy(); xn[3] = np.nan
print('nanquantile(n,0.9,hazen):', np.nanquantile(xn, 0.9, method='hazen'),
      '| quantile(valid,0.9,hazen):', np.quantile(xn[:3].tolist()+xn[4:].tolist(), 0.9, method='hazen'))
