import numpy as np, datetime as dt, json, warnings
warnings.filterwarnings('ignore')

cache = '/tmp/mhw_cache'
cube = np.load(f'{cache}/cube.npy')
with open(f'{cache}/dates.json') as f:
    dates = [dt.date.fromisoformat(s) for s in json.load(f)]
tgt = cube[4028:].astype('float64')
dates_t = dates[4028:]
thresh_s = np.load(f'{cache}/thresh_s.npy')
mhw = np.load(f'{cache}/mhw.npy')
sea = np.load(f'{cache}/sea.npy')

def doy(dd):
    leap = dd.year % 4 == 0 and (dd.year % 100 != 0 or dd.year % 400 == 0)
    tt = dd.timetuple().tm_yday
    return tt + 1 if (not leap and dd.month > 2) else tt

tdoys = np.array([doy(d) for d in dates_t])
th = thresh_s[tdoys].reshape(92, 60, 60)
hot = np.greater_equal(tgt, th, where=np.isfinite(tgt), out=np.zeros(tgt.shape, dtype=bool))

def runs_of_true(v):
    out=[]; n=len(v); i=0
    while i < n:
        if v[i]:
            j=i
            while j+1 < n and v[j+1]: j+=1
            out.append((i,j)); i=j+1
        else: i+=1
    return out

# logical validation of the mask, cell by cell
ok = True
seg_tot = 0
for r in range(60):
    for c in range(60):
        if not sea[r, c]:
            if mhw[:, r, c].any():
                ok = False; print('land cell flagged', r, c)
            continue
        h = hot[:, r, c]; m = mhw[:, r, c].astype(bool)
        if m.any() != h.any():
            pass  # may differ legitimately only if no run>=5
        segs = runs_of_true(m)
        seg_tot += len(segs)
        # 1) every segment starts and ends with a hot day
        for (s, e) in segs:
            if not (h[s] and h[e]):
                ok = False; print('seg edge not hot', r, c, s, e)
            # 2) gaps inside segment <= 2
            for g0, g1 in runs_of_true(~h[s:e+1]):
                if g1 - g0 + 1 > 2:
                    ok = False; print('gap >2 inside seg', r, c, s+g0, s+g1)
        # 3) every hot run >=5 is inside exactly one segment
        for (s, e) in runs_of_true(h):
            if e - s + 1 >= 5:
                inside = [k for k, (a, b) in enumerate(segs) if a <= s and e <= b]
                if len(inside) != 1:
                    ok = False; print('run>=5 not in exactly 1 seg', r, c, s, e, inside)
        # 4) consecutive segments separated by >= 3 non-mhw days
        for k in range(len(segs) - 1):
            gap = segs[k+1][0] - segs[k][1] - 1
            if gap < 3:
                ok = False; print('segments too close', r, c, gap)
        # 5) no hot runs <5 outside segments that should have been absorbed:
        #    a short hot run adjacent (gap<=2) to a segment must be inside it (covered by 3+4)
        # 6) mask matches re-derivation from scratch
        rs5 = [(s,e) for (s,e) in runs_of_true(h) if e-s+1 >= 5]
        mm = np.zeros(92, dtype='uint8')
        if rs5:
            merged = [list(rs5[0])]
            for (s,e) in rs5[1:]:
                if s - merged[-1][1] - 1 <= 2: merged[-1][1] = e
                else: merged.append([s,e])
            for (s,e) in merged: mm[s:e+1] = 1
        if not np.array_equal(mm, mhw[:, r, c]):
            ok = False; print('mask mismatch', r, c)
print('mask structure valid:', ok)
print('total per-cell segments:', seg_tot)

# regional active day runs
active = mhw.reshape(92, -1).any(axis=1)
evs = runs_of_true(active)
print('regional events (independent recompute):',
      [(dates_t[s].isoformat(), dates_t[e].isoformat()) for s, e in evs])
gaps_between = [evs[k+1][0] - evs[k][1] - 1 for k in range(len(evs)-1)]
print('gaps between events (all >=1?):', gaps_between)
print('VALIDATION COMPLETE')