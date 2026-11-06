
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

# Load cached data
cached = np.load('cache/target_data.npz')
target_dates = [datetime.date.fromordinal(int(d)) for d in np.load('cache/target_dates.npy')]
target_sst = {}
for d in target_dates:
    target_sst[d] = cached[d.strftime('%Y%m%d')]

threshold_sm = np.load('cache/threshold_smoothed.npy')
clim_sm = np.load('cache/clim_smoothed.npy')

n_target = len(target_dates)
n_lat, n_lon = 60, 60

target_array = np.array([target_sst[d] for d in target_dates], dtype=np.float64)
sea_cells = np.all(np.isfinite(target_array), axis=0)
target_doy = np.array([day_of_year(d) for d in target_dates])

# Build hot mask
hot = np.zeros((n_lat, n_lon, n_target), dtype=bool)
for t in range(n_target):
    doy = target_doy[t]
    for i in range(n_lat):
        for j in range(n_lon):
            if sea_cells[i, j] and not np.isnan(threshold_sm[doy-1, i, j]):
                hot[i, j, t] = target_array[t, i, j] >= threshold_sm[doy-1, i, j]

# Check per-cell run lengths
# Find maximum consecutive hot run per cell
for i in range(n_lat):
    for j in range(n_lon):
        if sea_cells[i,j]:
            h = hot[i,j]
            # Find runs
            max_run = 0
            cur = 0
            for t in range(n_target):
                if h[t]:
                    cur += 1
                    max_run = max(max_run, cur)
                else:
                    cur = 0
            if max_run >= 3:
                print(f'Cell ({i},{j}): max run = {max_run}, hot days at: ', end='')
                for t in range(n_target):
                    if h[t]:
                        print(f'{target_dates[t]}, ', end='')
                print()
