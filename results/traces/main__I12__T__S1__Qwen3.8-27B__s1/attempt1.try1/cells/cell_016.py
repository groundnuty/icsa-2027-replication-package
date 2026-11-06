import numpy as np, datetime as dt, os, json
z = np.load('data/climthr.npz')
thr_smooth = z['thr_smooth']; sea = z['sea']; tgt_doy = z['tgt_doy']
SST_tgt = np.load('data/SST_tgt.npy')
lat = z['lat']; lon = z['lon']
N = SST_tgt.shape[0]

hot = SST_tgt >= thr_smooth[tgt_doy-1]   # (92, 60, 60); NaN comparisons -> False
hot &= sea  # land cells never hot

def runs_of(h):
    # maximal True runs in boolean 1-D -> list of (start, end) inclusive
    out = []
    i = 0
    while i < len(h):
        if h[i]:
            j = i
            while j + 1 < len(h) and h[j+1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out

mhw = np.zeros((N, 60, 60), dtype=np.uint8)
for cell in range(60*60):
    c, l = divmod(cell, 60)
    if not sea[c, l]:
        continue
    h = hot[:, c, l]
    runs = runs_of(h)
    # keep runs >= 5 days
    runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
    # join runs separated by 1 or 2 non-hot days
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    for s, e in merged:
        mhw[s:e+1, c, l] = 1

inside = mhw.astype(bool)
active = inside.any(axis=(1, 2))
print('hot days per target day (sum over cells): first/last/max:',
      hot.sum(axis=(1,2))[0], hot.sum(axis=(1,2))[-1], int(hot.sum(axis=(1,2)).max()))
print('active days count:', active.sum(), 'of', N)

# regional events: maximal runs of active days
events = []
i = 0
while i < N:
    if active[i]:
        j = i
        while j + 1 < N and active[j+1]:
            j += 1
        events.append((i, j))
        i = j + 1
    else:
        i += 1
print('n regional events:', len(events))

def daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)
tgt_dates = list(daterange(dt.date(2009,6,1), dt.date(2009,8,31)))
for k, (s, e) in enumerate(events):
    print(f'event {k+1}: {tgt_dates[s]} .. {tgt_dates[e]}  ({e-s+1} days)')

# per-cell stats for sanity
ncell_mhw = (mhw.sum(axis=0) > 0).sum()
print('cells with >=1 MHW day:', ncell_mhw)
mhwlen = mhw.sum(axis=0)
print('max MHW duration per cell:', int(mhwlen.max()))

np.savez('data/results.npz', mhw=mhw, active=active, hot=hot,
         events=np.array(events, dtype=np.int32) if events else np.zeros((0,2), dtype=np.int32),
         tgt_dates=np.array(tgt_dates, dtype='datetime64[D]'))