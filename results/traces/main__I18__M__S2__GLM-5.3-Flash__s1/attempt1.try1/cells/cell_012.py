import numpy as np

hot = np.load("/tmp/hot.npy")          # (92,60,60) bool
sea = np.load("/tmp/sea.npy")          # (60,60) bool
T = hot.shape[0]
hot_cells = hot.reshape(T, -1)[:, sea.reshape(-1)]   # (92, nsea)
nsea = hot_cells.shape[1]

def detect_runs(hot_seq):
    """runs>=5, join gaps of 1-2. Returns bool array same length."""
    T = len(hot_seq)
    ext = np.concatenate([[0], hot_seq.astype(np.int8), [0]])
    delta = np.diff(ext)
    starts = np.where(delta == 1)[0] - 1     # 0-based inclusive
    ends = np.where(delta == -1)[0] - 2
    if len(starts) == 0:
        return np.zeros(T, bool)
    # join gaps <= 2
    merged_s, merged_e = [starts[0]], [ends[0]]
    for s, e in zip(starts[1:], ends[1:]):
        gap = s - merged_e[-1] - 1
        if gap <= 2:
            merged_e[-1] = e
        else:
            merged_s.append(s); merged_e.append(e)
    out = np.zeros(T, bool)
    for s, e in zip(merged_s, merged_e):
        if e - s + 1 >= 5:
            out[s:e+1] = True
    return out

def detect_runs_bruteforce(hot_seq):
    """Independent implementation for cross-check."""
    T = len(hot_seq)
    mask = np.zeros(T, bool)
    # find all maximal runs
    runs = []
    t = 0
    while t < T:
        if hot_seq[t]:
            u = t
            while u + 1 < T and hot_seq[u+1]:
                u += 1
            runs.append((t, u))
            t = u + 1
        else:
            t += 1
    # merge runs separated by gaps of 1-2
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(r)
    for s, e in merged:
        if e - s + 1 >= 5:
            mask[s:e+1] = True
    return mask

# cross-check both implementations on every cell
mhw_cells = np.zeros((T, nsea), bool)
for n in range(nsea):
    a = detect_runs(hot_cells[:, n])
    b = detect_runs_bruteforce(hot_cells[:, n])
    assert np.array_equal(a, b), n
    mhw_cells[:, n] = a
print("implementations agree on all", nsea, "cells")
print("mhw sea-cell-days:", mhw_cells.sum(), "of", T*nsea)

active = mhw_cells.any(axis=1)
print("active days:", active.sum(), "of", T)
print("active sequence:", "".join("1" if a else "0" for a in active))
np.save("/tmp/mhw_cells.npy", mhw_cells)
np.save("/tmp/active.npy", active)
