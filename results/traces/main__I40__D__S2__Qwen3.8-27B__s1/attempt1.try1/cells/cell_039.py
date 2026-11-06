import numpy as np
hot = np.load('/work/hot.npy'); mask = np.load('/work/mask.npy'); sea = np.load('/work/sea.npy')
T, C = hot.shape

prev = np.empty((T, C), bool); prev[0] = False; prev[1:] = hot[:-1]
nxt  = np.empty((T, C), bool); nxt[-1] = False; nxt[:-1] = hot[1:]
starts = (hot & ~prev)
ends   = (hot & ~nxt)
AR = np.broadcast_to(np.arange(T)[:, None], (T, C))
run_id_start = np.maximum.accumulate(np.where(starts, AR, 0), axis=0)
end_idx = np.where(ends, AR, T + 10)
run_id_end = np.minimum.accumulate(end_idx[::-1, :], axis=0)[::-1]
runlen = run_id_end - run_id_start + 1
R = (runlen >= 5) & hot

Rd = np.zeros_like(R)
for k in range(-2, 3):
    sh = np.roll(R, k, axis=0)
    if k > 0: sh[:k] = False
    if k < 0: sh[T+k:] = False
    Rd |= sh

lab = np.zeros_like(Rd, dtype=np.int64)
cur = 0
for c in range(C):
    r = Rd[:, c]
    if not r.any(): continue
    b = np.flatnonzero(r & ~np.r_[True, r[:-1]])
    for j, s in enumerate(b):
        e = (b[j+1]-1) if j+1 < len(b) else T-1
        cur += 1
        lab[s:e+1, c] = cur

mask2 = np.zeros_like(R)
for c in range(C):
    for labv in np.unique(lab[:, c]):
        if labv == 0: continue
        rr = np.flatnonzero(R[:, c] & (lab[:, c] == labv))
        mask2[rr.min():rr.max()+1, c] = True

print("masks identical:", np.array_equal(mask, mask2))
d = mask != mask2
print("n differing cell-days:", int(d.sum()))
# also verify: mask is subset of 'hot or gap<=2 between runs' and matches sea cells
print("mask nonzero only in sea cells:", np.all(mask[:, ~sea] == 0))
# event boundaries
active = mask.any(axis=1)
print("active days:", np.flatnonzero(active).tolist())
