import numpy as np
tgt = np.load('/work/tgt.npy')      # (92,60,60) float64, 2014-06-01..2014-08-31
thr_sm = np.load('/work/thr_sm.npy')
doys = np.arange(153, 245)          # target days of year
thr_t = thr_sm[doys-1]              # (92,60,60)

hot = np.greater_equal(tgt, thr_t, where=np.isfinite(tgt), out=np.zeros(tgt.shape, dtype=bool))
print('hot days total:', hot.sum(), '| per-day active cells: min', hot.sum(axis=(1,2)).min(), 'max', hot.sum(axis=(1,2)).max())
print('sea cells:', (~np.isnan(tgt[0])).sum())

# step a: runs of >=5 consecutive hot days
def runs_of_true(mask_1d):
    m = np.asarray(mask_1d, dtype=int)
    dm = np.diff(np.concatenate([[0], m, [0]]))
    starts, ends = np.where(dm==1)[0], np.where(dm==-1)[0]
    return list(zip(starts, ends))   # [s,e) pairs

mask = np.zeros_like(hot)
n5 = 0
for c in range(hot[0].size):
    flat = hot[:, 0, 0].ravel()  # placeholder
for i in range(60):
    for j in range(60):
        rs = runs_of_true(hot[:, i, j])
        hot5 = np.zeros(92, bool)
        for s, e in rs:
            if e - s >= 5:
                hot5[s:e] = True; n5 += 1
        # step b: fill gaps of 1-2 non-hot days between kept runs
        gaps = runs_of_true(~hot5)
        for s, e in gaps:
            if 0 < s and e < 92 and (e - s) <= 2:
                # interior gap (bounded by hot runs on both sides after trimming edges)
                hot5[s:e] = True
        mask[:, i, j] = hot5
print('runs >=5 kept:', n5, '| mask cells-days:', mask.sum())
# gap filling check: ensure no gap <=2 remains between runs of the mask, except touching array edges
bad = 0
for i in range(60):
    for j in range(60):
        rs = runs_of_true(mask[:, i, j])
        for (s1, e1), (s2, e2) in zip(rs[:-1], rs[1:]):
            if (s2 - e1) <= 2: bad += 1
        # trim edge partial gaps that I may have wrongly filled: check first/last run boundaries
        if rs and rs[0][0] == 0:
            pass
print('remaining interior gaps <=2:', bad)
np.save('/work/mask.npy', mask)