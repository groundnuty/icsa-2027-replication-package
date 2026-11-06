import numpy as np
hot = np.load('/work/hot.npy'); mask = np.load('/work/mask.npy')
c = 438
h = hot[:, c]
print("hot  (0=non-hot):", ''.join('#' if x else '.' for x in h))
print("mask:", ''.join('X' if x else '.' for x in mask[:, c]))
# manual runs
prev = np.r_[False, h[:-1]]; nxt = np.r_[h[1:], False]
starts = np.flatnonzero(h & ~prev); ends = np.flatnonzero(h & ~nxt)
print("starts:", starts.tolist())
print("ends:  ", ends.tolist())
print("lens:  ", (ends-starts+1).tolist())
