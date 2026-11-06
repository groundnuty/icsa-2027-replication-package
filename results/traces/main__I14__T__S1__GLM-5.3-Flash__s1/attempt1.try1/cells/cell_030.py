import numpy as np, pickle, warnings
with open('/tmp/stepA2.pkl','rb') as fh: A = pickle.load(fh)
mem = A['mem']; arr_sea = A['arr_sea']

i = 183; cell = 10
pool2d = arr_sea[mem[:, i-1]]
pool1d = pool2d[:, cell]
print("pool shape:", pool2d.shape, "nan count:", int((~np.isfinite(pool2d)).sum()))
q2d = np.nanquantile(pool2d, 0.9, axis=0, method='hazen')[cell]
q1d = np.nanquantile(pool1d, 0.9, method='hazen')
print("q2d:", q2d, "q1d:", q1d, "diff:", q2d - q1d)
# sorted manual
s = np.sort(pool1d)
n = len(s); pos = 0.9*(n+1)
lo = int(np.floor(pos)); frac = pos - lo
print("n:", n, "pos:", pos, "s[lo-1]:", s[lo-1], "s[lo]:", s[lo], "manual:", s[lo-1] + frac*(s[lo]-s[lo-1]))
# small repro test
rng = np.random.default_rng(0)
x = rng.random((121, 5))
print("small test max diff:", np.abs(np.nanquantile(x, 0.9, axis=0, method='hazen') - np.array([np.nanquantile(x[:, c], 0.9, method='hazen') for c in range(5)])).max())
print("numpy:", np.__version__)
# check with the actual pool but reshaped transposes
q2d_T = np.nanquantile(pool2d.T, 0.9, axis=1, method='hazen')[cell]
print("q2d_T:", q2d_T)
q2d_copy = np.nanquantile(pool2d.copy(order='C'), 0.9, axis=0, method='hazen')[cell]
print("q2d_copy:", q2d_copy)
