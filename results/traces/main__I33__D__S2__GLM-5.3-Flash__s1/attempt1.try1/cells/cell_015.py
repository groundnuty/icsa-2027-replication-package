import numpy as np
ext = np.load('/work/ext.npy')
pool = np.load('/work/pool.npy', allow_pickle=True)
clim_raw = np.full((366, 60, 60), np.nan)
for d in range(1, 367):
    if d == 60: continue
    vals = ext[pool[d-1]]
    with np.errstate(all='ignore'):
        clim_raw[d-1] = np.nanmean(vals, axis=0)
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])

def circ_smooth31(x):
    a = np.concatenate([x[-15:], x, x[:15]], axis=0)
    c = np.concatenate([np.zeros((1,)+x.shape[1:]), np.cumsum(a, axis=0)], axis=0)
    j = np.arange(1, 367) + 14
    return (c[j+16] - c[j-15]) / 31.0

# minimal single-column test
x = clim_raw[:, 0, 0].copy()
print('x finite:', np.isfinite(x).all(), 'len', len(x))
a = np.concatenate([x[-15:], x, x[:15]])
c = np.concatenate([[0.0], np.cumsum(a)])
sm_func = circ_smooth31(x)
man = np.array([np.mean(x[(np.arange(d-15, d+16)) % 366]) for d in range(1, 367)])
diff = np.abs(sm_func - man)
print('single col max diff:', diff.max())
k = 199
print('k=199: func %.12f man %.12f' % (sm_func[k], man[k]))
print('direct: c[230]-c[199] = %.12f vs sum(a[199:231]) = %.12f' % (c[k+31]-c[k], a[k:k+31].sum()))
print('equal arrays?', np.array_equal(a[k:k+31], x[(np.arange(k-15,k+16)) % 366]))
# brute-force recompute c[k+31]-c[k] definition: c[m] = sum(a[0:m])
print('c[230] check:', c[230], np.sum(a[:230]), 'c[199] check:', c[199], np.sum(a[:199]))