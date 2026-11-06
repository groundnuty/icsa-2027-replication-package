import numpy as np

def detect_runs(hot_seq):
    """runs>=5, join gaps of 1-2. Correct version."""
    hot_seq = np.asarray(hot_seq)
    T = len(hot_seq)
    ext = np.concatenate([[0], hot_seq.astype(np.int8), [0]])
    delta = np.diff(ext)
    starts = np.where(delta == 1)[0]        # ext index i+1 -> seq index i
    ends = np.where(delta == -1)[0] - 1     # ext index i   -> seq index i-1
    if len(starts) == 0:
        return np.zeros(T, bool)
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
    hot_seq = list(hot_seq)
    T = len(hot_seq)
    mask = np.zeros(T, bool)
    runs = []
    t = 0
    while t < T:
        if hot_seq[t]:
            u = t
            while u + 1 < T and hot_seq[u+1]:
                u += 1
            runs.append((t, u)); t = u + 1
        else:
            t += 1
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

for seq in ["1111101111", "11111011111", "1111011111", "11110111101111",
            "11110111100111", "1111111", "111110", "00011111000001111100",
            "1111101111011111", "1111101111001111", "11101110111", "1101101101",
            "10111011111", "111110111110111", "011110111110111110", "11111"]:
    a = detect_runs([c == "1" for c in seq])
    b = detect_runs_bruteforce([c == "1" for c in seq])
    assert np.array_equal(a, b), (seq, a, b)
    print(f"{seq}: {''.join('1' if x else '.' for x in a)}")

hot = np.load("/tmp/hot.npy"); sea = np.load("/tmp/sea.npy")
T = hot.shape[0]
hot_cells = hot.reshape(T, -1)[:, sea.reshape(-1)]
nsea = hot_cells.shape[1]
mhw_cells = np.zeros((T, nsea), bool)
for n in range(nsea):
    a = detect_runs(hot_cells[:, n]); b = detect_runs_bruteforce(hot_cells[:, n])
    assert np.array_equal(a, b), n
    mhw_cells[:, n] = a
print("implementations agree on all", nsea, "cells")
print("mhw sea-cell-days:", mhw_cells.sum(), "of", T*nsea)
active = mhw_cells.any(axis=1)
print("active days:", active.sum(), "of", T)
print("active:", "".join("1" if a else "0" for a in active))
np.save("/tmp/mhw_cells.npy", mhw_cells); np.save("/tmp/active.npy", active)
