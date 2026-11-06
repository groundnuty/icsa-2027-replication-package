import os, numpy as np, json
W = '/work/work'
data = np.load(f'{W}/baseline_data.npy')  # (4028, 60, 60) float32
import datetime as dt
dates = [dt.date.fromisoformat(x) for x in np.load(f'{W}/baseline_dates.npy')]

def doy_map(d):
    yd = d.timetuple().tm_yday
    import calendar
    if calendar.isleap(d.year):
        return yd
    return yd if yd <= 59 else yd + 1

# group baseline dates by mapped doy -> indices into data
groups = {}
for i, d in enumerate(dates):
    groups.setdefault(doy_map(d), []).append(i)

# verify: 366 groups, correct member counts
print('groups:', len(groups), '| members of slot 60:', len(groups[60]),
      '| typical:', len(groups[1]), len(groups[153]), len(groups[366]))
print('slot 60 anchors:', [dates[i].isoformat() for i in groups[60]])

# check per-cell finite coverage over baseline+ext (sea cell definition is target-period-only,
# but let's see the data shape)
fin = np.isfinite(data)
percell = fin.mean(axis=0)
print('baseline finite fraction per cell: min', percell.min(), 'max', percell.max())
# cells that are NaN everywhere in baseline
print('cells all-NaN in baseline:', (percell == 0).sum())
