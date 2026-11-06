import numpy as np, json
from datetime import date, timedelta

T = np.load('/work/T.npy')
thr_s = np.load('/work/thr_s.npy')
meta = json.load(open('/work/meta.json'))
t0 = date.fromisoformat(meta['t0']); t1 = date.fromisoformat(meta['t1'])
nt = (t1-t0).days+1
tdates = [t0+timedelta(days=i) for i in range(nt)]
CUM366 = [0,31,60,91,121,152,182,213,244,274,305,335]
tdoy = np.array([CUM366[d.month-1]+d.day for d in tdates])

# baseline completeness: any fully-NaN days in the window?
B = np.load('/work/B.npy')
fin = np.isfinite(B).mean(axis=(1,2))
print("baseline days with zero finite cells:", int((fin==0).sum()))
print("baseline min/mean finite frac:", fin.min(), fin.mean())
# target: fully-NaN days?
finT = np.isfinite(T).mean(axis=(1,2))
print("target days with zero finite cells:", int((finT==0).sum()), "min frac:", finT.min())

# hot days
thr_days = thr_s[tdoy-1]          # (92,60,60)
hot = T >= thr_days               # land: NaN>=x -> False
print("hot days total:", int(hot.sum()), "hot frac on sea:", hot[:, np.isfinite(T).all(axis=0)].mean())

def per_cell_mhw(hot, minlen=5, maxgap=2, strict_gap_days=True):
    nt, nlat, nlon = hot.shape
    mask = np.zeros_like(hot, dtype=bool)
    runs_by_cell = []
    for r in range(nlat):
        for c in range(nlon):
            h = hot[:, r, c]
            # find maximal runs of True
            idx = np.flatnonzero(h)
            if idx.size == 0:
                runs_by_cell.append([]); continue
            breaks = np.flatnonzero(np.diff(idx) > 1)
            starts = np.concatenate(([idx[0]], idx[breaks+1]))
            ends = np.concatenate((idx[breaks], [idx[-1]]))
            runs = [(int(s), int(e)) for s, e in zip(starts, ends)]
            runs_by_cell.append(runs)
            qual = [(s, e) for (s, e) in runs if e - s + 1 >= minlen]
            merged = []
            for (s, e) in qual:
                if merged and (maxgap is not None) and (s - merged[-1][1] - 1 <= maxgap) and (s - merged[-1][1] - 1 >= 1):
                    # strict: intervening days must be non-hot (they may include discarded hot runs)
                    if strict_gap_days:
                        inter = range(merged[-1][1]+1, s)
                        if any(h[i] for i in inter):
                            merged.append((s, e)); continue
                    merged[-1] = (merged[-1][0], e)
                else:
                    merged.append((s, e))
            for (s, e) in merged:
                mask[s:e+1, r, c] = True
    return mask, runs_by_cell

mask_strict, _ = per_cell_mhw(hot, strict_gap_days=True)
mask_loose, _  = per_cell_mhw(hot, strict_gap_days=False)
print("strict vs loose identical:", np.array_equal(mask_strict, mask_loose))
print("mhw cell-days:", int(mask_strict.sum()))
np.save('/work/mhw_mask.npy', mask_strict)
