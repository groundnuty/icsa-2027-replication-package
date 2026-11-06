import numpy as np, os, sys, time
print('numpy', np.__version__)
# test hazen quantile
x = np.arange(1., 11.)
print('hazen q0.9 of 1..10:', np.quantile(x, 0.9, method='hazen'))
# manual type 5: h = n*p + 0.5
def t5(x, p):
    xs = np.sort(x); n = len(xs); h = n*p + 0.5
    lo = int(np.floor(h)); hi = int(np.ceil(h))
    if lo < 1: return xs[0]
    if hi > n: return xs[-1]
    return xs[lo-1] + (h-lo)*(xs[hi-1]-xs[lo-1])
print('manual type5    :', t5(x, 0.9))

# persistence check
os.makedirs('cache', exist_ok=True)
with open('cache/persist.txt','w') as f: f.write('ok')
print('cwd', os.getcwd())

# fs listing behaviour
import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
t0=time.time()
try:
    allf = fs.find(base)
    print('find count', len(allf), 'time', time.time()-t0)
    print(allf[0], allf[-1])
except Exception as e:
    print('find ERR', type(e).__name__, str(e)[:200])
t0=time.time()
print('exists one:', fs.exists(f'{base}/sst_19920615.nc'), 'time', time.time()-t0)
