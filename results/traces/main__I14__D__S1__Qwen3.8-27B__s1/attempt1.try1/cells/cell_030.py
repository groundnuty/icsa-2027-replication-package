import numpy as np
def runs_bool(v):
    pad = np.concatenate(([0], v.view(np.int8), [0]))
    idx = np.flatnonzero(np.diff(pad))
    if len(idx) == 0: return []
    p = np.vstack(idx).T
    return [(int(p[j,0]), int(p[j,1])-1) for j in range(p.shape[0])]

v = np.array([0,1,1,0,1,0,1,1,1,0], dtype=bool)
print("pad:", np.concatenate(([0], v.view(np.int8), [0])))
print("diff:", np.diff(np.concatenate(([0], v.view(np.int8), [0]))))
idx = np.flatnonzero(np.diff(np.concatenate(([0], v.view(np.int8), [0]))))
print("idx:", idx, idx.shape)
print("vstack:", np.vstack(idx), np.vstack(idx).shape)
p = np.vstack(idx).T
print("p:", p, p.shape)