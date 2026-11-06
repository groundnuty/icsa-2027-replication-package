import os, time, numpy as np, json, datetime as dt
W = '/work/work'
data = np.load(f'{W}/baseline_data.npy')  # (4028, 60, 60) float32
dates = [dt.date.fromisoformat(x) for x in np.load(f'{W}/baseline_dates.npy')]

def doy_map(d):
    yd = d.timetuple().tm_yday
    if dt.date(d.year, 12, 31).timetuple().tm_yday == 366:
        return yd
    return yd if yd <= 59 else yd + 1

groups = {}
for i, d in enumerate(dates):
    groups.setdefault(doy_map(d), []).append(i)

# per date, which slots include it (for pool scatter) - quick sanity only
# Build pools per slot and compute quantile+mean
import warnings
warnings.filterwarnings('ignore')

thr_raw = np.empty((366, 60, 60), dtype=np.float64)
clim_raw = np.empty((366, 60, 60), dtype=np.float64)

t_start = time.time()
for s in range(1, 367):
    idxs = []
    for i in groups.get(s, []):
        for off in range(-5, 6):
            j = i + off
            if 0 <= j < 4028:
                idxs.append(j)
    idxs = np.array(sorted(set(idxs)))
    assert idxs.size > 0, s
    pool = data[idxs].astype(np.float64)          # copies up to 121*60*60*8 = 3.5MB
    thr_raw[s-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
    with np.errstate(all='ignore'):
        clim_raw[s-1] = np.nanmean(pool, axis=0)
    if s % 100 == 0:
        print(f'slot {s}/366  ({time.time()-t_start:.0f} s)', flush=True)
print('pools done:', f'{time.time()-t_start:.1f} s')
np.save(f'{W}/thr_raw.npy', thr_raw)
np.save(f'{W}/clim_raw.npy', clim_raw)

# day 60 <- mean of day 59 and 61
thr_raw[59] = 0.5*(thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])
print('day60 fill done; any NaN in thr_raw/clim_raw:',
      np.isnan(thr_raw).any(), np.isnan(clim_raw).any())
np.save(f'{W}/thr_raw.npy', thr_raw)
np.save(f'{W}/clim_raw.npy', clim_raw)
