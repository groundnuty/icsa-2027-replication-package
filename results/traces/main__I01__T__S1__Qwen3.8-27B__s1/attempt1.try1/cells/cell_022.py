import json, time
import numpy as np
from datetime import date, timedelta

sst = np.load('/tmp/sst_region.npy')
meta = json.load(open('/tmp/meta.json'))
dates = [date.fromisoformat(d) for d in meta['dates']]
date_to_idx = {d: i for i, d in enumerate(dates)}
z = np.load('/tmp/mhw_intermediate.npz')
thr_raw, thr_sm, in_mhw = z['thr_raw'], z['thr_sm'], z['in_mhw']
sea_idx = z['sea_idx']
n_sea = len(sea_idx)
NC = sst.shape[1]

def doy(d):
    cum = {1:0, 2:31, 3:60, 4:91, 5:121, 6:152, 7:182, 8:213, 9:244, 10:274, 11:305, 12:335}
    return cum[d.month] + d.day

# ---- independent hazen quantile (hand formula) ----
def hazen_q(v, p):
    v = np.sort(v)
    n = len(v)
    h = n * p + 0.5          # 1-based position
    lo = int(np.floor(h))
    if lo < 1: return v[0]
    if lo >= n: return v[-1]
    frac = h - lo
    if frac == 0: return v[lo-1]
    return v[lo-1] + frac * (v[lo] - v[lo-1])

# ---- pick a cell and day 153 (2008-06-01) ----
c = 37   # some sea cell
d = 153
base_dates = [date(1992,1,1) + timedelta(days=k) for k in range(4018)]
poolset = set()
for B in base_dates:
    if doy(B) == d:
        for k in range(-5, 6):
            poolset.add(B + timedelta(days=k))
vals = []
for X in sorted(poolset):
    vi = sst[date_to_idx[X], sea_idx[c]]
    if np.isfinite(vi):
        vals.append(vi)
q_hazen = hazen_q(np.array(vals), 0.90)
q_np = np.nanquantile(np.array(vals), 0.90, method='hazen')
print(f"cell {c} day {d}: pool n={len(vals)}  hand={q_hazen!r}  numpy={q_np!r}  pipeline={thr_raw[c, d-1]!r}")
assert q_hazen == q_np == thr_raw[c, d-1]

# ---- verify smoothing for day 1 (wrap) and a mid day ----
for day in (1, 153, 366):
    di = day - 1
    window = np.array([thr_raw[c, (day - 1 + k - 15) % 366] for k in range(31)])
    expect = window.mean()
    print(f"cell {c} day {day}: manual={expect!r} pipeline={thr_sm[c, di]!r}")
    assert expect == thr_sm[c, di]

# ---- check a cell that was inside an MHW: show hot pattern & runs ----
cnt = in_mhw.sum(axis=1)
c2 = int(np.argmax(cnt))
b = (sst[[date_to_idx[date(2008,6,1)+timedelta(days=k)] for k in range(92)]][:, sea_idx[c2]]
     >= thr_sm[c2, np.array([doy(date(2008,6,1)+timedelta(days=k)) for k in range(92)])-1]).T
hot = b[0]
m = in_mhw[c2]
ext = np.concatenate(([0], hot.view(np.int8), [0]))
dff = np.diff(ext)
starts = np.where(dff==1)[0]; ends = np.where(dff==-1)[0]
print(f"cell {c2}: hot runs (start,len):", [(int(s), int(e-s)) for s, e in zip(starts, ends)])
print(f"cell {c2}: mhw mask days: {np.where(m)[0].min()}..{np.where(m)[0].max()}, n={int(m.sum())}")
# verify every mhw day belongs to a hot run or a gap<=2 between kept runs
kept = [(s, e) for s, e in zip(starts, ends) if e - s >= 5]
merged = []
for s, e in kept:
    if merged and s - merged[-1][1] <= 2:
        merged[-1][1] = e
    else:
        merged.append([s, int(e)])
mask = np.zeros(92, bool)
for s, e in merged:
    mask[s:e] = True
assert (mask == m).all()
print("cell2 runs/merge verified; merged spans:", merged)

# ---- verify event logic against mask ----
active = in_mhw.any(axis=0)
runs = []
inev = False
for t in range(92):
    if active[t] and not inev:
        st = t; inev = True
    elif not active[t] and inev:
        runs.append((st, t-1)); inev = False
if inev: runs.append((st, 91))
print("event spans (day idx):", runs)
# no other days active
print("days 22-91 all inactive:", not active[21:].any())
