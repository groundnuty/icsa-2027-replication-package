
import numpy as np
import pickle
from datetime import date, timedelta

def day_of_year(month, day):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:month-1]) + day
    return doy

tgt_data = np.load('/work/tgt_data.npy')
tgt_time = np.load('/work/tgt_time.npy')
threshold_sm = np.load('/work/threshold_sm.npy')
climatology_sm = np.load('/work/climatology_sm.npy')

target_dates = [date(1970,1,1) + timedelta(days=int(t)) for t in tgt_time]
target_doy = np.array([day_of_year(d.month, d.day) for d in target_dates])

tgt_nan = np.isnan(tgt_data)
cell_tgt_nan = tgt_nan.any(axis=0)
sea_cells = ~cell_tgt_nan

# Recompute hot mask
n_t = len(target_dates)
hot = np.zeros((n_t, 60, 60), dtype=bool)
for t in range(n_t):
    d = target_doy[t] - 1
    hot[t] = (tgt_data[t] >= threshold_sm[d]) & sea_cells

# Find per-cell MHWs
def find_mhws(hot_mask):
    T = len(hot_mask)
    runs = []
    i = 0
    while i < T:
        if hot_mask[i]:
            start = i
            while i < T and hot_mask[i]:
                i += 1
            runs.append((start, i-1))
        else:
            i += 1
    qualified = [r for r in runs if r[1]-r[0]+1 >= 5]
    if not qualified:
        return []
    merged = [qualified[0]]
    for run in qualified[1:]:
        prev = merged[-1]
        gap = run[0] - prev[1] - 1
        if 1 <= gap <= 2:
            merged[-1] = (prev[0], run[1])
        else:
            merged.append(run)
    return merged

mhw_mask = np.zeros((n_t, 60, 60), dtype=np.uint8)
for i in range(60):
    for j in range(60):
        if sea_cells[i,j]:
            mhws = find_mhws(hot[:, i, j])
            for (s, e) in mhws:
                mhw_mask[s:e+1, i, j] = 1

active = mhw_mask.any(axis=(1,2))
print("Active days:", np.where(active)[0] + 1)
print("Active pattern (1=active):", ''.join('1' if a else '0' for a in active))
