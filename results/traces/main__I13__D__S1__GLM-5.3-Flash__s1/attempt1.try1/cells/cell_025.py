import numpy as np, datetime as dt
datestrs = np.load('/work/extract_dates.npy')
arr32 = np.load('/work/extract_sst.npy')
dates = [dt.date.fromisoformat(s) for s in datestrs]
n_base_win = sum(1 for d in dates if d <= dt.date(2003,1,5))
tgt_dates = dates[n_base_win:]
mhw_mask = np.load('/work/mhw_mask.npy')
active = mhw_mask.any(axis=(1,2))
cells_per_day = mhw_mask.sum(axis=(1,2))
hot_cells = np.load('/work/hot.npy').sum(axis=(1,2))
for i in [0,1,2,3,4,5,54,55,56,57]:
    print(tgt_dates[i], 'active:', bool(active[i]), 'mhw cells:', int(cells_per_day[i]), 'hot cells:', int(hot_cells[i]))
print('...')
for i in range(52, 62):
    print(tgt_dates[i], 'active:', bool(active[i]), 'mhw cells:', int(cells_per_day[i]), 'hot cells:', int(hot_cells[i]))
print('last days:')
for i in range(87, 92):
    print(tgt_dates[i], 'active:', bool(active[i]), 'mhw cells:', int(cells_per_day[i]), 'hot cells:', int(hot_cells[i]))
