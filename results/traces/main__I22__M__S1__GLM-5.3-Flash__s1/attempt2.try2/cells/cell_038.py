import numpy as np, datetime as dt
W = '/work/work'
hot = np.load(f'{W}/hot.npy')
sea = np.load(f'{W}/sea.npy')
tgt = np.load(f'{W}/target_data.npy').astype(np.float64)
thr = np.load(f'{W}/thr.npy')
tdates = [dt.date.fromisoformat(str(x)) for x in np.load(f'{W}/target_dates.npy')]

def doy_map(d):
    yd = d.timetuple().tm_yday
    if dt.date(d.year, 12, 31).timetuple().tm_yday == 366: return yd
    return yd if yd <= 59 else yd + 1
slots = np.array([doy_map(d) for d in tdates])

def runs_of_true(m):
    out = []; n = len(m); i = 0
    while i < n:
        if m[i]:
            j = i
            while j + 1 < n and m[j+1]: j += 1
            out.append((i, j)); i = j + 1
        else: i += 1
    return out

# days 0..91 -> runs of (at least one cell hot)
anyhot = hot.any(axis=(1, 2))
print('runs of any-hot (per day any cell hot):')
for (a, b) in runs_of_true(anyhot):
    print(f'  {tdates[a]} -> {tdates[b]} ({b-a+1} days), max simultaneous cells:',
          hot[a:b+1].sum(axis=(1, 2)).max())

# closest approaches: per day count cells with margin < 0.1 K
margin = tgt - thr[slots - 1]
for i in range(92):
    m = margin[i][sea]
    n_close = (m >= -0.1).sum()
    if n_close:
        print(tdates[i], f'cells within 0.1K below thr: {n_close}, max margin {m.max():.3f}')
