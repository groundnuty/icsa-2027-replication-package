
import numpy as np
import datetime

def day_of_year(date):
    y, m, d = date.year, date.month, date.day
    months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    doy = sum(months[:m-1]) + d
    if m > 2 and is_leap:
        doy += 1
    if not is_leap and m > 2:
        doy += 1
    return doy

cached = np.load('cache/target_data.npz')
target_dates = [datetime.date.fromordinal(int(d)) for d in np.load('cache/target_dates.npy')]
target_sst = {}
for d in target_dates:
    target_sst[d] = cached[d.strftime('%Y%m%d')]

threshold_sm = np.load('cache/threshold_smoothed.npy')

n_target = len(target_dates)
target_array = np.array([target_sst[d] for d in target_dates], dtype=np.float64)
target_doy = np.array([day_of_year(d) for d in target_dates])

# Check cell (53,40) which had 4 hot days (Aug 8-11)
i, j = 53, 40
print(f'Cell ({i},{j}) - day of year and values:')
for t in range(n_target):
    doy = target_doy[t]
    sst_val = target_array[t, i, j]
    thr = threshold_sm[doy-1, i, j]
    is_hot = sst_val >= thr
    if not np.isnan(sst_val):
        print(f'  {target_dates[t]} (doy={doy}): SST={sst_val:.4f}, threshold={thr:.4f}, hot={is_hot}')

print()
# Also check cell (22,28)
i, j = 22, 28
print(f'Cell ({i},{j}):')
for t in range(n_target):
    doy = target_doy[t]
    sst_val = target_array[t, i, j]
    thr = threshold_sm[doy-1, i, j]
    is_hot = sst_val >= thr
    if not np.isnan(sst_val):
        print(f'  {target_dates[t]} (doy={doy}): SST={sst_val:.4f}, threshold={thr:.4f}, hot={is_hot}')
