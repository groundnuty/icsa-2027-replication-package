import numpy as np, pandas as pd

d = np.load("work/coords.npz"); t_tgt = pd.to_datetime(d['t_tgt'])
c = np.load("work/clim.npz")
thr, clm, sea, tgt = c['thr'], c['clm'], c['sea'], c['tgt']  # thr/clm (60,60,366), tgt (92,60,60)
nt = tgt.shape[0]

def doy_convention(ts):
    doy = ts.day_of_year.values.copy()
    leap = ts.is_leap_year.values
    after_feb = (ts.month.values > 2)
    return np.where(leap | ~after_feb, doy, doy + 1)
doy = doy_convention(t_tgt)
print("target doys:", doy.min(), "-", doy.max(), "count", nt)

thr_t = thr[:, :, doy-1].transpose(2,0,1)   # (92,60,60)
hot = (tgt >= thr_t) & sea[None,:,:]        # hot day per cell (land forced False)

def find_runs(mask):
    """runs of consecutive True: list of (start,end_incl) along axis 0 for 2D mask per cell"""
    # per-cell runs
    m = mask  # (T,60,60)
    out = []
    T = m.shape[0]
    starts = np.zeros(m.shape[1:], dtype=bool); ends = np.zeros(m.shape[1:], dtype=bool)
    starts[0] = m[0]
    starts[1:] = m[1:] & ~m[:-1]
    ends[:-1] = m[:-1] & ~m[1:]
    ends[-1] = m[-1]
    return starts, ends

# vectorized run handling: iterate cells via flat arrays with run-length encoding
hotf = hot.reshape(nt, -1)                    # (92,3600)
# run-length per column
mhw = np.zeros_like(hotf, dtype=bool)
for j in range(hotf.shape[1]):
    col = hotf[:, j]
    if not col.any():
        continue
    # find runs
    diff = np.diff(col.astype(np.int8))
    run_starts = np.where((diff == 1) | ((diff != 0) & (col[1:] & ~col[:-1]) & (np.arange(1,nt)==0)))[0]
    starts = list(np.where((~col[:-1]) & col[1:])[0] + 1)
    if col[0]: starts = [0] + starts
    ends = list(np.where(col[:-1] & (~col[1:]))[0])
    if col[-1]: ends = ends + [nt-1]
    assert len(starts) == len(ends)
    # merge: runs >=5 hot; gaps of 1-2 non-hot days join runs that are each >=5
    runs = [[s, e] for s, e in zip(starts, ends)]
    # first filter: hot runs with length >= 5
    hot_runs = [[s, e] for s, e in runs if e - s + 1 >= 5]
    # join with gaps of 1 or 2 non-hot days
    merged = []
    for r in hot_runs:
        if merged and (r[0] - merged[-1][1] - 1) in (1, 2):
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    for s, e in merged:
        mhw[s:e+1, j] = True

mhw = mhw.reshape(nt, 60, 60)
active = mhw.any(axis=(1,2))
print("hot cell-days:", int(hot.sum()), "; mhw cell-days:", int(mhw.sum()))
# regional events
ev = []
i = 0
while i < nt:
    if active[i]:
        j = i
        while j + 1 < nt and active[j+1]:
            j += 1
        ev.append((i, j)); i = j + 1
    else:
        i += 1
print("active days:", int(active.sum()), "of", nt)
for s, e in ev:
    print("event:", str(t_tgt[s].date()), "to", str(t_tgt[e].date()), f"({e-s+1} days)")
np.savez_compressed("work/mhw.npz", mhw=mhw, hot=hot, active=active)
