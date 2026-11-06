import numpy as np
b = np.array([0,1,1,1,0,0,1,1,1,1,1,1]+[0]*80, dtype=bool)
n = len(b); idx = np.arange(n)[:, None]
d = np.where(b, idx, 0); d = np.maximum.accumulate(d, axis=0)
e = np.where(~b, idx, n); e = np.minimum.accumulate(e[::-1], axis=0)[::-1]
print("d:", d.ravel()[:14])
print("e:", e.ravel()[:14])
runlen = e - d
cores = b & (runlen >= 5)
print("runlen:", runlen.ravel()[:14])
print("cores:", cores.ravel()[:14])
