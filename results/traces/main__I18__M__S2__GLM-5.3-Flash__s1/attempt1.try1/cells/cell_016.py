import numpy as np

hot = np.load("/tmp/hot.npy"); sea = np.load("/tmp/sea.npy")
T = hot.shape[0]
hot_cells = hot.reshape(T, -1)[:, sea.reshape(-1)]
nsea = hot_cells.shape[1]

def runs_of(seq):
    runs = []
    t = 0; L = len(seq)
    while t < L:
        if seq[t]:
            u = t
            while u+1 < L and seq[u+1]: u += 1
            runs.append([t, u]); t = u+1
        else:
            t += 1
    return runs

def reading_A(seq):
    """runs>=5 are MHWs; join MHWs separated by gaps<=2; gap days belong."""
    runs = runs_of(seq)
    mhw_runs = [r for r in runs if r[1]-r[0]+1 >= 5]
    # chain-join mhw_runs with gap<=2
    merged = []
    for r in mhw_runs:
        if merged and r[0]-merged[-1][1]-1 <= 2:
            merged[-1][1] = r[1]
        else:
            merged.append(list(r))
    out = np.zeros(len(seq), bool)
    for s, e in merged: out[s:e+1] = True
    return out

def reading_B(seq):
    """join all hot runs across gaps<=2, then keep merged runs >=5."""
    runs = runs_of(seq)
    merged = []
    for r in runs:
        if merged and r[0]-merged[-1][1]-1 <= 2:
            merged[-1][1] = r[1]
        else:
            merged.append(list(r))
    out = np.zeros(len(seq), bool)
    for s, e in merged:
        if e-s+1 >= 5: out[s:e+1] = True
    return out

A = np.zeros((T, nsea), bool); B = np.zeros((T, nsea), bool)
for n in range(nsea):
    A[:, n] = reading_A(hot_cells[:, n])
    B[:, n] = reading_B(hot_cells[:, n])
print("masks identical:", np.array_equal(A, B))
print("A cell-days:", A.sum(), " B cell-days:", B.sum())
activeA = A.any(axis=1); activeB = B.any(axis=1)
print("active days A:", activeA.sum(), " B:", activeB.sum())
print("active identical:", np.array_equal(activeA, activeB))
if not np.array_equal(A, B):
    d = A ^ B
    print("differing cell-days:", d.sum())
    idx = np.where(d.any(axis=1))[0]
    print("days with differences:", idx.min(), "..", idx.max(), "count days:", len(idx))
    # example cell
    cn = np.where(d[idx[0]])[0][0]
    print("example cell hot:", "".join("1" if x else "0" for x in hot_cells[:, cn]))
    print("example cell A  :", "".join("1" if x else "0" for x in A[:, cn]))
    print("example cell B  :", "".join("1" if x else "0" for x in B[:, cn]))
