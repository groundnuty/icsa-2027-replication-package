import numpy as np, datetime as dt, pickle
dates = np.load('/tmp/dates.npy')
data = np.load('/tmp/sst_needed.npy')
n_base = 4028
target = data[n_base:]            # (92, 60, 60)
tdates = dates[n_base:]
clim_s = np.load('/tmp/clim_smooth.npy')
thr_s = np.load('/tmp/thr_smooth.npy')

# verify all target dates within 2009-06-01..2009-08-31
td_list = [str(d) for d in tdates]
assert td_list[0]=='2009-06-01' and td_list[-1]=='2009-08-31' and len(td_list)==92

# sea cells: finite on every target day
sea = np.isfinite(target).all(axis=0)
print('sea cells:', sea.sum())

# DOY of target dates (2009 not leap)
md_doy = {}
cum = [0,31,59,90,120,151,181,212,243,273,304,334]
for m in range(1,13):
    for day in range(1,32):
        if not (m==2 and day>29) and not (m in (4,6,9,11) and day>30):
            md_doy[(m,day)] = cum[m-1] + day
tdoy = np.array([md_doy[(int(str(d)[5:7]), int(str(d)[8:10]))] for d in tdates])

sst64 = target.astype('float64')
# threshold & climatology per day for each cell
thr_t = thr_s[tdoy-1]           # (92,60,60)
hot = sst64 >= thr_t
hot &= sea[None,:,:]
print('hot days frac (all cells):', hot.mean().round(4))

# runs >= 5 then join gaps of 1-2 non-hot days, per cell
def find_events_1d(h, min_run=5, max_gap=2):
    n = len(h)
    inside = np.zeros(n, dtype=bool)
    runs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j < n and h[j]: j += 1
            if j - i >= min_run:
                runs.append((i, j-1))
            i = j
        else:
            i += 1
    # join runs separated by gaps of 1..2 non-hot days
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] - 1 <= max_gap and r[0] > merged[-1][1]:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(list(r))
    for s,e in merged:
        inside[s:e+1] = True
    return inside, merged

nx, ny = 60, 60
mhw = np.zeros(target.shape, dtype=bool)
per_cell_events = {}
for i in range(nx):
    for j in range(ny):
        if not sea[i,j]: continue
        h = hot[:,i,j]
        if not h.any(): continue
        ins, merged = find_events_1d(h)
        mhw[:,i,j] = ins
        per_cell_events[(i,j)] = merged
n_cells_with = sum(1 for v in per_cell_events.values() if v)
print('cells with >=1 per-cell MHW:', n_cells_with)
active = mhw.any(axis=(1,2))
print('active days:', active.sum(), 'of', len(active))
# regional events
ev = []
i = 0
while i < len(active):
    if active[i]:
        j = i
        while j < len(active) and active[j]: j += 1
        ev.append((i, j-1))
        i = j
    else:
        i += 1
print('regional events:')
for s,e in ev:
    print('  ', td_list[s], '->', td_list[e], f'({e-s+1} days)')
np.save('/tmp/mhw_mask.npy', mhw)
with open('/tmp/percell.pkl','wb') as f: pickle.dump((per_cell_events, td_list, ev, sea), f)
