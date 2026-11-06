import numpy as np
print("numpy version:", np.__version__)
A = np.arange(366*2, dtype=float).reshape(366, 2)
i = 0
lst = [A[(i+k) % 366] for k in range(-15, 16)]
arr = np.array(lst)
print("np.array(lst).shape:", arr.shape)
print("np.mean(arr):", np.mean(arr), np.shape(np.mean(arr)))
print("np.mean(lst):", np.mean(lst), np.shape(np.mean(lst)))
print("arr.mean():", arr.mean())
print("arr.mean(axis=0):", arr.mean(axis=0))
# check the 31 rows expected
print("expected rows:", [A[j] for j in list(range(351,366))+list(range(0,16))][:3], "...")