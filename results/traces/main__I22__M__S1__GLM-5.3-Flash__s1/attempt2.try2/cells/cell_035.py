import numpy as np, datetime as dt, calendar
W = '/work/work'
tgt = np.load(f'{W}/target_data.npy').astype(np.float64)   # (92, 60, 60)
thr = np.load(f'{W}/thr.npy')
tdate_strs = [str(x) for x in np.load(f'{W}/target_dates.npy')]
tdates = [dt.date.fromisoformat(x) for x in tdate_strs]

def doy_map(d):
    yd = d.timetuple().tm_yday
    if dt.date(d.year, 12, 31).timetuple().tm_yday == 366:
        return yd
    return yd if yd <= 59 else yd + 1

slots = np.array([doy_map(d) for d in tdates])
print('target slots: min', slots.min(), 'max', slots.max(), '(expect 153..244)')

# sea cells: finite on every target day
sea = np.isfinite(tgt).all(axis=0)
print('sea cells:', sea.sum(), 'of', sea.size)

# hot days: SST >= threshold (NaN -> False)
hot = np.greater_equal(tgt, thr[slots - 1], where=~np.isnan(tgt), out=np.zeros(tgt.shape, dtype=bool))
# ensure NaN cells are False
hot &= np.isfinite(tgt)
print('hot days total:', hot.sum(), '| hot only on sea cells:', np.all(~hot[:, ~sea]))

def runs_of_true(mask_1d):
    """yield (start, end) inclusive indices of maximal True runs"""
    out = []
    n = len(mask_1d)
    i = 0
    while i < n:
        if mask_1d[i]:
            j = i
            while j + 1 < n and mask_1d[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out

# vectorised run detection per cell
def find_mhw_mask(hot):
    """hot: (T, Y, X) bool -> mhw mask (T, Y, X) bool with runs>=5 and gaps 1-2 filled"""
    T, Y, X = hot.shape
    out = np.zeros_like(hot)
    # runs >= 5: use cumulative trick per cell
    for y in range(Y):
        for x in range(X):
            if not sea[y, x]:
                continue
            h = hot[:, y, x]
            runs = runs_of_true(h)
            if not runs:
                continue
            # mark runs with length >= 5
            mhw = np.zeros(T, dtype=bool)
            for (a, b) in runs:
                if b - a + 1 >= 5:
                    mhw[a:b+1] = True
            # fill interior gaps of 1-2 days between marked runs
            marked = runs_of_true(mhw)
            for k in range(len(marked) - 1):
                gap_a = marked[k][1] + 1
                gap_b = marked[k+1][0] - 1
                gap = gap_b - gap_a + 1
                if 1 <= gap <= 2:
                    mhw[gap_a:gap_b+1] = True
            out[:, y, x] = mhw
    return out

import time
t0 = time.time()
mhw = find_mhw_mask(hot)
print(f'per-cell MHW detection: {time.time()-t0:.2f} s')
print('mhw cells-days:', mhw.sum())
# after joining, check every maximal mhw run has length >=5
bad = 0
for y, x in zip(*np.where(sea)):
    for (a, b) in runs_of_true(mhw[:, y, x]):
        if b - a + 1 < 5:
            bad += 1
print('final runs shorter than 5 days:', bad)

# regional active days
active = mhw.any(axis=(1, 2))
print('active days:', active.sum(), 'of', len(tdates))
evs = runs_of_true(active)
print('regional events:', len(evs))
for (a, b) in evs:
    print(f'  {tdates[a]} -> {tdates[b]}  ({b-a+1} days)')

# per-cell event count diagnostics
n_ev_cell = np.zeros((60, 60), dtype=int)
for y, x in zip(*np.where(sea)):
    n_ev_cell[y, x] = len(runs_of_true(mhw[:, y, x]))
print('per-cell MHW count: min', n_ev_cell[sea].min(), 'max', n_ev_cell[sea].max(), 'mean', n_ev_cell[sea].mean().round(2))
np.save(f'{W}/mhw.npy', mhw)
np.save(f'{W}/sea.npy', sea)
np.save(f'{W}/hot.npy', hot)
