import numpy as np
A = np.random.rand(7, 366)
idx = np.array([[(d-15+k) % 366 for k in range(31)] for d in range(366)])
print("idx", idx.shape, idx.min(), idx.max())
B = A.take(idx, axis=1)
print("take result:", B.shape)
# alternative: advanced indexing
C = A[:, idx]
print("advanced:", C.shape)
S = C.mean(axis=2)
print("smoothed:", S.shape)