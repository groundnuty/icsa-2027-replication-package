import numpy as np
# 1) verify numpy's 'hazen' against Hyndman-Fan type 5 on small arrays
def hf5(x, p):
    x = np.sort(x); n = len(x)
    h = (n+1)*p
    i = int(np.floor(h))
    if i >= n: return x[-1]
    f = h - i
    return x[i-1] + f*(x[i]-x[i-1])  # 1-based indexing
a = np.array([3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0, 5.0, 3.0])
print("n=10 p=0.9: numpy", np.nanquantile(a, 0.9, method='hazen'), " HF5", hf5(a, 0.9))
b = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print("n=5 p=0.9: numpy", np.nanquantile(b, 0.9, method='hazen'), " HF5", hf5(b, 0.9))
# with nans
c = np.array([1.0, np.nan, 3.0, 4.0, np.nan, 5.0])
print("n=4 p=0.9: numpy", np.nanquantile(c, 0.9, method='hazen'), " HF5", hf5(c[~np.isnan(c)], 0.9))

# 2) check the cell(0,0) pool size/nans
import warnings; warnings.filterwarnings("ignore")
D = np.load('/work/region_data.npz')
base = D['base']; t_base = D['t_base']
cum = np.concatenate([[0], np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])])
def doy_of(strs):
    m = np.array([int(s[5:7]) for s in strs]); d = np.array([int(s[8:10]) for s in strs])
    return cum[m-1] + d
doyb = doy_of(t_base)
in_base = (t_base >= "1992-01-01") & (t_base <= "2002-12-31")
idx = np.where((doyb == 153) & in_base)[0]
print("anchor dates for June-1:", [t_base[i] for i in idx])
pool = np.concatenate([base[i-5:i+6, 0, 0] for i in idx])
print("cell(0,0) pool n:", len(pool), "nans:", np.isnan(pool).sum())
p2 = pool[~np.isnan(pool)]
print("q90 hazen: %.4f  manual HF5: %.4f" % (np.nanquantile(pool, 0.9, method='hazen'), hf5(pool, 0.9)))
print("sorted top 6 of pool:", p2[-6:])
print("n =", len(p2), " h =", (len(p2)+1)*0.9)
