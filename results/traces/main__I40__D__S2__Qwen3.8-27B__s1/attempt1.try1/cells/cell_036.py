import numpy as np
hot = np.load('/work/hot.npy'); mask = np.load('/work/mask.npy'); sea = np.load('/work/sea.npy')
T, C = hot.shape

prev = np.empty((T, C), bool); prev[0] = False; prev[1:] = hot[:-1]
nxt  = np.empty((T, C), bool); nxt[-1] = False; nxt[:-1] = hot[1:]
starts = (hot & ~prev)
end_idx = np.where(hot & ~nxt, np.broadcast_to(np.arange(T)[:, None], (T, C)), 0)
run_id_start = np.maximum.accumulate(np.where(starts, np.broadcast_to(np.arange(T)[:, None], (T, C)), 0), axis=0)
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
if not np.array_equal(mask, mask2):
    d = (mask != mask2)
    print("n differing cell-days:", int(d.sum()), "days:", np.flatnonzero(d.any(axis=1)))
    # where: which cells, which day ranges
    cd = np.flatnonzero(d)
    print("sample diffs (day, cell, mask, mask2):")
    for i in cd[:10]:
        k, c = divmod(int(i), C)
        print(k, c, mask[k,c], mask2[k,c], "hot:", hot[k-2:k+3, c].astype(int).tolist())
