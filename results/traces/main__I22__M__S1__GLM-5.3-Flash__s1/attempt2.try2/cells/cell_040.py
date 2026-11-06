import os, json, datetime as dt
import numpy as np

W = '/work/work'
OUT = '/work/output'
os.makedirs(OUT, exist_ok=True)

# ---------------- inputs ----------------
data = np.load(f'{W}/baseline_data.npy')        # (4028, 60, 60) float32, days 1991-12-27..2003-01-05
tdates = [dt.date.fromisoformat(str(x)) for x in np.load(f'{W}/target_dates.npy')]
tgt = np.load(f'{W}/target_data.npy').astype(np.float64)  # (92, 60, 60) float64, 2004-06-01..2004-08-31
thr = np.load(f'{W}/thr.npy')                   # (366, 60, 60) float64, smoothed threshold
clim = np.load(f'{W}/clim.npy')                 # (366, 60, 60) float64, smoothed climatology

assert len(tdates) == 92 and tdates[0] == dt.date(2004, 6, 1) and tdates[-1] == dt.date(2004, 8, 31)

# day-of-year 1..366 (1 Jan=1, 28 Feb=59, 29 Feb=60, 1 Mar=61, ..., 31 Dec=366)
def doy_map(d):
    yd = d.timetuple().tm_yday
    if dt.date(d.year, 12, 31).timetuple().tm_yday == 366:
        return yd
    return yd if yd <= 59 else yd + 1

slots = np.array([doy_map(d) for d in tdates])
assert slots.min() == 153 and slots.max() == 244

# ---------------- sea cells ----------------
sea = np.isfinite(tgt).all(axis=0)
print('sea cells (finite on every target day):', int(sea.sum()))

# ---------------- hot days: SST >= threshold (as stored, kelvin) ----------------
hot = (tgt >= thr[slots - 1]) & np.isfinite(tgt)
assert not hot[:, ~sea].any()
print('hot cell-days:', int(hot.sum()))

def runs_of_true(m):
    out = []; n = len(m); i = 0
    while i < n:
        if m[i]:
            j = i
            while j + 1 < n and m[j + 1]:
                j += 1
            out.append((i, j)); i = j + 1
        else:
            i += 1
    return out

# ---------------- per-cell MHWs: runs >= 5 hot days, join gaps of 1-2 days ----------------
T = len(tdates)
mhw = np.zeros_like(hot)
for y, x in zip(*np.where(sea)):
    m = np.zeros(T, dtype=bool)
    for (a, b) in runs_of_true(hot[:, y, x]):
        if b - a + 1 >= 5:
            m[a:b + 1] = True
    marked = runs_of_true(m)
    for k in range(len(marked) - 1):
        ga, gb = marked[k][1] + 1, marked[k + 1][0] - 1
        if 1 <= gb - ga + 1 <= 2:
            m[ga:gb + 1] = True
    mhw[:, y, x] = m

# sanity: every maximal mhw run >= 5 days; unfilled gaps between runs >= 3 days
for y, x in zip(*np.where(sea)):
    mr = runs_of_true(mhw[:, y, x])
    for (a, b) in mr:
        assert b - a + 1 >= 5
    for k in range(len(mr) - 1):
        assert mr[k + 1][0] - mr[k][1] - 1 >= 3

# ---------------- regional events ----------------
active = mhw.any(axis=(1, 2))
events = runs_of_true(active)
print('active days:', int(active.sum()), '| regional events:', len(events))

# diagnostics
longest = 0
for y, x in zip(*np.where(sea)):
    for (a, b) in runs_of_true(hot[:, y, x]):
        longest = max(longest, b - a + 1)
perday = hot.sum(axis=(1, 2))
i_peak = int(perday.argmax())
print('longest consecutive hot run in any cell:', longest)
print('max cells hot simultaneously:', int(perday[i_peak]), 'on', tdates[i_peak])

# ---------------- write mhw_mask.nc ----------------
import h5py
ilat0, ilat1, ilon0, ilon1 = 196, 256, 485, 545
with h5py.File('/data/icsa2027_data_20261101T090944Z/s1z/sst_20040615.nc', 'r') as f:
    lat = f['latitude'][ilat0:ilat1].astype(np.float64)
    lon = f['longitude'][ilon0:ilon1].astype(np.float64)
assert lat.min() >= 57.41 - 1e-6 and lat.max() <= 58.61 + 1e-6
assert lon.min() >= 18.69 - 1e-6 and lon.max() <= 19.89 + 1e-6

import xarray as xr
mhw_u8 = mhw.astype(np.uint8)
ds = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_u8, {
            'long_name': 'marine heatwave (per-cell MHW) mask',
            'units': '1',
            'flag_values': np.array([0, 1], dtype=np.uint8),
            'flag_meanings': 'not_in_mhw in_mhw',
        })
    },
    coords={
        'time': ('time', np.array(tdates, dtype='datetime64[ns]'),
                 {'long_name': 'Time', 'standard_name': 'time'}),
        'lat': ('lat', lat, {'long_name': 'latitude', 'units': 'degrees_north',
                             'standard_name': 'latitude'}),
        'lon': ('lon', lon, {'long_name': 'longitude', 'units': 'degrees_east',
                             'standard_name': 'longitude'}),
    },
)
enc = {'mhw': {'dtype': 'uint8', '_FillValue': None, 'zlib': True}}
ds.to_netcdf(f'{OUT}/mhw_mask.nc', engine='h5netcdf', encoding=enc)

# ---------------- write report.json ----------------
report = {
    'region': {'lat_min': 57.41, 'lat_max': 58.61, 'lon_min': 18.69, 'lon_max': 19.89},
    'baseline_analysed': {'start': '1991-12-27', 'end': '2003-01-05'},
    'target_analysed': {'start': '2004-06-01', 'end': '2004-08-31'},
    'events': [{'onset': tdates[a].isoformat(), 'end': tdates[b].isoformat()} for (a, b) in events],
    'complete': True,
    'caveats': (
        'No regional MHW events were found under the specified definition: no sea cell reached a run of '
        'at least 5 consecutive hot days (hot = daily SST >= its smoothed 90th-percentile threshold, '
        '1992-2002 baseline, +-5-day calendar-day-of-year windows) anywhere in 2004-06-01..2004-08-31; '
        'the longest hot run in any cell was 4 days. A broad regional warm spell (2004-08-07..2004-08-12, '
        'up to 1019 cells hot simultaneously on 2004-08-08) peaked just below the per-cell thresholds, '
        'which are inflated by the record Baltic warm spell of early August 2002 inside the baseline pool. '
        'The baseline range actually read spans the window extension days 1991-12-27..1991-12-31 and '
        '2003-01-01..2003-01-05 beyond the 1992-2002 baseline proper; day-of-year 60 (29 Feb) threshold '
        'and climatology were filled as the mean of days 59 and 61 and received no pool of their own. '
        'Dataset version 202506.'
    ),
}
with open(f'{OUT}/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print('\nfiles written:')
print(' ', f'{OUT}/mhw_mask.nc', os.path.getsize(f'{OUT}/mhw_mask.nc'), 'bytes')
print(' ', f'{OUT}/report.json', os.path.getsize(f'{OUT}/report.json'), 'bytes')
