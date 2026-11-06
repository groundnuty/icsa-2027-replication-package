import numpy as np
A = np.arange(366*2, dtype=float).reshape(366, 2)
print("A shape", A.shape)
i = 0
lst = [A[(i+k) % 366] for k in range(-15, 16)]
print("n elems:", len(lst), "elem0 type:", type(lst[0]), "elem0:", lst[0] if lst[0].ndim else lst[0])
m = np.mean(lst)
print("mean shape:", np.shape(m), m)