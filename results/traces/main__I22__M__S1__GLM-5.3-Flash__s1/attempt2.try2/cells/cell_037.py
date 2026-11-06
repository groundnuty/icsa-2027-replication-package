import numpy as np, datetime as dt, os, h5py
W = '/work/work'
thr = np.load(f'{W}/thr.npy')
sea = np.load(f'{W}/sea.npy')
tgt = np.load(f'{W}/target_data.npy').astype(np.float64)
hot = np.load(f'{W}/hot.npy')
tdates = [dt.date.fromisoformat(str(x)) for x in np.load(f'{W}/target_dates.npy')]

def runs_of_true(m):
    out = []; n = len(m); i = 0
    while i < n:
        if m[i]:
            j = i
            while j + 1 < n and m[j+1]: j += 1
            out.append((i, j)); i = j + 1
        else: i += 1
    return out

# per-cell: longest hot run, total hot days
best_len = np.zeros((60, 60), int)
for y in range(60):
    for x in range(60):
        if not sea[y, x]: continue
        for (a, b) in runs_of_true(hot[:, y, x]):
            best_len[y, x] = max(best_len[y, x], b - a + 1)
print('longest hot run per cell: max', best_len.max(), '| cells with run>=5:', (best_len >= 5).sum())
print('distribution of longest runs:', {k: int((best_len[sea] == k).sum()) for k in range(0, 6)})

# brute-force independent threshold for cell (0,12), slot 214 (Aug 2) and slot 152 (Jun 1)
ILAT0, ILAT1, ILON0, ILON1 = 196, 256, 485, 545
d_root = '/data/icsa2027_data_20261101T090944Z/s1z'
def read_cell(date):
    with h5py.File(f'{d_root}/sst_{date.strftime("%Y%m%d")}.nc', 'r') as f:
        return float(f['analysed_sst'][0, ILAT0 + 0, ILON0 + 12])
def doy_map(d):
    yd = d.timetuple().tm_yday
    if dt.date(d.year, 12, 31).timetuple().tm_yday == 366: return yd
    return yd if yd <= 59 else yd + 1
for slot_target in [214, 152, 244]:
    vals = []
    # anchors: baseline dates with doy_map == slot_target
    y = 1992
    # enumerate all baseline dates 1992-01-01..2002-12-31 (skip reading; use date arithmetic)
    dd = dt.date(1992, 1, 1)
    anchors = []
    while dd <= dt.date(2002, 12, 31):
        if doy_map(dd) == slot_target:
            anchors.append(dd)
        dd += dt.timedelta(days=1)
    for a in anchors:
        for off in range(-5, 6):
            vals.append(read_cell(a + dt.timedelta(days=off)))
    vals = np.array(vals, dtype=np.float64)
    brute_q = np.nanquantile(vals, 0.9, method='hazen')
    brute_m = np.nanmean(vals)
    print(f'slot {slot_target}: brute q90 {brute_q:.6f} mean {brute_m:.6f} (n={len(vals)}, nan={np.isnan(vals).sum()})',
          f'| pipeline: thr[214] raw-window... smoothed pipeline value at that day: ', end='')
    # pipeline raw value for this slot (before smoothing) - recompute from thr_raw? load
    thr_raw = np.load(f'{W}/thr_raw.npy')
    print(f'{thr_raw[slot_target-1, 0, 12]:.6f}')
