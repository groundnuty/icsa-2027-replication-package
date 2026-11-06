import numpy as np
from scipy.ndimage import uniform_filter1d
rng = np.random.default_rng(0)
x = rng.normal(10, 1, 366)

def circ_mine(x):
    a = np.concatenate([x[-15:], x, x[:15]])
    c = np.concatenate([[0.0], np.cumsum(a)])
    j = np.arange(1, 367) + 14
    return (c[j+16] - c[j-15]) / 31.0

def circ_manual(x):  # output[k] = mean(x[(k-15..k+15) mod 366])
    return np.array([np.mean(x[(np.arange(k-15, k+16)) % 366]) for k in range(366)])

m1 = circ_mine(x); m2 = circ_manual(x)
s_wrap = uniform_filter1d(x, size=31, mode='wrap')
s_grid = uniform_filter1d(x, size=31, mode='grid-wrap')
print('mine vs manual:', np.abs(m1-m2).max())
print('mine vs scipy wrap:', np.abs(m1-s_wrap).max())
print('mine vs scipy grid-wrap:', np.abs(m1-s_grid).max())
# brute force expected for a few positions
for k in [0, 1, 180, 365]:
    exp = x[(np.arange(k-15, k+16)) % 366].mean()
    print(k, 'mine %.12f manual %.12f wrap %.12f grid %.12f exp %.12f' % (m1[k], m2[k], s_wrap[k], s_grid[k], exp))